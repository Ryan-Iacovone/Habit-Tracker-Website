import pandas as pd
from itertools import product
from pandas.api.types import CategoricalDtype
from sqlalchemy import create_engine, text
import numpy as np
import json
from db import engine

# Update the list of book titles table in my database with any potential new entries
def load_book_options():

    # read_sql_query simple 
    with engine.connect() as connection:
        books_options = pd.read_sql_query(
            text("""SELECT DISTINCT answer FROM habit_answers
                WHERE question = 'book_title'"""), connection)
        
    book_titles = sorted(books_options["answer"].to_list())

    # Add an "Other" option to the list of book titles because 'other' is not saved to the database
    book_titles.append("Other") 

    return book_titles


# List to log existing workouts from db
def load_workout_options():

    with engine.connect() as connection:
        workouts = pd.read_sql_query(
            text("""SELECT DISTINCT answer FROM habit_answers
                WHERE question = 'workout_type'"""), connection)
        
    workouts_list = sorted(workouts['answer'].tolist())

    # Add "Other" option to the list of book titles and works. This way other is not saved to the database
    workouts_list.append("Other")

    return workouts_list



# Read in cleaned Apple Workouts data 
def Read_Apple_Workouts():

    # Read in the data and parse datetime columns
    with engine.connect() as connection:
        aw_final = pd.read_sql_query(
            text("SELECT * FROM apple_workouts"),
            connection,
            parse_dates=['StartDate', 'EndDate', 'week_period'])


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
    activities = ["Walking", "Cycling", "TraditionalStrengthTraining", "Running", "Swimming"]

    # Grab last 5 Months of data
    today = pd.Timestamp.today()
    l_5_m = (today - pd.DateOffset(months=7)).to_period('M')

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

    # Create a string label for display
    full_count_data['month_label'] = full_count_data['month'].dt.strftime('%b %Y')

    # Set 'month_label' as a categorical(factor variable) with order based on 'month_period'
    month_order = full_count_data.sort_values('month')['month_label'].unique()
    full_count_data['month_label'] = pd.Categorical(full_count_data['month_label'], categories=month_order, ordered=True)  # Convert to int for better readability

    # Adding a label for 'TraditionalStrengthTraining' top shorten it for the graph output
    full_count_data['activity'] = full_count_data['activity'].replace({'TraditionalStrengthTraining': 'Weights'})

    return full_count_data


############### Distance per week grouped by exercise type ###############
def gen_distance_df(aw_final):
    miles_week = (aw_final[(aw_final['activity'].isin(['Running', 'Cycling'])) & (aw_final['metric'].str.contains("Distance")) & (aw_final['month'] > "2025-06")]
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
        time_filter=lambda df: df['month'] > "2025-06",
        category_values=['Running', 'Cycling'])
        
        # Create a string label for display
    full_miles_week['week_label'] = full_miles_week['week_period'].dt.strftime('%b %d')

    # Set 'week_label' as a categorical(factor variable) with order based on 'week_period'
    week_order = full_miles_week.sort_values('week_period')['week_label'].unique()
    full_miles_week['week_label'] = pd.Categorical(full_miles_week['week_label'], categories=week_order, ordered=True)

    
    return full_miles_week


############### Minutes per week grouped by cardio and weights ###############
def gen_mins_df(aw_final):
    mins_week = (aw_final[
            (aw_final['activity_type'].notna()) &
            (aw_final['metric'] == "Duration") &
            (aw_final['month'] > "2025-06")]
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
        time_filter=lambda df: df['month'] > "2025-06",
        category_values=['Cardio', 'Weights'])
    
        
    # Create a string label for display
    full_mins_week['week_label'] = full_mins_week['week_period'].dt.strftime('%b %d')

    # Set 'week_label' as a categorical(factor variable) with order based on 'week_period'
    week_order = full_mins_week.sort_values('week_period')['week_label'].unique()
    full_mins_week['week_label'] = pd.Categorical(full_mins_week['week_label'], categories=week_order, ordered=True)
    
    return full_mins_week


