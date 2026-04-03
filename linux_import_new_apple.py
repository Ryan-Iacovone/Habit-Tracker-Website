import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
import time
import numpy as np
from zoneinfo import ZoneInfo
from datetime import datetime, date
from fitparse import FitFile

from apple.apple_health_xml_convert_linux import preprocess_to_temp_file, strip_invisible_character, xml_to_csv, save_to_csv, \
remove_temp_file

# Static creation of the engine to connect to linux sql db
engine = create_engine(r"sqlite:///\\192.168.1.164\WarpDrive\habit_website\habits.db")

def apple_health_xml_convert():
    file_path = r"\\192.168.1.164\WarpDrive\habit_website\apple\export.xml" # Changed file path
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

    # Using the existing max date in my db to filter to only new data from apple
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



#### Uploading .fit bike workouts to db 

### Bike Workout table
def bike_workout_upload(raw_bike_data, today_upload_date):

    # Converting timestamp to utc datetime format for sqlite db
    raw_bike_data["timestamp"] = raw_bike_data["timestamp"].astype(str) + ".000000"

    # Grabbing min and max times for the bike workout
    # timestamp from .fit file is already in UTC
    max_time = max(raw_bike_data["timestamp"])
    min_time = min(raw_bike_data["timestamp"])

    engine = create_engine(f"sqlite:///habits.db")
    with engine.begin() as conn:
        # Bike Workout table
        result = conn.execute(text("""INSERT INTO bike_workout (start_time, end_time, upload_date)
                            VALUES (:start_time, :end_time, :upload_date)"""),
                            {"start_time": str(min_time), "end_time": str(max_time), "upload_date": str(today_upload_date) })
        
        workout_id = result.lastrowid  # Get the ID of the workout we just inserted

    return workout_id


### Bike Units table
def bike_units_upload(raw_bike_data):

    # Data cleaning step to conver the data to long format

    ## Statically Defining the metric-to-unit mappings
    metric_unit_map = {
        'altitude': 'meters',
        'cadence': 'revolutions_per_minute',
        'distance': 'meters',
        'enhanced_altitude': 'meters',
        'enhanced_speed': 'meters_per_second',
        'position_lat': 'degrees',
        'position_long': 'degrees',
        'power': 'watts',
        'speed': 'meters_per_second'
    }

    ## Statically defining the unit to abbreviation mappings
    unit_abv_map = {
        'meters': 'm',
        'revolutions_per_minute': 'rpm',
        'meters_per_second': 'm/s',
        'degrees': 'deg',
        'watts': 'W',
    }

    ## Melt the dataframe
    bike_data_long = pd.melt(raw_bike_data, 
                id_vars=['timestamp'], 
                value_vars=['altitude', 'cadence', 'distance', 'enhanced_altitude',
                            'enhanced_speed', 'position_lat', 'position_long',
                            'power', 'speed'], 
                var_name="metric", 
                value_name="value")


    ## Add unit columns using map
    bike_data_long['unit_name'] = bike_data_long['metric'].map(metric_unit_map) 
    bike_data_long['metric_unit'] = bike_data_long['unit_name'].map(unit_abv_map)


    # Uploading data to the bike units df only if it's new 

    ## Filtering bike_data_long to only revlavent columns associated with bike_units table
    bike_units_df = bike_data_long[["metric", "unit_name", "metric_unit"]].drop_duplicates() # drop_dups to get unique values

    for _, row in bike_units_df.iterrows():
        metric_type = row["metric"]
        metric_unit = row["metric_unit"]
        unit_name = row["unit_name"]

        with engine.begin() as conn:
            ## Insert only if it doesn't already exist
            conn.execute(text("""
                INSERT OR IGNORE INTO bike_units (metric_type, metric_unit, unit_name)
                VALUES (:metric_type, :metric_unit, :unit_name)"""), 
                {"metric_type": metric_type, "metric_unit": metric_unit, "unit_name": unit_name})
            
    return bike_data_long
            

### Bike Metrics table
def bike_metrics_upload(bike_data_long, workout_id):

   # Selecting data only relavent to bike_metrics table insertion 
   bike_metrics_df = bike_data_long[["timestamp", "metric", "value"]].drop_duplicates().copy()

   # workout_id comes from above insertion code
   bike_workout_id = workout_id

   # Grabbing all the metric types from the metrics table which I'll use to filter incoming bike data and insert into bike_metrics
   with engine.begin() as conn:
      bike_units = pd.read_sql_query(text("""SELECT id, metric_type 
                                          FROM bike_units"""), conn)

   bike_metrics_df["workout_id"] = bike_workout_id

   # Looping through each bike metric and uploading data from new bike file with the appropriate bike metric id 
   for _, row in bike_units.iterrows():
      metric_name = row["metric_type"]
      
      bike_metrics_upload_df = bike_metrics_df[bike_metrics_df["metric"] == metric_name].copy()

      # Now that we're filtered by metric name we can just insert the id for that metric
      bike_metrics_upload_df["metric_id"] = row["id"]
      
      # After filtering by metric column droppping it because now we have it's ID!
      bike_metrics_upload_df.drop(columns=["metric"], inplace=True)

      # Appending the new raw data to the apple_data_raw table
      bike_metrics_upload_df.to_sql(name="bike_metrics", con=engine, if_exists='append', index=False)


