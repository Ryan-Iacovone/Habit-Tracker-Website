import os
import datetime as dt
import sys
import pandas as pd
from sqlalchemy import create_engine, text
import time
import numpy as np

from apple.apple_health_xml_convert import preprocess_to_temp_file, strip_invisible_character, xml_to_csv, save_to_csv, \
remove_temp_file

def apple_health_xml_convert():
    file_path = r"apple/export.xml"
    temp_file_path = preprocess_to_temp_file(file_path)
    health_df = xml_to_csv(temp_file_path)
    save_to_csv(health_df)
    remove_temp_file(temp_file_path)

engine = create_engine(f"sqlite:///habits.db")


def max_date():
    # Read in existing max date from apple_data_raw table 
    with engine.connect() as connection:
        max_date_db = pd.read_sql_query(
            text("SELECT max(StartDate) as Max_Date FROM apple_data_raw"), 
            connection,
            parse_dates=['startDate'])   
    engine.dispose()

    # Grabbing just the max date from df  
    max_date = max_date_db["Max_Date"][0]

    return max_date

# ETL step of gathering new data from apple health and upploading it almost as it is apple_data_raw
def upload_new_raw_apple_data(inital_max_date):
    # Read in new CSV File
    apple = pd.read_csv(os.path.join(directory, apple_file))

    ### Cleaning Data ###

    # Using the exisiting max date in my db to filter to only new data from apple 
    apple = apple[apple["startDate"] >= inital_max_date]

    # Fitler the source to only my Apple Watch (Could pull in other devices later like iPhone or gamin)
    apple = apple[(apple['sourceName'] == "Ryan’s Apple\xa0Watch") | (apple['sourceName'].isna())]

    # Strip the "HKWorkoutActivityType" prefix from the workout types
    apple["workoutActivityType"] = apple["workoutActivityType"].str.replace("HKWorkoutActivityType", "")

    # Convert date columns to datetime format (took 16 min to run on 2.4 million rows)
    datetime_cols = ['startDate', 'endDate', 'creationDate']
    for col in datetime_cols:
        apple[col] = pd.to_datetime(apple[col], errors='coerce', utc=True)

    for col in datetime_cols:
        apple[col] = apple[col].dt.strftime('%Y-%m-%dT%H:%M:%S%z')

    # Drop the UUID column, apple added this since last 7/18 upload
    apple.drop(columns=['uuid'], inplace=True)

    # Appending the actually new raw data to the apple_data_raw table
    apple.to_sql(name="apple_data_raw", con=engine, if_exists='append', index=False)


def Read_Apple_Workouts(inital_max_date):
    # Read from SQLite and parse those columns as datetime
    with engine.connect() as connection:
        apple = pd.read_sql_query( 
            text("""SELECT workoutActivityType, startDate, endDate, type, maximum, minimum, sum, average, duration, durationUnit 
            FROM apple_data_raw"""),
            connection,
            parse_dates=['startDate', 'endDate', 'creationDate'])
        

    # Has to be run in conjunction with 'upload_new_raw_apple_data' function to ensure both are using same max date value
    apple = apple[apple["startDate"] >= inital_max_date]

    # Gather a df of workouts types, their dates, and key statistics
    # Filters df to include only rows where at least one of the workout-related columns is not missing (NaN).
    # .notna() Check for Non-Nulls in selected columns 
    # .any(axis=1) aggregates rows where there's at least one non-missing value 
    apple_workouts = apple[apple[['maximum', 'minimum', 'sum', 'average', 'duration', 'workoutActivityType', 'durationUnit']].notna().any(axis=1)] 

    return apple_workouts


