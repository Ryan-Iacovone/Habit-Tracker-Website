from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from zoneinfo import ZoneInfo
import pandas as pd
from itertools import product
from pandas.api.types import CategoricalDtype
from sqlalchemy import create_engine, text
from db import engine

# Update the list of book titles table in my database with any potential new entries
def load_book_options():

    # read_sql_query simple 
    with engine.connect() as connection:
        books_options = pd.read_sql_query(
            text("""SELECT DISTINCT answer FROM habit_answers
                    WHERE question = 'book_title'
                    ORDER BY answer"""), connection)
        
    book_titles = books_options["answer"].to_list()

    # Add an "Other" option to the list of book titles because 'other' is not saved to the database
    book_titles.append("Other") 

    return book_titles


# List to log existing workouts from db
def load_workout_options(category: int):

    with engine.connect() as connection:
        workouts = pd.read_sql_query(
            text("""SELECT DISTINCT answer FROM habit_answers
                    WHERE question = 'workout_type'
                    ORDER BY answer"""), connection)
        
    workouts_list = workouts['answer'].tolist()

    # Adding some logic to use this function multiple places depending on whether I need an "Other" option or not 
    if category == 0:
        pass
    elif category == 1:
        # Add "Other" option to the list of book titles and works. This way other is not saved to the database
        workouts_list.append("Other")        

    return workouts_list



# Read in cleaned Apple Workouts data 
def Read_Apple_Workouts():

    # Read in the data and parse datetime columns
    with engine.connect() as connection:
        aw_all = pd.read_sql_query(
            text("""SELECT * FROM apple_workouts"""),
            connection)
            #dtype={"workout_id": "Int64"}) # Converting workout_id to Int64 upon entry, will need again if workout_id includes blanks
        
    # Converting the string datetime variable from db to with timezone normalization to UTC then converting to EST
    # This is needed because of combination of EST and EDT in the data 
    # I could do this with a parse dates function in pd.read_sql_query() function above
    date_cols = ["StartDate"]
    for col in date_cols:
        aw_all[col] = (
            pd.to_datetime(aw_all[col])
            .dt.tz_localize("UTC")
            .dt.tz_convert("US/Eastern"))
    

    # Creating a month categorical variable
    # Create a string label for display
    aw_all['month'] =  aw_all['StartDate'].dt.strftime('%b %Y') # Need .dt for series/panda 
    # Certainly 1 way to get month from datetime but keep it as a datetime variable lol
    aw_all['month_date'] =  pd.to_datetime(aw_all['month'], format='%b %Y') # Need .dt for series/panda
    # Need to localize datetime to US/Eastern
    aw_all['month_date'] = aw_all['month_date'].dt.tz_localize("US/Eastern")
    # Set 'month' as a categorical(factor variable) with order based on 'month_date'
    month_order = aw_all.sort_values('month_date')['month'].unique()
    aw_all['month'] = pd.Categorical(aw_all['month'], categories=month_order, ordered=True)

    # Creating a week categorical variable
    # calculating out necessary time metrics when reading in apple workouts data
    ## calculates how many days each weekday is from monday and subtracts that from the orignal date to get back to start of the week Monday
    aw_all['week_date'] = (
        aw_all['StartDate'] - pd.to_timedelta(aw_all['StartDate'].dt.weekday, unit="D") # dt.weekday uses Monday as 0 
    ).dt.normalize()
        # Create a string label for display
    aw_all['week'] = aw_all['week_date'].dt.strftime('%b %d')
    # Set 'week_label' as a categorical(factor variable) with order based on 'week_period'
    week_order = aw_all.sort_values('week_date')['week'].unique()
    aw_all['week'] = pd.Categorical(aw_all['week'], categories=week_order, ordered=True)

    return aw_all

aw_all = Read_Apple_Workouts()


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


############### Frequency bar chart grouped by exercise type and month ###############
def gen_month_freq_df(aw_all, l_7_m):
    activities = ["Walking", "Cycling", "TraditionalStrengthTraining", "Running", "Swimming"]

    df_counts = (aw_all[(aw_all['metric'] == 'Duration') & (aw_all['activity'].isin(activities)) & 
                        (aw_all['month_date'] > l_7_m)]
                        .groupby(['month_date', 'activity'], observed=True) # Include only combinations that actually occur in the data
                        .size() 
                        .reset_index(name='n'))

    month_count_data = fill_missing_combinations(
        original_df=df_counts,
        aggregated_df=df_counts,
        time_col='month_date',
        category_col='activity',
        value_cols=['n'])

    month_count_data['n'] = month_count_data['n'].astype(int)  # Convert to int for better readability

    # Adding a label for 'TraditionalStrengthTraining' top shorten it for the graph output
    month_count_data['activity'] = month_count_data['activity'].replace({'TraditionalStrengthTraining': 'Weights'})

    # Merging in categorical month label
    month_count_data = pd.merge(month_count_data,
        aw_all[['month', 'month_date']].drop_duplicates(),
        on='month_date',
        how='left')

    return month_count_data