### Upload new .fit files from specified directory to bike specific tables in SQL
def upload_new_fit_files(directory, today_upload_date):

    # Initializing file number counter to start at the first file
    file_number = 0
    total_unprocessed_files = len([file for file in os.listdir(directory) if "Bike Workout" not in file])

    for file_path in os.listdir(directory):
        # Filtering to fit files that I have not processed yet (All processed files get renamed)
        if "Bike Workout" not in file_path:
            bike_fit_file = os.path.join(directory, file_path)

            # This is where python creates the connection to the fit file and reads it in
            fitfile = FitFile(bike_fit_file)

            # Initializing rows
            rows = []

            # Iterate over all record messages
            for record in fitfile.get_messages('record'):
                row = {}

                # Each record contains multiple data fields
                for field in record:
                    row[field.name] = field.value

                rows.append(row)

            # Create DataFrame
            df = pd.DataFrame(rows)

            # Dropping heart rate because it's blank
            raw_bike_data = df.drop(columns="heart_rate")

            # Putting bike data into appropriate tables
            ## Inserting data into the Bike workouts table
            workout_id = bike_workout_upload(raw_bike_data, today_upload_date)

            ## Inserting data into the Bike units table
            bike_data_long = bike_units_upload(raw_bike_data)    

            ## Inserting data into the Bike metrics table
            bike_metrics_upload(bike_data_long, workout_id)

            # For each fit file changing the name so I don't read it in again  
            for record in fitfile.get_messages('record'):
                for field in record:
                    if field.name == "timestamp":     #, field.value, field.units
                        file_date = field.value
                        # String formatting the date variable
                        file_date = file_date.strftime('%m-%d-%Y')
                        break
                if file_date:
                    break

            # Important to discard the connection to fitfile before saving over it otherwise os.rename will error out because python is still using the file
            del fitfile

            # This would be bad if we can't find timestamp data
            if not file_date:
                print(f"No timestamp found for {file_path}")
                continue
            
            # Renaming current file to fit naming schema: 01-14-2026 Bike Workout
            os.rename(bike_fit_file, os.path.join(directory, f"{file_date} Bike Workout.fit"))

            file_number += 1
            
            # Readable step to ensure correct number of files are processed
            print(f"Processed file '{file_path}', number {file_number} out of {total_unprocessed_files}")


### Use newly inserted bike workout data to add specific metrics to clycling workouts in the apple_wokrouts table

# Grabbing dates of all bike workouts from apple
def get_apple_cycle_data():
        with engine.begin() as conn:
                apple_cycle = pd.read_sql_query(
                        text("""SELECT StartDate, activity, workout_id 
                                FROM apple_workouts
                                where activity = 'Cycling' and metric = 'Duration'
                                order by StartDate desc"""), conn,
                        parse_dates=["StartDate"],
                        dtype={"workout_id": "Int64"})

                # Localizing to UTC timezone for merging later
                apple_cycle["StartDate"] = apple_cycle["StartDate"].dt.tz_localize("UTC")

                # Abstracting to date for merge to .fit data (won't merge perfectly on datetime)
                apple_cycle["apple_date"] =  apple_cycle["StartDate"].dt.date

                return apple_cycle
        

# Grabbing total distance and average wattage from .fit files bike workouts we just uploaded
def get_fit_cycle_data(today_upload_date):
    with engine.begin() as conn:
        fit_distance = pd.read_sql_query(
            text("""SELECT bw.id, bw.start_time, MAX(bm.value) as 'max_distance'
                    from bike_workout bw 
                    LEFT OUTER JOIN bike_metrics bm 
                    on bm.workout_id = bw.id 
                    LEFT OUTER JOIN bike_units bu 
                    on bu.id = bm.metric_id
                    where bu.metric_type = 'distance' AND bw.upload_date = :today_upload_date 
                    GROUP BY bw.id"""), conn,
            params={"today_upload_date": str(today_upload_date)},
            parse_dates=["start_time"])
        
        fit_watts = pd.read_sql_query(
            text("""SELECT bw.id, ROUND(AVG(bm.value), 2) as 'avg_watts'
                    from bike_workout bw 
                    LEFT OUTER JOIN bike_metrics bm 
                    on bm.workout_id = bw.id 
                    LEFT OUTER JOIN bike_units bu 
                    on bu.id = bm.metric_id
                    where bu.metric_type = 'power' AND bw.upload_date = :today_upload_date
                    GROUP BY bw.id"""), conn,
            params={"today_upload_date": str(today_upload_date)},
            parse_dates=["start_time"])

    # Localizing to UTC timezone for merging because this is the start time var that will stay
    fit_distance["start_time"] = fit_distance["start_time"].dt.tz_localize("UTC")

    fit_distance["fit_date"] = fit_distance["start_time"].dt.date

    # Merging various calculations of bike metric data together at bike workout level into singular df for upload
    fit_total = pd.merge(fit_distance, fit_watts, on="id", how="left")

    return fit_total


