import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
import time
import numpy as np
from zoneinfo import ZoneInfo
from datetime import datetime

# Local database import
from db import engine 

from apple.apple_health_xml_convert import preprocess_to_temp_file, strip_invisible_character, xml_to_csv, save_to_csv, \
remove_temp_file

def apple_health_xml_convert():
    file_path = r"apple/export.xml"
    temp_file_path = preprocess_to_temp_file(file_path)
    health_df = xml_to_csv(temp_file_path)
    save_to_csv(health_df)
    remove_temp_file(temp_file_path)

def max_date():
    # Read from SQLite and parse those columns as datetime
    with engine.connect() as connection:
        max_date_db = pd.read_sql_query(
            text("""SELECT MAX(DATETIME(adr.startDate)) as 'Max_Raw_UTC_Start_Date'
                    FROM apple_data_raw adr"""), 
            connection,
            parse_dates=['Max_Raw_UTC_Start_Date'])   


    max_date_db["Max_Raw_UTC_Start_Date"] = (
        pd.to_datetime(max_date_db["Max_Raw_UTC_Start_Date"])
        .dt.tz_localize("UTC"))

    max_UTC_date_db = max_date_db["Max_Raw_UTC_Start_Date"].iloc[0]

    return max_UTC_date_db

# ETL step of gathering new data from apple health and upploading it almost as it is apple_data_raw
def upload_new_raw_apple_data(max_UTC_date_db):
    # Read in new CSV File, low_memory=False to avoid dtype warnings
    apple = pd.read_csv(os.path.join(directory, apple_file), low_memory=False)

    # Fitler the source to only my Apple Watch (Could pull in other devices later like iPhone or gamin)
    apple = apple[(apple['sourceName'] == "Ryan’s Apple\xa0Watch") | (apple['sourceName'].isna())]

    # Strip the "HKWorkoutActivityType" prefix from the workout types
    apple["workoutActivityType"] = apple["workoutActivityType"].str.replace("HKWorkoutActivityType", "")

    # Drop the UUID column, apple added this since last 7/18 upload
    apple.drop(columns=['uuid'], inplace=True)

    # Creating a copy of apple dataframe to avoid settingwithcopy warnings when converting datetime
    apple_copied = apple.copy()

    # Cleaning step helpful for troubleshooting
    del apple

    # Convert date columns to datetime format including UTC timezone
    datetime_cols = ['startDate', 'endDate', 'creationDate']
    for col in datetime_cols:
        apple_copied[col] = pd.to_datetime(apple_copied[col], format='%Y-%m-%d %H:%M:%S %z', utc=True)

    # Using the exisiting max date in my db to filter to only new data from apple 
    apple_copied = apple_copied[apple_copied["startDate"] > max_UTC_date_db] # dt_utc_test  max_UTC_date_db

    # Appending the new raw data to the apple_data_raw table
    apple_copied.to_sql(name="apple_data_raw", con=engine, if_exists='append', index=False)


def Read_Apple_Workouts(max_UTC_date_db):
    # Reading in only the newly updated data from apple_data_raw (using inital max_UTC_date_db prior to uploading new raw data)
    with engine.connect() as connection: 
        apple_raw = pd.read_sql_query( 
            text("""SELECT workoutActivityType, startDate, type, maximum, minimum, sum, average, duration, durationUnit 
            FROM apple_data_raw
            WHERE StartDate > :max_date"""),
            connection,
            params={"max_date": str(max_UTC_date_db)}, # Using the str version of the datetime for filtering
            parse_dates=['startDate']) # Parse date here takes out need for pd.to_datetime below 

    apple_raw["startDate"] = apple_raw["startDate"].dt.tz_localize("UTC")

    # Filters df to include only rows where at least one of the workout-related columns is not missing (NaN).
    # .notna() Check for Non-Nulls in selected columns 
    # .any(axis=1) aggregates rows where there's at least one non-missing value 
    apple_workouts = apple_raw[apple_raw.notna().any(axis=1)] 

    return apple_workouts


# Convert apple workouts to long format
def aw_to_long(apple_workouts):

    # Reshape the apple_workouts DataFrame from wide format (one row per workout with multiple measurement columns) to long format (one row per measurement per workout).
    df_long = pd.melt(apple_workouts, 
                        id_vars=['startDate', 'workoutActivityType', 'type', 'duration', 'durationUnit'],
                        value_vars=['maximum', 'minimum', 'sum', 'average'], # turned into rows via where the name goes into 'measurement_type' and actual values to the 'value' column
                        var_name='measurement_type', 
                        value_name='value')

    # Removing rows where either type or value are null (no meaningful data here)
    df_long = df_long[(df_long['type'].notna()) | (df_long['value'].notna())]

    # Handle duration rows separately and combine
    duration_rows = apple_workouts[apple_workouts['duration'].notna() & apple_workouts['type'].isna()].copy()
    duration_rows = duration_rows.assign(
        measurement_type='total',
        value=duration_rows['duration'],
        type='Duration')[['startDate', 'workoutActivityType', 'type', 'measurement_type', 'value', 'durationUnit']]

    # Combine and clean
    aw_long = pd.concat([df_long[df_long['value'].notna()][['startDate', 'workoutActivityType', 'type', 'measurement_type', 'value', 'durationUnit']],
        duration_rows], ignore_index=True)

    # Rename columns for clarity
    aw_long.rename(columns={'startDate': 'StartDate', 'workoutActivityType': 'activity', 'type': 'metric', # Why do I rename StartDate to be different than apple data raw?
                        'measurement_type': 'measurement_type', 'value': 'value', 'durationUnit': 'd_unit'}, inplace=True)

    # cleaning value column to only go out 2 decimal places
    aw_long['value'] = aw_long['value'].round(2)

    aw_long.sort_values('StartDate', ascending=False, inplace=True)

    return aw_long