############### Minutes per week for all exercises ############### 
def gen_workout_time_df(aw_final):
    workout_time = aw_final[(aw_final['StartDate'].dt.year >= 2025) & 
                            (aw_final['metric'] == 'Duration')].groupby(['week_period'])['value'].agg(Time='sum', n='count').reset_index()
    workout_time['Time'] = workout_time['Time'].round(2)

    return workout_time


############### Activity Treemap ############### 
def gen_activity_treemap_df(aw_final):

    activites = ['Running', 'Cycling', 'TraditionalStrengthTraining', 'Swimming']
    
    #Gathering 5 weeks ago statistic to filter treemap
    today = pd.Timestamp.today() # IDk how this number doesn't match what's showing on my webpage
    five_week_ago = (today - pd.DateOffset(weeks=5)).normalize() # Normalize sets the time to midnight

    activity_distribution = (aw_final[
            (aw_final['metric'] == "Duration") & 
            (aw_final['activity'].isin(activites)) &   
            (aw_final['month'] >= "2025-03")]
            #(aw_final['StartDate'] >= five_week_ago)]
        .sort_values(by='StartDate', ascending=False)
        .groupby(['activity'])['value']
        .agg(count='count')
        .reset_index())
                
    # Add percent of total column
    total = activity_distribution['count'].sum()
    activity_distribution['percent'] = activity_distribution['count'] / total

    # Format labels as "Activity<br>Count (Percent)"
    activity_distribution['label'] = activity_distribution.apply(lambda row: f"{row['activity']}<br>{row['count']} ({row['percent']:.1%})", axis=1)

    return activity_distribution


############### Steps per day boxplot ###############
def gen_steps_month_df():

    # Read from SQLite and parse those columns as datetime
    with engine.connect() as connection:
        apple = pd.read_sql_query(
            text("""SELECT type, value, startDate, endDate 
                FROM apple_data_raw
                WHERE type = 'StepCount' AND value IS NOT NULL and startDate >= '2025-01-01'
                ORDER BY startDate DESC"""), connection,
            parse_dates=['startDate', 'endDate'])
        

    # Group by date (not datetime)
    steps_day = apple.groupby(apple['startDate'].dt.date)['value'].agg(steps='sum', n='count').reset_index()

    # Convert 'startDate' to datetime
    steps_day['startDate'] = pd.to_datetime(steps_day['startDate'])

    # Extract month as a period for correct ordering
    steps_day['month_period'] = steps_day['startDate'].dt.to_period('M')

    # Create a string label for display
    steps_day['month_label'] = steps_day['month_period'].dt.strftime('%b %Y')

    # Set 'month_label' as a categorical(factor variable) with order based on 'month_period'
    month_order = steps_day.sort_values('month_period')['month_label'].unique()
    steps_day['month_label'] = pd.Categorical(steps_day['month_label'], categories=month_order, ordered=True)

    return steps_day



############### KPI Statisitcs Functions ###############

