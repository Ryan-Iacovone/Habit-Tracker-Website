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
    # Read from SQLite and parse those columns as datetime
    with engine.connect() as connection:
        max_date_db = pd.read_sql_query(
            text("SELECT max(StartDate) FROM apple_data_raw"), 
            connection,
            parse_dates=['startDate'])   

    # Grabbing the max date from dataset to filter new data off of  
    max_date_db = max_date_db['max(StartDate)'].tolist()[0]

    return max_date_db


def R_A_raw_apple(max_date_db):
    # Read in new CSV File
    apple = pd.read_csv(os.path.join(directory, apple_file))

    ### Cleaning Data ###

    # Remove observations from csv file that are already in my sql db (remove this line if starting from scratch)
    apple = apple[apple["startDate"] >= max_date_db]

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

    # Appending the new raw data to my sql lite table
    apple.to_sql(name="apple_data_raw", con=engine, if_exists='append', index=False)


def Read_Apple_Workouts():
    # Read from SQLite and parse those columns as datetime
    with engine.connect() as connection:
        apple = pd.read_sql_query(
            text("SELECT * FROM apple_data_raw"),
            connection,
            parse_dates=['startDate', 'endDate', 'creationDate'])
        

    # Using max date from the inital upload into the apple workouts raw db to also ensure only new observations are going into the apple workouts table 
    apple = apple[apple["startDate"] >= max_date_db]

    # Gather a df of workouts types, their dates, and key statistics
    # Filters df to include only rows where at least one of the workout-related columns is not missing (NaN).
    # .notna() Check for Non-Nulls in selected columns 
    # .any(axis=1) aggregates rows where there's at least one non-missing value 
    apple_workouts = apple[apple[['maximum', 'minimum', 'sum', 'average', 'duration', 'workoutActivityType', 'durationUnit']].notna().any(axis=1)] 

    # Select particular variables
    apple_workouts = apple_workouts[["workoutActivityType", "startDate", "endDate", "type", "maximum", "minimum", "sum", "average", "duration", "durationUnit"]]

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

    # Rename columns for clarity
    result.columns = ['StartDate', 'activity', 'metric', 'measurement_type', 'value', 'd_unit', 'EndDate']

    # cleaning value column to only go out 2 decimal places
    result['value'] = result['value'].round(2)

    result.sort_values('StartDate', ascending=False, inplace=True)

    return result



def add_workout_id(aw_long):
    # Identify rows where activity is not null (these rows define the actual activity)
    activity_map = aw_long[aw_long['activity'].notnull()]

    activity_map = activity_map[["StartDate", "activity"]]

    # Creating a workout identifier
    # Creates sequential IDs starting from 0
    # Convert index IDs to integers
    activity_map = activity_map.reset_index(drop=True)
    activity_map['workout_id'] = activity_map.index

    # Merge activity back onto the main dataframe using startDate
    aw_final = aw_long.merge(activity_map, on='StartDate', how='left', suffixes=('', '_Specifier'))

    # Forward-fill the activity only for rows with the same startDate (simplicity but not needed )
    aw_final['activity'] = aw_final['activity'].fillna(aw_final['activity_Specifier'])

    # Drop helper column
    aw_final.drop(columns=['activity_Specifier'], inplace=True)

    # Think about later, can't convert column to int because of missing variables that are uploaded from garmin that wasn't filtered out initally because I need blanks
    #aw_final_new = aw_final_new['id'].astype('int')

    # Grabbing just the start of the week in dt fashion
    aw_final['week_period'] = aw_final['StartDate'].dt.to_period('W').apply(lambda r: r.start_time)

    # Adding week periods which is EXACTLY what I want! Idk why I then convert it to string
    #aw_final['week_period'] = aw_final['StartDate'].dt.to_period('W').astype(str)

    # Extract Year-Month for grouping
    aw_final['month'] = aw_final['StartDate'].dt.to_period('M')

    # Adding new activity type variable for minutes calculation 
    aw_final['activity_type'] = np.where(aw_final['activity'].isin(['Running', 'Cycling', 'Swimming']), 'Cardio',
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
    apple_health_xml_convert()

    # Defining the subddirectroy 
    directory = "apple/"

    # Grabbing today's date
    today = dt.datetime.now().strftime('%Y-%m-%d')

    # Getting user input at the breginning of this script to ensure I'm grabbing the correct file
    while True:
        choice = input("\nAre you using today's date to uploaded apple data? (y/n) \n").lower()
        if choice == 'y':
            # Lopping through each of the files in the directory to find a csv file with today's date
            for file in os.listdir(directory):
                if file.endswith(".csv") and today in file:
                    apple_file = file
            break
        if choice == "n":
            print("Exiting program...")
            time.sleep(2)
            sys.exit()
    
    print("\nMoving on to data cleaning stage... \n")
    time.sleep(1)

    print("Grabbing the max date from existing DB \n")
    max_date_db = max_date()

    print("Uploading new raw Apple CSV data to the raw Apple SQL DB \n")
    R_A_raw_apple(max_date_db)

    time.sleep(.5)

    print("\nReading in newly uploaded raw Apple workouts from 'apple_data_raw' SQL DB \n")
    # Read in raw apple workouts data from the sql db
    apple_workouts = Read_Apple_Workouts()

    print("Cleaning newly uploaded raw Apple data \n")
    # Convert apple workouts to long format
    aw_long = aw_to_long(apple_workouts)
    aw_final = add_workout_id(aw_long)

    print("\nUploading newly cleaned Apple data to 'apple_workouts' SQL DB \n")
    # Final Upload
    final_upload(aw_final)

    print("Finished!")

    time.sleep(5)