############### Frequency bar chart grouped by exercise type and week ###############
""" def gen_week_freq_df(aw_all, l_3_m):
    activities = ["Walking", "Cycling", "TraditionalStrengthTraining", "Running", "Swimming"]

    df_counts = (aw_all[(aw_all['metric'] == 'Duration') & (aw_all['activity'].isin(activities)) & (aw_all['week_date'] > l_3_m)]
        .groupby(['week_date', 'activity'])
        .size()
        .reset_index(name='n'))

    week_count_data = fill_missing_combinations(
        original_df=df_counts,
        aggregated_df=df_counts,
        time_col='week_date',
        category_col='activity',
        value_cols=['n'])

    week_count_data['n'] = week_count_data['n'].astype(int)  # Convert to int for better readability

    # Adding a label for 'TraditionalStrengthTraining' top shorten it for the graph output
    week_count_data['activity'] = week_count_data['activity'].replace({'TraditionalStrengthTraining': 'Weights'})

    week_count_data = pd.merge(week_count_data,
        aw_all[['week', 'week_date']].drop_duplicates(),
        on='week_date',
        how='left')

    return week_count_data """




############### Distance per week grouped by exercise type ###############
def gen_distance_df(aw_all, l_3_m):

    miles_week = (aw_all[(aw_all['activity'].isin(['Running', 'Cycling'])) & (aw_all['metric'].str.contains("Distance")) & (aw_all['week_date'] >= l_3_m)]
        .groupby(['activity', 'week_date'])['value']
        .agg(Total_Miles='sum', n='count')  # compute both mean and count
        .round(2) # Round to 2 decimal places
        .reset_index())


    full_miles_week = fill_missing_combinations(
        original_df=miles_week,
        aggregated_df=miles_week,
        time_col='week_date',
        category_col='activity',
        value_cols=['Total_Miles', 'n'])


    full_miles_week = pd.merge(full_miles_week,
        aw_all[['week', 'week_date']].drop_duplicates(),
        on='week_date',
        how='left')

    
    return full_miles_week


############### Workout time grouped by workout type, specified with specific exercise ###############
def gen_mins_df(aw_all, l_3_m):

    full_mins_cardio = (aw_all[
            (aw_all['activity_type'] == "Cardio") &
            (aw_all['metric'] == "Duration") &
            (aw_all['week_date'] >= l_3_m)]
        .groupby(['activity', 'week_date'])['value']
        .agg(Total_min='sum', n='count')  # compute sum and count
        .round(2)  # Round to 2 decimal places
        .reset_index())


    ## Weight df
    full_mins_weight = (aw_all[
            (aw_all['activity_type'] == "Weights") &
            (aw_all['metric'] == "Duration") &
            (aw_all['week_date'] >= l_3_m)]
        .groupby(['activity', 'week_date'])['value']
        .agg(Total_min='sum', n='count')  # compute sum and count
        .round(2)  # Round to 2 decimal places
        .reset_index())

    ## Changing Total_min from float to rounded int
    full_mins_cardio["Total_min"] = round(full_mins_cardio["Total_min"], 0).astype("int64")

    ## Offsetting the weekdate so I can plot both cardio and weight bars on the same graph
    full_mins_cardio['x_nudged']  = full_mins_cardio['week_date']  - timedelta(days=1)
    full_mins_weight['x_nudged'] = full_mins_weight['week_date'] + timedelta(days=1)
    
    # Calculating total minutes per week for cardio workouts (used to set y axis max and label calculation)
    total_mins = full_mins_cardio.groupby(['week_date'])['Total_min'].agg(week_min='sum')

    # Instituing some quality of life for my legend
    y_cush = 50 
    y_max = int(y_cush + max(total_mins["week_min"]))

    # Merging total cardio mins for each week to full_mins_cardio and renaming to cardio_labels 
    cardio_labels = pd.merge(full_mins_cardio, total_mins, on= "week_date", how="left") 

    # Calculating the percetnage of cardio time spent on each activity for each week 
    cardio_labels["percent_time"] = round(cardio_labels["Total_min"] / cardio_labels["week_min"] * 100, 2)

    # Sorting cardio_labels by week_date and activity for cumcum calculation to match how activities are stacked on barplot 
    cardio_labels = cardio_labels.sort_values(by=['week_date', 'activity'], ascending=[True, False])
    cardio_labels["cumsum_min"] = cardio_labels.groupby('week_date')['Total_min'].cumsum()

    return full_mins_cardio, cardio_labels, full_mins_weight, y_max 