def max_workout_id():
    #Gathering the max workout_id from existing apple_workouts table
    with engine.connect() as connection:
        max_workout_id_df = pd.read_sql_query(
                text("""SELECT max(workout_id) as workout_id 
                        FROM apple_workouts
                        WHERE activity IS NOT NULL"""), # Need to filter on activity because otherwise workout_id is NA
                connection)  

    # Grabbing singlular max workout_id from dataset to filter new data off of  
    max_workout_id = int(max_workout_id_df['workout_id'][0]) # Maybe make this an INT variable?

    return max_workout_id


def add_workout_id(aw_long):

    # We're able to easily get unique workouts by date because aw_long only has activity filled for the duration metric which every workout has 1 of 
    activity_map = aw_long[aw_long['activity'].notnull()][["StartDate", "activity"]]

    # Sorting values by date and resetting index (easy way to grab a unique id so long as I'm sorting correctly)
    activity_map = activity_map.sort_values('StartDate').reset_index(drop=True)

    # Creating a new variable based on the index  
    # Previous null values probably from Garmin are keeping workout_id from being an integer in aw_final
    activity_map['workout_id'] = activity_map.index.astype(int) + max_workout_id()  # Start IDs from 1

    # Merge activity back onto the main dataframe using startDate
    aw_final = pd.merge(aw_long, activity_map, on='StartDate', how='left', suffixes=('', '_Specifier'))

    # Drop the original activity column
    aw_final.drop(columns=['activity'], inplace=True)

    # Rename the helper column to activity since that's actually what we'll want
    aw_final.rename(columns={'activity_Specifier': 'activity'}, inplace=True)

    # Adding new activity type variable for minutes calculation 
    aw_final['activity_type'] = np.where(aw_final['activity'].isin(['Running', 'Cycling', 'Swimming', 'Walking']), 'Cardio',
        np.where(aw_final['activity'] == 'TraditionalStrengthTraining', 'Weights', None))

    return aw_final


def final_upload(aw_final):
        aw_final.to_sql(name="apple_workouts", con=engine, if_exists='append', index=False) 



if __name__ == '__main__':
    
    # Using the external code to convert raw apple xml export to more usable csv file 
    apple_health_xml_convert()

    # Applying logic to smartly find today's apple health export file
    ## Defining the subddirectroy where apple docs live
    directory = "apple/"
    ## Grabbing today's date
    today = datetime.now().strftime('%Y-%m-%d') # Format: '2025-12-10' December 10th, 2025  datetime.now
    ## Initializing apple_file variable
    apple_file = None

    for file in os.listdir(directory):
        if file.endswith(".csv") and today in file:
            apple_file = file
            print(f"Found Apple Health file: {apple_file}")
            break  # stop once we find it

    if apple_file is None:
        print(f"No apple file found with {today} date... Exiting script")
        time.sleep(5)
        sys.exit(1)
    
    print("\nMoving on to data cleaning stage... \n")
    time.sleep(1)

    # Grabbing existing max date from apple_data_raw table so that we can tell what data is old and new 
    print("Grabbing the max date from existing DB \n")
    max_UTC_date_db = max_date()

    # Uploading new raw apple data to apple_data_raw table, based on inital max date of the apple_data_raw db
    print("Uploading new raw Apple CSV data to the raw Apple SQL DB \n")
    upload_new_raw_apple_data(max_UTC_date_db)
    time.sleep(.5)

    # Read in newly uploaded raw apple data from the sql dbbv
    print("\nReading in newly uploaded raw apple data from apple_data_raw SQL DB \n")
    apple_workouts = Read_Apple_Workouts(max_UTC_date_db)

    # Convert apple workouts to long format plus selecting specific columns
    print("Cleaning newly uploaded Apple raw data into only apple workouts")
    aw_long = aw_to_long(apple_workouts)

    # Properly add in workout id taking into account existing max workout id plus coalescing activity variable 
    aw_final = add_workout_id(aw_long)

    print("\nUploading newly cleaned apple workouts data to 'apple_workouts' SQL DB \n")
    # Final Upload
    final_upload(aw_final)

    # Displaying date range bulk upload took place for
    print(f"Finished! Uploaded data from {str(max_UTC_date_db)} to {str(max(apple_workouts['startDate']))} ")

    time.sleep(12)