# Going to have to recreate this function with apple workout data
def get_kpi_stats(steps_day):
    # Get today's date
    today = pd.Timestamp.today()

    # Get this month and last month as Periods
    this_month = today.to_period('M')
    last_month = (today - pd.DateOffset(months=1)).to_period('M')
    three_mon_ago = (today - pd.DateOffset(months=3)).normalize() # Normalize sets the time to midnight


    # Since I just want to get straight count numbers for this db, I can use the shape funciton to get row count
    wokrout_count_CM = aw_final[(aw_final['month'] == this_month) & (aw_final['metric'] == 'Duration')].shape[0]
    workout_count_LM = aw_final[(aw_final['month'] == last_month) & (aw_final['metric'] == 'Duration')].shape[0]
    workout_count_year = aw_final[(aw_final['StartDate'].dt.year >= 2025) & (aw_final['metric'] == 'Duration')].shape[0]

    # Average daily step count last 3 months
    steps_L3_mon = steps_day[steps_day["startDate"] >= three_mon_ago]
    steps_L3_mon = steps_L3_mon["steps"].mean().round(0).astype("int")

    # Gather workout time metrics
    workout_time = aw_final[(aw_final['metric'] == 'Duration')].groupby(['week_period'])['value'].agg(Time='sum', n='count').reset_index()
    workout_time = workout_time[workout_time["week_period"] >= three_mon_ago] # Taking the last 3 months of data 
    workout_time_hrs_avg = (workout_time["Time"].mean()/60).round(2) 

    # Gather names for above statistic

    current_month_name = today.month_name()
    last_month_name = (today - pd.DateOffset(months=1)).strftime('%B')  

    return workout_count_year, workout_count_LM, wokrout_count_CM, current_month_name, last_month_name, workout_time_hrs_avg, steps_L3_mon




############### Dynamic Visuals Functions ###############

# Generates a table for the dynamic exercise filter page 
def specific_exercise_filter(specific_exercise):

    columns = ['entry_id', '10RM', 'comment', 'effort', 'reps', 'sets', 'weight', 'workout_type']
    workout_df_total = pd.DataFrame(columns=columns)

    with engine.connect() as connection:

        entry_ids = pd.read_sql_query(text("SELECT ha.entry_id FROM habit_answers ha WHERE answer = :exercise"), connection, params={"exercise": specific_exercise})

        entry_ids = entry_ids['entry_id'].tolist()

        for id in entry_ids:
            workout_df = pd.read_sql_query(text("SELECT * FROM habit_answers ha WHERE entry_id = :id"), connection, params={"id": id})

            workout_df = workout_df[['entry_id', 'question', 'answer']]

            workout_df = workout_df.pivot(index='entry_id', columns='question', values='answer').reset_index() 

            workout_df_total = pd.concat([workout_df_total, workout_df], ignore_index=True)

        habit_entries = pd.read_sql_query(text("SELECT * FROM habit_entries"), connection)

        workout_df_total = workout_df_total.merge(habit_entries, left_on='entry_id', right_on='id', how='left')

        workout_df_total = workout_df_total[["log_date", "workout_type", "weight", "sets", "reps", "effort", "comment"]]

        # Getting rid of the nan values 
        workout_df_total['comment'] = workout_df_total['comment'].str.replace("nan", "")

        # Convert the timestamp variable to a datetime format, i'm unsure why I have to do this because that's how it's coded and uploaded in the databse
        workout_df_total['log_date'] = pd.to_datetime(workout_df_total['log_date'])
        
        # Sort the values by date for the table before conert to string output
        workout_df_total = workout_df_total.sort_values('log_date')

        # Then I convert that that datetime variable into a more readable string format/might even decide I don't want to display hours and minutes
        workout_df_total['log_date'] = workout_df_total['log_date'].dt.strftime('%B %d, %Y')

        # Rename columns for clarity
        workout_df_total.columns = ['Timestamp', 'Exercise', 'Weight', 'Sets', 'Reps', 'Effort Level', 'Notes:']

        # Formatting weight variable to show 1 decimal place only if it exits, otherwise I make it a string and strip the '.' and ending '0'
        # Idk how I feel about this as I lose weight as a numeric varaible but should be contained in this function only
        #workout_df_total['weight'] = workout_df_total['weight'].apply(lambda w: f"{w:.1f}".rstrip('0').rstrip('.') if pd.notnull(w) else '')

    return workout_df_total.to_html(classes='workout-table', index=False, border=1)


def generate_excise_options():
    # Get unique exercises for dropdown

    with engine.connect() as connection:
        workouts = pd.read_sql_query(
            text("""SELECT DISTINCT answer FROM habit_answers
                WHERE question = 'workout_type'"""), connection)
        
        exercise_options = sorted(workouts['answer'].dropna().tolist())

    return exercise_options