############### Minutes per week for all exercises ############### 
def gen_workout_time_df(aw_all, l_3_m):
    workout_time = (
        aw_all[(aw_all['week_date'] > l_3_m) & (aw_all['metric'] == 'Duration')]
        .groupby('week_date', observed=True)['value']
        .agg(Time='sum', n='count')
        .round(2)
        .reset_index())

    workout_time = pd.merge(workout_time,
        aw_all[['week', 'week_date']].drop_duplicates(),
        on='week_date',
        how='left')

    return workout_time


############### Activity Treemap ###############  
def gen_activity_treemap_df(aw_all, l_3_m):

    activites = ['Running', 'Cycling', 'TraditionalStrengthTraining', 'Swimming']

    activity_distribution = (aw_all[
            (aw_all['metric'] == "Duration") & 
            (aw_all['activity'].isin(activites)) & 
            (aw_all['week_date'] >= l_3_m)] # Filtering by the last 3 months
        .groupby(['activity'])['value']
        .agg(n='count')
        .reset_index())
                
    # Add percent of total column
    total = activity_distribution['n'].sum()
    activity_distribution['percent'] = activity_distribution['n'] / total

    # Format labels as "Activity<br>Count (Percent)"
    activity_distribution['label'] = activity_distribution.apply(lambda row: f"{row['activity']}<br>{row['n']} ({row['percent']:.1%})", axis=1)

    return activity_distribution


############### Daily Step count grouped by month boxplot ###############
def gen_steps_month_df(l_1_y):

    # Calculating steps per day in SQLite, then using localtime function to get to EST from UTC
    with engine.connect() as connection:
        apple_steps = pd.read_sql_query(
            text("""SELECT type, sum(value) as 'value', date(startDate, 'localtime') as 'date', DATETIME(startDate, 'start of month') as 'month_date'
                    FROM apple_data_raw
                    WHERE type = 'StepCount' AND value IS NOT NULL and date(startDate, 'start of month','+1 month','-1 day') >= :t_filter
                    GROUP BY date(startDate)
                    ORDER BY 'date'"""), connection,
            dtype={"value": "int64"},
            params={"t_filter": l_1_y},
            parse_dates=['date', 'month_date'])

    # Localizing date and month_date to US/Eastern because already convert to localtime in the SQL query
    apple_steps['date'] = apple_steps['date'].dt.tz_localize("US/Eastern")
    apple_steps['month_date'] = apple_steps['month_date'].dt.tz_localize("US/Eastern")

    # Creating a month categorical variable
    apple_steps['month'] = apple_steps['date'].dt.strftime('%b %Y') # Need .dt for series/panda

    # Set 'month' as a categorical(factor variable) with order based on 'month_date'
    month_order = apple_steps.sort_values('month_date')['month'].unique()
    apple_steps['month'] = pd.Categorical(apple_steps['month'], categories=month_order, ordered=True)

    return apple_steps



############### KPI Statisitcs Functions ###############

