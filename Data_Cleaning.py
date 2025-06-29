import pandas as pd
from itertools import product
from pandas.api.types import CategoricalDtype
from sqlalchemy import create_engine, text
import numpy as np
import json

# Database configuration details
def create_sql_engine():
    # Create a SQLAlchemy engine to connect to the SQLite database
    Database = "habits.db"
    engine = create_engine(f"sqlite:///{Database}")
    return engine


# Update the list of book titles table in my database with any potential new entries
def load_book_options():
    engine = create_sql_engine()

    # read_sql_query simple 
    with engine.connect() as connection:
        whole_table = pd.read_sql_query(
            text("""SELECT * FROM habit_logs
                WHERE habit_type = 'reading'"""), connection)
        
    # Realeasing the database connection
    engine.dispose() 
    
    # Load the "data" column (which is a json string) into a pandas series because it's a singular column
    df_parsed = whole_table["data"].apply(json.loads)

    # Normalizing the json string into a pandas dataframe
    df_expanded = pd.json_normalize(df_parsed)

    # Grabbing unique book titles from the df and sorting them
    book_titles = sorted(df_expanded["book_title"].unique().tolist())

    # Add an "Other" option to the list of book titles because 'other' is not saved to the database
    book_titles.append("Other") 

    return book_titles

# List to log existing workouts from db
def load_workout_options():
    engine = create_sql_engine()

    # read_sql_query simple 
    with engine.connect() as connection:
        workouts = pd.read_sql_query(
            text("""SELECT DISTINCT exercise FROM workouts"""), connection)

    engine.dispose()

    # Sorting and converting the exercise column to a list to pass to html
    workouts_list = sorted(workouts["Exercise"].tolist())

    # Add "Other" option to the list of book titles and works. This way other is not saved to the database
    workouts_list.append("Other")

    return workouts_list





# Read in cleaned Apple Workouts data 
def Read_Apple_Workouts():
    engine = create_sql_engine()
    # Read in the data and parse datetime columns
    with engine.connect() as connection:
        aw_final = pd.read_sql_query(
            text("SELECT * FROM apple_workouts"),
            connection,
            parse_dates=['StartDate', 'EndDate', 'week_period'])
    # Clean up connection
    engine.dispose()

    # Convert 'month' to a period type for better handling of monthly data
    aw_final['month'] = aw_final['month'].astype('period[M]')

    return aw_final

aw_final = Read_Apple_Workouts()


# Function that fills in missing data for each grouped by df 
def fill_missing_combinations(
    original_df,
    aggregated_df,
    time_col,
    category_col,
    value_cols,
    time_filter=None,
    category_values=None):

    # Step 1: Filter time periods if needed
    if time_filter:
        time_values = original_df[time_filter(original_df)].loc[:, time_col].unique()
    else:
        time_values = original_df[time_col].unique()
    # Step 2: Get all categories
    if category_values:
        category_values = category_values
    else:
        category_values = aggregated_df[category_col].unique()
    # Step 3: Create full index
    full_index = pd.DataFrame(
        product(category_values, time_values),
        columns=[category_col, time_col])
    # Step 4: Merge with aggregated data
    filled_df = pd.merge(full_index, aggregated_df, on=[category_col, time_col], how='left')
    # Step 5: Fill NaNs with 0 for specified value columns
    for col in value_cols:
        filled_df[col] = filled_df[col].fillna(0)

    return filled_df.sort_values(by=[time_col, category_col]).reset_index(drop=True)


############### Frequency bar chart grouped by exercise type ###############
def gen_freq_df(aw_final):
    activities = ["Walking", "Cycling", "TraditionalStrengthTraining", "Running"]

    # Grab last 5 Months of data
    today = pd.Timestamp.today()
    l_5_m = (today - pd.DateOffset(months=5)).to_period('M')

    df_counts = (aw_final[(aw_final['metric'] == 'Duration') & (aw_final['activity'].isin(activities)) & (aw_final['month'] > l_5_m)]
        .groupby(['month', 'activity'])
        .size()
        .reset_index(name='n'))
    
    full_count_data = fill_missing_combinations(
        original_df=df_counts,
        aggregated_df=df_counts,
        time_col='month',
        category_col='activity',
        value_cols=['n'])

    full_count_data['n'] = full_count_data['n'].astype(int)  # Convert to int for better readability

    return full_count_data


############### Distance per week grouped by exercise type ###############
def gen_distance_df(aw_final):
    miles_week = (aw_final[(aw_final['activity'].isin(['Running', 'Cycling'])) & (aw_final['metric'].str.contains("Distance")) & (aw_final['month'] > "2025-03")]
        .groupby(['activity', 'week_period'])['value']
        .agg(Total_Miles='sum', n='count')  # compute both mean and count
        .round(2) # Round to 2 decimal places
        .reset_index())


    full_miles_week = fill_missing_combinations(
        original_df=aw_final,
        aggregated_df=miles_week,
        time_col='week_period',
        category_col='activity',
        value_cols=['Total_Miles', 'n'],
        time_filter=lambda df: df['month'] > "2025-03",
        category_values=['Running', 'Cycling'])

    # IDK how I feel about this
    full_miles_week['week_label'] = full_miles_week['week_period'].dt.strftime('%b %d')
    week_order = full_miles_week.sort_values('week_period')['week_label'].unique()
    full_miles_week['week_label'] = full_miles_week['week_label'].astype(
        CategoricalDtype(categories=week_order, ordered=True))
    
    return full_miles_week