# Convert apple workouts to long format
def aw_to_long(apple_workouts):

    # Reshape the apple_workouts DataFrame from wide format (one row per workout with multiple measurement columns) to long format (one row per measurement per workout).
    df_long = pd.melt(apple_workouts, 
                        id_vars=['startDate', 'endDate', 'workoutActivityType', 'type', 'duration', 'durationUnit'],
                        value_vars=['maximum', 'minimum', 'sum', 'average'], # turned into rows via where the name goes into 'measurement_type' and actual values to the 'value' column
                        var_name='measurement_type', 
                        value_name='value')

    # rRemove rows where both type and value are null (no meaningful data here)
    df_long = df_long[(df_long['type'].notna()) | (df_long['value'].notna())]

    # Handle duration rows separately and combine
    duration_rows = apple_workouts[apple_workouts['duration'].notna() & apple_workouts['type'].isna()].copy()
    duration_rows = duration_rows.assign(
        measurement_type='total',
        value=duration_rows['duration'],
        type='Duration')[['startDate', 'endDate', 'workoutActivityType', 'type', 'measurement_type', 'value', 'durationUnit']]

    # Combine and clean
    result = pd.concat([df_long[df_long['value'].notna()][['startDate', 'workoutActivityType', 'type', 'measurement_type', 'value', 'durationUnit']],
        duration_rows], ignore_index=True)

    # Rename columns for clarity (Should probably rename into a dictionary at some point)
    result.columns = ['StartDate', 'activity', 'metric', 'measurement_type', 'value', 'd_unit', 'EndDate']

    # cleaning value column to only go out 2 decimal places
    result['value'] = result['value'].round(2)

    result.sort_values('StartDate', ascending=False, inplace=True)

    return result


def max_workout_id():
    #Gathering the max workout_id from existing apple_workouts table
    with engine.connect() as connection:
        max_workout_id_df = pd.read_sql_query(
            text("""SELECT max(workout_id) as workout_id 
                    FROM apple_workouts
                    WHERE activity IS NOT NULL"""), # Need to filter on activity because otherwise workout_id is NA
            connection)  

    # Grabbing the max date from dataset to filter new data off of  
    max_workout_id = max_workout_id_df['workout_id'][0]

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

    # Grabbing just the start of the week in dt fashion
    aw_final['week_period'] = aw_final['StartDate'].dt.to_period('W').apply(lambda r: r.start_time)

    # Extract Year-Month for grouping
    aw_final['month'] = aw_final['StartDate'].dt.to_period('M')

    # Adding new activity type variable for minutes calculation 
    aw_final['activity_type'] = np.where(aw_final['activity'].isin(['Running', 'Cycling', 'Swimming', 'Walking']), 'Cardio',
        np.where(aw_final['activity'] == 'TraditionalStrengthTraining', 'Weights', None))
    
    # need to do a couple of string conversions before uploading the data to the sql lite db
    aw_final['month'] = aw_final['month'].astype(str)
    aw_final['workout_id'] = aw_final['workout_id'].astype('Int64').astype(str)
    aw_final['StartDate'] = aw_final['StartDate'].dt.tz_convert(None)
    aw_final['EndDate'] = aw_final['EndDate'].dt.tz_convert(None)

    return aw_final


def final_upload(aw_final):
        aw_final.to_sql(name="apple_workouts", con=engine, if_exists='append', index=False)



if __name__ == '__main__':
    
    # Using the external code to convert raw apple xml export to more usable csv file 
    apple_health_xml_convert()

    # Defining the subddirectroy where apple docs live
    directory = "apple/"

    # Grabbing today's date
    today = dt.datetime.now().strftime('%Y-%m-%d') # Format: '2025-12-10' Decebmer 10th, 2025 

    # Getting user input at the breginning of this script to ensure I'm grabbing the correct file
    print(f"Using date of {today} to grab correct Apple Health export CSV file... \n")
    for file in os.listdir(directory):
        if file.endswith(".csv") and today in file:
            apple_file = file
        else:
            print("No apple file found with that date... Exiting script")
            sys.exit()
    
    print("\nMoving on to data cleaning stage... \n")
    time.sleep(1)

    # Grabbing existing max date from apple_data_raw table so that we can tell what's old and new data 
    print("Grabbing the max date from existing DB \n")
    max_date = max_date()

    # Uploading new raw apple data to apple_data_raw table, based on inital max date
    print("Uploading new raw Apple CSV data to the raw Apple SQL DB \n")
    upload_new_raw_apple_data(max_date)

    time.sleep(.5)

    print("\nReading in newly uploaded raw Apple workouts from 'apple_data_raw' SQL DB \n")
    # Read in raw apple workouts data from the sql db
    apple_workouts = Read_Apple_Workouts(max_date)

    print("Cleaning newly uploaded raw Apple data \n")
    # Convert apple workouts to long format
    aw_long = aw_to_long(apple_workouts)

    # Properly adding workout id taking into account existing max workout id 
    aw_final = add_workout_id(aw_long)

    print("\nUploading newly cleaned Apple data to 'apple_workouts' SQL DB \n")
    # Final Upload
    final_upload(aw_final)

    print("Finished!")

    time.sleep(5)