# Going to have to recreate this function with apple workout data
def get_kpi_stats(apple_steps, l_3_m):

    # gathering some date statistics for filtering but I'm not sure I like this method :/
    today = datetime.now(tz=ZoneInfo("US/Eastern"))

    this_month = today.strftime('%b %Y')
    last_month = (today - relativedelta(months=1)).strftime('%b %Y')
    current_year = int(today.strftime('%Y'))
    duration_length = 10

    # Gathering wokrout counts (classifying a true workout to be greater than 10 minutes long)
    ## Current Month Workout Count
    wokrout_count_CM = len(aw_all[(aw_all['month'] == this_month) & (aw_all['metric'] == 'Duration') & (aw_all['value'] >= duration_length)])
    ## Last month Workout Count
    workout_count_LM = len(aw_all[(aw_all['month'] == last_month) & (aw_all['metric'] == 'Duration') & (aw_all['value'] >= duration_length)])
    ## Current Year Workout Count
    workout_count_year = len(aw_all[(aw_all['StartDate'].dt.year == current_year) & (aw_all['metric'] == 'Duration') & (aw_all['value'] >= duration_length)])

    # Average daily step count last 3 months
    steps_L3_mon = apple_steps[apple_steps['date'] >= l_3_m]['value'].mean().round(0).astype("int")

    # Gather average weekly time spent working out using last 3 months data
    workout_time_df = aw_all[(aw_all['metric'] == 'Duration') & (aw_all['week_date'] > l_3_m) ].groupby(['week_date'])['value'].agg(Time='sum', n='count').reset_index()
    workout_time_hrs_avg = (workout_time_df["Time"].mean()/60).round(2)

    # Gather names for above statistic
    current_month_name = today.strftime('%B')
    last_month_name = (today - relativedelta(months=1)).strftime('%B') 

    return workout_count_year, workout_count_LM, wokrout_count_CM, current_month_name, last_month_name, workout_time_hrs_avg, steps_L3_mon



############### Filtered Exercise HTML Table ###############

# Generates a table for the dynamic exercise filter page 
def specific_exercise_filter(specific_exercise):

    columns = ['entry_id', '10RM', 'comment', 'effort', 'reps', 'sets', 'weight', 'workout_type']
    workout_df_total = pd.DataFrame(columns=columns)

    with engine.connect() as connection:
        entry_ids = pd.read_sql_query(text("SELECT ha.entry_id FROM habit_answers ha WHERE answer = :exercise"), connection, params={"exercise": specific_exercise})
        entry_ids = entry_ids['entry_id'].tolist()

        for id in entry_ids:
            workout_df = pd.read_sql_query(text("SELECT entry_id, question, answer FROM habit_answers ha WHERE entry_id = :id"), connection, params={"id": id})
            workout_df = workout_df.pivot(index='entry_id', columns='question', values='answer').reset_index() 
            workout_df_total = pd.concat([workout_df_total, workout_df], ignore_index=True)

        habit_entries = pd.read_sql_query(text("SELECT log_date, id FROM habit_entries"), connection)

        # Merging and selecting relevant columns
        workout_df_total = pd.merge(workout_df_total, habit_entries, left_on='entry_id', right_on='id', how='left')[["log_date", "workout_type", "weight", "sets", "reps", "effort", "comment"]]

        workout_df_total['comment'] = workout_df_total['comment'].str.replace("nan", "")

        workout_df_total.rename(columns={'log_date': 'Timestamp', 'workout_type': 'Exercise', 'weight': 'Weight', 'sets': 'Sets', 'reps': 'Reps',
                                'effort': 'Effort Level', 'comment': 'Notes:'}, inplace=True)

        # reading in 10RM workouts to add 
        ten_rm_additions = pd.read_sql_query(
            text("""SELECT tc.completion_date as Timestamp, tp.exercise_name as Exercise, tp.target_weight as Weight, tp.sets as Sets, tp.reps as Reps, tc.notes as 'Notes:' 
                    FROM tenrm_completions tc
                    LEFT JOIN tenrm_plans tp 
                        ON tp.id = tc.plan_id
                    WHERE tp.exercise_name = :exercise
                    AND tc."timestamp" = (
                            SELECT MAX(tc2."timestamp")
                            FROM tenrm_completions tc2
                            -- Correlated Subquery
                            -- This works because we loop through plan_ids in orig table until it equals max plan_id
                            WHERE tc2.plan_id = tc.plan_id)"""), connection, params={"exercise": specific_exercise})

        # Adding in effort level as a blank variable since 10rm data doesn't track that
        ten_rm_additions['Effort Level'] = ""

        # Combining original workouts with 10rm workouts (Since they have the same columns and format) 
        combined_works = pd.concat([workout_df_total, ten_rm_additions], ignore_index=True) 

        # Convert the timestamp variable to a datetime format ( Could have done this sql query with parse dates too)
        combined_works['Timestamp'] = pd.to_datetime(combined_works['Timestamp'])

        # Sort the combined_works table by date before converting to string output (for readability)
        combined_works = combined_works.sort_values('Timestamp')

        # Converting Timestamp into readable string format (flexability to display time however I want
        combined_works['Timestamp'] = combined_works['Timestamp'].dt.strftime('%B %d, %Y')

    return combined_works.to_html(classes='workout-table', index=False, border=1)