def upload_fit_to_apple(fit_total, apple_cycle):

    # Using fit file data to find corresponding apple bike workouts 
    combined = pd.merge(fit_total, apple_cycle, left_on="fit_date", right_on="apple_date", how="left")

    # Meters to miles conversion
    combined["max_distance_miles"] = ( int(combined["max_distance"]) / 1609).round(2)

    # Converting start date to sqlite appropriate format
    combined["StartDate"] = combined["StartDate"].dt.strftime('%Y-%m-%d %H:%M:%S') + ".000000"

    # Dropping unnecessary/helper columns
    combined.drop(columns=["start_time", "max_distance", "fit_date", "apple_date"], inplace=True)

    ## Defining dict with variable options   
    variables = {"max_distance_miles": {"metric":"DistanceCycling", "measurement_type": "sum"}, 
                "avg_watts": {"metric":"AvgWatts", "measurement_type": "average"}}

    with engine.begin() as conn:
        for var_name, var_config in variables.items() :
            temp_df = combined[combined[var_name].notnull()][["StartDate",  "activity", "workout_id", var_name]]

            temp_df["metric"] = var_config["metric"]
            temp_df["measurement_type"] = var_config["measurement_type"]
            temp_df["activity_type"] = "Cardio"

            for _, row in temp_df.iterrows():

                conn.execute(text("""
                        INSERT INTO apple_workouts (StartDate, activity, metric, measurement_type, value, d_unit, activity_type, workout_id)
                        VALUES (:StartDate, :activity, :metric, :measurement_type, :value, :d_unit, :activity_type, :workout_id)"""), {
                        'StartDate': str(row["StartDate"]),
                        'activity': row["activity"],
                        'metric': row["metric"],
                        'measurement_type': row["measurement_type"],
                        'value': row[var_name],  # Taking the variable name from the dict key
                        'd_unit': None,
                        'activity_type': row["activity_type"],
                        'workout_id': row["workout_id"]
                    })


if __name__ == '__main__':
    
    # Using the external code to convert raw apple xml export to more usable csv file 
    apple_health_xml_convert()

    # Applying logic to smartly find today's apple health export file
    ## Defining the subddirectroy where apple docs live
    directory = r"\\192.168.1.164\WarpDrive\habit_website\apple"  # Changed file path for linux computer
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
    print("Reading in newly uploaded raw apple data from apple_data_raw SQL DB \n")
    apple_workouts = Read_Apple_Workouts(max_UTC_date_db)

    # Convert apple workouts to long format plus selecting specific columns
    print("Cleaning newly uploaded Apple raw data into only apple workouts\n")
    aw_long = aw_to_long(apple_workouts)

    # Properly add in workout id taking into account existing max workout id plus coalescing activity variable 
    aw_final = add_workout_id(aw_long)

    print("Uploading newly cleaned apple workouts data to 'apple_workouts' SQL DB \n")
    # Final Upload
    final_upload(aw_final)

    # Displaying date range bulk upload took place for
    print(f"Uploaded apple data from {str(max_UTC_date_db)} to {str(max(apple_workouts['startDate']))} ")

    ####### .fit file ETL process #######
    print("\nNow moving on to uploading bike workouts from .fit files to bike specific SQL tables... \n")

    time.sleep(1)

    ## Directory where all fit files are saved
    bike_directory = r"\\192.168.1.164\WarpDrive\habit_website\bike_files"  # Changed directory for linux computer

    ## Defining server upload time once to use in multiple places
    today_upload_date = date.today().strftime("%m-%d-%Y")

    ## Specific function that uploads data to bike specific SQL tables
    upload_new_fit_files(bike_directory, today_upload_date)

    print("\nUploaded bike data from .fit files to bike specific SQL tables")

    time.sleep(1)

    ####### Uploading specific metrics from bike tables to apple_workouts #######

    print("\nUploading specific bike metrics from .fit file to cycling workouts in apple_workouts table")

    ## Gathering all bike workout data from apple_workouts
    apple_cycle = get_apple_cycle_data()

    ## Gathering all specific metrics like total distance and avg wattage for each .fit bike workout
    fit_total = get_fit_cycle_data(today_upload_date)

    ## Merging .fit metrics to apple_workouts cycling data and uploading to apple_workouts table 
    upload_fit_to_apple(fit_total, apple_cycle)

    print("\n.fit data successfully matched and uploaded to apple_workouts table. Exiting script...")

    time.sleep(12)