def gen_mins_df(aw_final):
    mins_week = (aw_final[
            (aw_final['activity_type'].notna()) &
            (aw_final['metric'] == "Duration") &
            (aw_final['month'] > "2025-03")]
        .groupby(['activity_type', 'week_period'])['value']
        .agg(Total_min='sum', n='count')  # compute sum and count
        .round(2)  # Round to 2 decimal places
        .reset_index())

    full_mins_week = fill_missing_combinations(
        original_df=aw_final,
        aggregated_df=mins_week,
        time_col='week_period',
        category_col='activity_type',
        value_cols=['Total_min', 'n'],
        time_filter=lambda df: df['month'] > "2025-03",
        category_values=['Cardio', 'Weights'])
    
    return full_mins_week

def gen_workout_time_df(aw_final):
    workout_time = aw_final[(aw_final['StartDate'].dt.year >= 2025) & 
                            (aw_final['metric'] == 'Duration')].groupby(['week_period'])['value'].agg(Time='sum', n='count').reset_index()
    workout_time['Time'] = workout_time['Time'].round(2)

    return workout_time


def gen_activity_treemap_df(aw_final):

    activites = ['Running', 'Cycling', 'TraditionalStrengthTraining', 'Swimming']

    # Time I spent on each exercise every week

    activity_distribution = (
        aw_final[
            (aw_final['metric'] == "Duration") & 
            (aw_final['activity'].isin(activites)) & 
            (aw_final['StartDate'].dt.year >= 2025)]
        .sort_values(by='StartDate', ascending=False)
        .head(60) # Get the last 8 weeks of data
        .groupby(['activity'])['value']
        .agg(count='count')
        .reset_index())
                
    # Add percent of total column
    total = activity_distribution['count'].sum()
    activity_distribution['percent'] = activity_distribution['count'] / total

    # Format labels as "Activity<br>Count (Percent)"
    activity_distribution['label'] = activity_distribution.apply(lambda row: f"{row['activity']}<br>{row['count']} ({row['percent']:.1%})", axis=1)

    return activity_distribution


############### KPI Statisitcs Functions ###############

# Going to have to recreate this function with apple workout data
def get_kpi_stats():
    # Get today's date
    today = pd.Timestamp.today()

    # Get this month and last month as Periods
    this_month = today.to_period('M')
    last_month = (today - pd.DateOffset(months=1)).to_period('M')

    # Since I just want to get straight count numbers for this db, I can use the shape funciton to get row count
    wokrout_count_CM = aw_final[(aw_final['month'] == this_month) & (aw_final['metric'] == 'Duration')].shape[0]
    workout_count_LM = aw_final[(aw_final['month'] == last_month) & (aw_final['metric'] == 'Duration')].shape[0]
    workout_count_year = aw_final[(aw_final['StartDate'].dt.year >= 2025) & (aw_final['metric'] == 'Duration')].shape[0]

    # Gather workout time metrics
    workout_time = aw_final[(aw_final['metric'] == 'Duration')].groupby(['week_period'])['value'].agg(Time='sum', n='count').reset_index()
    workout_time = workout_time.tail(5) # Taking the last 5 weeks of data 
    workout_time_hrs_avg = (workout_time["Time"].mean()/60).round(2)

    # Gather names for above statistic

    current_month_name = today.month_name()
    last_month_name = (today - pd.DateOffset(months=1)).strftime('%B')  

    return workout_count_year, workout_count_LM, wokrout_count_CM, current_month_name, last_month_name, workout_time_hrs_avg




############### Dynamic Visuals Functions ###############

# Generates a table for the dynamic exercise filter page 
def specific_exercise_filter(specific_exercise):
    engine = create_sql_engine()
    with engine.connect() as connection:
        # Use SQLAlchemy's text() to safely parameterize the query
        workouts = pd.read_sql_query(
            text("SELECT * FROM workouts WHERE exercise = :activity"),
            connection,
            params={"activity": specific_exercise}  # Correct parameter name to match function argument
        )
    engine.dispose()

    # Convert the timestamp variable to a datetime format, i'm unsure why I have to do this because that's how it's coded and uploaded in the databse
    workouts['Timestamp'] = pd.to_datetime(workouts['Timestamp'])

    # Then I convert that that datetime variable into a more readable string format/ might even decide I don't want to display hours and minutes
    workouts['Timestamp'] = workouts['Timestamp'].dt.strftime('%B %d, %Y %H:%M:%S')

    # Formatting weight variable to show 1 decimal place only if it exits, otherwise I make it a string and strip the '.' and ending '0'
    # Idk how I feel about this as I lose weight as a numeric varaible but should be contained in this function only
    workouts['Weight'] = workouts['Weight'].apply(lambda w: f"{w:.1f}".rstrip('0').rstrip('.') if pd.notnull(w) else '')

    return workouts.to_html(classes='workout-table', index=False, border=1)


def generate_excise_options():
    # Get unique exercises for dropdown
    engine = create_sql_engine()
    with engine.connect() as connection:
        workouts = pd.read_sql_query(
            text("SELECT DISTINCT Exercise FROM workouts" 
        "         ORDER BY Exercise"), connection)
        exercise_options = workouts['Exercise'].dropna().tolist()

    engine.dispose()

    return exercise_options