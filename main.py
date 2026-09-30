# Standard library imports
import datetime as dt
import calendar 
import time
import markdown

# Flask
from flask import Flask, render_template, request, jsonify

# Local variable/function import
from core.functions import engine, init_db, workout_theme

# Data Handling
import pandas as pd
import numpy as np
from zoneinfo import ZoneInfo
from sqlalchemy import text

# Visualizations
import matplotlib
matplotlib.use('Agg')  # use non-GUI backend for Flask app
import matplotlib.pyplot as plt
import plotly.graph_objs as go
import plotly.io as pio
from plotnine import *
import base64
import io


app = Flask(__name__)

# Gunicorn must preload the app so database initialization runs once before workers fork.
init_db()


########### Statically defining list of habits and their associated questions ########### :) 

# Defining helper functions 

## Grabbing list of book titles for new habit logging
def load_book_options():

    # read_sql_query simple 
    with engine.connect() as connection:
        books_options = pd.read_sql_query(
            text("""
                SELECT DISTINCT answer FROM habit_answers
                WHERE question = 'book_title'
                ORDER BY answer
                    """), connection)
        
    book_titles = books_options["answer"].to_list()

    # Add an "Other" option to the list of book titles because 'other' is not saved to the database
    book_titles.append("Other")

    return book_titles


## Defining list of workout options to choose from both for logging workout habit and viewing workout exercises
def load_workout_options(category: int):

    with engine.connect() as connection:
        workouts = pd.read_sql_query(
            text("""
                SELECT DISTINCT answer FROM habit_answers
                WHERE question = 'workout_type'
                ORDER BY answer
            """), connection)
        
    workouts_list = workouts['answer'].tolist()

    # Adding some logic to use this function multiple places depending on whether I need an "Other" option or not 
    if category == 0:
        pass
    elif category == 1:
        # Add "Other" option to the list of book titles and works. This way other is not saved to the database
        workouts_list.append("Other")        

    return workouts_list


HABITS = {
    "workout": {
        "questions": [
            # Add date selector as the first question for all habits
            {"id": "habit_date", "text": "Date:", "type": "date", "required": True},
            {"id": "workout_type", "text": "Exercise:", "type": "select", "required": True, "options": load_workout_options(1)},
            {"id": "new_workout", "text": "What new workout would you like to log?", "type": "text", "conditional": {"field": "workout_type", "value": "Other"}},
            
            {"id": "weight", "text": "Weight:", "type": "number", "required": True, "step": 0.5}, # step added to allow for decimal inputs rounded to .5S
            {"id": "sets", "text": "Sets:", "type": "number", "required": True},
            {"id": "reps", "text": "Reps:", "type": "number", "required": True},
            {"id": "effort", "text": "Effort Level:", "type": "range", "min": 1, "max": 10, "required": True, 
            "tooltip": """4: No effort 😴 \n
                        5: Easy 🌟 \n
                        6: Moderate effort 💪 \n
                        7: Sweet spot, feel confident 🎯 \n
                        8: Moderately challenging but still completed 🔥 \n
                        9: Very challenging, DNC ⚠️ \n
                        10: Extremely challenging, DNC, go down ⛔"""},
            {"id": "10RM", "text": "10RM Workout?", "type": "checkbox"},
            {"id": "comment", "text": "Notes:", "type": "text"}
        ]
    },
    "reading": {
        "questions": [
            {"id": "habit_date", "text": "Date:", "type": "date", "required": True},
            {"id": "book_title", "text": "What book did you read?", "type": "select", "options": load_book_options()},
            {"id": "custom_title", "text": "What new book would you like to log?", "type": "text", "conditional": {"field": "book_title", "value": "Other"}},
            {"id": "pages", "text": "How many pages did you read?", "type": "number", "required": True}
        ]
    },
    "stretch": {
        "questions": [
            {"id": "habit_date", "text": "Date:", "type": "date", "required": True},
            {"id": "time", "text": "Time of Day:", "type": "select", "required": True, "options": ["Morning", "Evening", "Both"]},
            {"id": "stretch_type", "text": "Stretch:", "type": "select", "required": True, "options": ["Heel Drop", "Wall Calf Stretch", "Ankle Stabilization", "Standing Childs Pose", "Wall Slides", "Triceps Stretch", "Seated Assisted External Rotation", "5lb Shoulder Press", "Floor Slides", "Shoulder Rolls" ]},
            {"id": "comment", "text": "Notes:", "type": "text"}
        ]
    }
}

engine.dispose()


########### Log users IP address after every made request ###########
def get_client_ip():
    """Helper to get the client IP address, accounting for proxies."""
    if request.headers.get("X-Forwarded-For"):
        # Might contain multiple IPs, take the first one
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    return request.remote_addr or "unknown"

@app.before_request
def log_ip():
    ip = get_client_ip()
    endpoint = request.path

    ############# Inputting UTC datetime from server as timestamp variable #############
    ## Converting datetime to strftime format plus adding 0s for proper UTC conversion to sqlite
    sever_time_utc = dt.datetime.now(tz=ZoneInfo("UTC")).strftime('%Y-%m-%d %H:%M:%S') + ".000000"

    with engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO access_log (ip, endpoint, timestamp)
                    VALUES (:ip, :endpoint, :timestamp)"""),
            {"ip": ip, "endpoint": endpoint, "timestamp": sever_time_utc},
        )



########### Default landing to log habits that I statically pass in ###########
@app.route('/')
def index():
    return render_template('index.html', habits=HABITS)

### Dynamically displaying the questions for each habit ###
@app.route('/get_questions', methods=['POST'])
def get_questions():
    habit = request.json.get('habit')
    if habit in HABITS:
        return jsonify(HABITS[habit])
    return jsonify({"error": "Habit not found"}), 404

### Logging habit information from website into sqlite ###
@app.route('/submit_habit', methods=['POST'])
def submit_habit():
    """Receive form data and store it in a normalized SQL structure"""
    try:
        # Convert incoming form data to dict
        form_data = request.form.to_dict()

        ############# Inputting UTC datetime from server as timestamp variable #############
        ## Converting datetime to strftime format plus adding 0s for proper UTC conversion to sqlite
        sever_time_utc = dt.datetime.now(tz=ZoneInfo("UTC")).strftime('%Y-%m-%d %H:%M:%S') + ".000000"
        
        # Extracting habit name and date for input into db later 
        habit_name = form_data.pop("habit_type", "unknown")
        habit_date = form_data.pop("habit_date", dt.datetime.now().strftime('%Y-%m-%d'))

        # Handling new data input via "Other" field and cleaning the input
        if habit_name == "reading":
            if form_data.get("book_title") == "Other":
                form_data["book_title"] = form_data.pop("custom_title", "Other")
            else:
                form_data.pop("custom_title", None)

        if habit_name == "workout":
            if form_data.get("workout_type") == "Other":
                form_data["workout_type"] = form_data.pop("new_workout", "Other")
            else:
                form_data.pop("new_workout", None)

            # Normalize 10RM checkbox
            form_data["10RM"] = form_data.get("10RM") == "on"

        # Start database logic
        with engine.begin() as conn:

            # Grabbing the habit id if the habit exists in the db otherwise, inputting a new observation
            habit_id_result = conn.execute(text("SELECT id FROM habits WHERE name = :name"),
                {"name": habit_name}).fetchone()

            if habit_id_result:
                habit_id = habit_id_result[0]

            # inserting the new habit observation to the db 
            else:
                conn.execute(text("""INSERT INTO habits (name) VALUES (:name)"""),
                    {"name": habit_name})
                
                habit_id = conn.execute(text("""SELECT id FROM habits WHERE name = :name"""),
                    {"name": habit_name}).fetchone()[0] # need the [0] because we're consolidating a step from above

            # Insert into habit_entries
            result = conn.execute(
                text("""INSERT INTO habit_entries (habit_id, log_date, timestamp)
                    VALUES (:habit_id, :log_date, :timestamp)"""),
                {"habit_id": habit_id, "log_date": habit_date, "timestamp": sever_time_utc}
)
            
            entry_id = result.lastrowid  # Retrieves the unique ID of the row that was just inserted into the habit_entries table

            # Insert each question as a separate row
            for question, answer in form_data.items():
                conn.execute(text("""INSERT INTO habit_answers (entry_id, question, answer)
                        VALUES (:entry_id, :question, :answer)"""),
                    {"entry_id": entry_id, "question": question, "answer": str(answer)}) # We cast all answers to string variable before inserting in sql db (meaning I'll have to convert them back later)

        return jsonify({"status": "success",
            "message": "Data saved to normalized database",
            "habit_type": habit_name,
            "log_date": habit_date})

    except Exception as e:
        print("Error in submit_habit:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

    
########### Exercise filter page displays all instances of a selected exercise ###########

# Functionizing exercise filter to take in selected exercise and generates html table
def specific_exercise_filter(specific_exercise):

    columns = ['entry_id', '10RM', 'comment', 'effort', 'reps', 'sets', 'weight', 'workout_type']
    workout_df_total = pd.DataFrame(columns=columns)

    with engine.connect() as connection:
        entry_ids = pd.read_sql_query(
            text("""
                SELECT ha.entry_id 
                FROM habit_answers ha 
                WHERE answer = :exercise
            """), connection, 
            params={"exercise": specific_exercise})
        
        entry_ids = entry_ids['entry_id'].tolist()

        for id in entry_ids:
            workout_df = pd.read_sql_query(
                text("""
                    SELECT entry_id, question, answer 
                    FROM habit_answers ha 
                    WHERE entry_id = :id
                """), connection, 
                params={"id": id})
            
            workout_df = workout_df.pivot(index='entry_id', columns='question', values='answer').reset_index()

            workout_df_total = pd.concat([workout_df_total, workout_df], ignore_index=True)

        habit_entries = pd.read_sql_query(
            text("""
            SELECT log_date, id 
            FROM habit_entries
        """), connection)

        # Merging and selecting relevant columns
        workout_df_total = pd.merge(workout_df_total, habit_entries, left_on='entry_id', right_on='id', how='left')[["log_date", "workout_type", "weight", "sets", "reps", "effort", "comment"]]

        workout_df_total['comment'] = workout_df_total['comment'].str.replace("nan", "")

        workout_df_total.rename(columns={'log_date': 'Timestamp', 'workout_type': 'Exercise', 'weight': 'Weight', 'sets': 'Sets', 'reps': 'Reps',
                                'effort': 'Effort Level', 'comment': 'Notes:'}, inplace=True)

        # reading in 10RM workouts to add 
        ten_rm_additions = pd.read_sql_query(
            text("""
                SELECT tc.completion_date as Timestamp, tp.exercise_name as Exercise, tp.target_weight as Weight, tp.sets as Sets, tp.reps as Reps, tc.notes as 'Notes:' 
                FROM tenrm_completions tc
                LEFT JOIN tenrm_plans tp 
                    ON tp.id = tc.plan_id
                WHERE tp.exercise_name = :exercise
                AND tc."timestamp" = (
                    SELECT MAX(tc2."timestamp")
                    FROM tenrm_completions tc2
                    -- Correlated Subquery
                    -- This works because we loop through plan_ids in orig table until it equals max plan_id
                    WHERE tc2.plan_id = tc.plan_id)
            """), connection, 
            params={"exercise": specific_exercise})

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


@app.route('/exercise_filter', methods=['GET', 'POST'])
def exercise_filter_page(): 
    # Loading in exercise options for user
    exercise_options = load_workout_options(0)
    
    # User choosen exercise (defaults to first exerise in exercise_options list?) 
    selected_exercise = request.form.get('exercise')

    # Generating HTML table for selected exercise
    df_html_table = specific_exercise_filter(selected_exercise)

    return render_template('exercise_filter.html',
                           df_html_table=df_html_table,
                           exercise_options=exercise_options,
                           selected_exercise=selected_exercise)



########### Heart filter visualization page shows heart over time for selected workout ###########   
@app.route('/hr_filter', methods=['GET', 'POST'])
def hr_filter_page(): 

############ Initial workouts list for user to choose from ############
    ## Grabbing the list of workouts from database and applying a nice label
    with engine.connect() as connection:
        workouts = pd.read_sql_query(
            text("""
                SELECT DISTINCT aw.workout_id, DATETIME(aw.StartDate, 'localtime') as date, concat_ws(" ", strftime('%m-%d-%Y', aw.StartDate),  replace(aw.activity, 'TraditionalStrengthTraining', 'Weights')  ) as workout_label
                FROM apple_workouts aw
                WHERE aw.workout_id IS NOT NULL
                ORDER  BY aw.StartDate desc
            """), connection,
            dtype={"workout_id": "int64"},
            parse_dates=['date'])

    ## Converting output options to list 
    workout_options = workouts["workout_label"].to_list()

    
############ Reading in user choosen workout from webapp front end ############
    selected_workout = request.form.get('workout')

    # Stays None (blank) until a workout is picked
    #hr_plot_url = None  

    # Setting the default workout when heart rate page is initally opened 
    if not selected_workout:
        # Selecting the latest workout id to get the correct workout label
        max_id = workouts["workout_id"].max() 

        selected_workout = workouts.loc[workouts["workout_id"] == max_id, "workout_label"].iloc[0]


############ Using the selected workout to get heart rate data for graph and KPIs ############

    ## Grabbing the workout ID of the user selected workout

    #selected_workout_id = workouts[workouts["workout_label"] == selected_workout][["workout_id"]].iloc[0, 0]
    selected_workout_id = workouts.loc[workouts["workout_label"] == selected_workout, "workout_id"].iloc[0]

    ## Finding the start and duration of the selected workout to get start and end date
    with engine.connect() as connection:
        times = pd.read_sql_query(
            text("""
                SELECT aw.workout_id as id, aw.StartDate as start_date, aw.value 
                FROM apple_workouts aw 
                WHERE aw.metric = 'Duration' AND aw.workout_id = :selected_workout_id
            """), connection,
            dtype={"id": "int64"},
            params={"selected_workout_id": int(selected_workout_id)},
            parse_dates=['start_date'])

    ### Adding the duration and start time together get workout end time
    times["end_date"] = times["start_date"] + dt.timedelta(minutes = times["value"].iloc[0] )

    ## Grabbing heart rate values for duration of the workout
    with engine.connect() as connection:
        hr_df = pd.read_sql_query(
            text("""
                SELECT adr.value as 'HeartRate', DATETIME(adr.startDate, 'localtime') as date 
                FROM apple_data_raw adr 
                WHERE adr.type = 'HeartRate' AND
                    adr.startDate BETWEEN :t_low AND :t_upper
                ORDER BY adr.startDate
            """), connection,
            dtype={"HeartRate": "float64"},
            params={"t_low": str( times["start_date"].iloc[0] ), "t_upper": str( times["end_date"].iloc[0] ) },
            parse_dates=['date'])

    ### Calculating elapsed time from the start
    hr_df["run_time"] = hr_df["date"] - hr_df["date"].iloc[0]


############ Building the heartrate plot ############ 
    hr_plot = (ggplot(hr_df, aes('run_time', 'HeartRate')) +
        
        geom_line(size=1.2, color='red') +
        geom_point(size=1.2, color='black') +
        
        geom_smooth(color = "green", span=0.3) +

        # Horizontal lines for HR zones
        geom_hline(yintercept=[130, 145, 160, 180], linetype='dashed', color=['green', 'yellow', 'orange', 'red'], size=0.5) +

        scale_x_datetime(date_labels='%H:%M:%S') +

        labs(title= f"{selected_workout} Workout",
            x="",
            y="Heart Rate",
            fill = "Activity") +

        # Global plotnine workout theme graph 
        workout_theme
        )

    ## Render plot to a matplotlib figure
    fig = hr_plot.draw()

    ## Save figure to buffer
    static_bytes = io.BytesIO()
    fig.savefig(static_bytes, format='png', bbox_inches='tight')
    static_bytes.seek(0)
    static_base64 = base64.b64encode(static_bytes.read()).decode('utf-8')
    hr_plot_url = f"data:image/png;base64,{static_base64}"
    plt.close(fig)


############ Calculating heartrate KPIs ############

    ## Calculate the time difference between each heart rate measurement.
    hr_df["time_delta"] = hr_df["date"].diff()

    ## Formatting functiont to turn total seconds into a "MM:SS" format 
    def format_mmss(total_seconds):
        minutes, seconds = divmod(int(round(total_seconds)), 60)
        return f"{minutes}:{seconds:02d}"  # MM:SS for display

    ### Total workout time (not elapsed time so doesn't include paused time)
    total_seconds = hr_df["time_delta"].sum().total_seconds()
    total_time = round(total_seconds / 60, 2)  # Decimal minutes, kept for percentage calculations.
    total_time_str = format_mmss(total_seconds)

    ### Time in zone 2
    zone2_seconds = hr_df.loc[hr_df["HeartRate"] <= 145, "time_delta"].sum().total_seconds()
    zone2_time = round(zone2_seconds / 60, 2)
    zone2_time_str = format_mmss(zone2_seconds)

    ### Percentage of time in zone 2
    zone2_time_pct = round(zone2_time / total_time * 100, 2)

    ### Time above zone 2
    zone2_above_seconds = hr_df.loc[hr_df["HeartRate"] > 145, "time_delta"].sum().total_seconds()
    zone2_time_above = round(zone2_above_seconds / 60, 2)
    zone2_time_above_str = format_mmss(zone2_above_seconds)

    ### Percentage of time above zone 2
    zone2_time_above_pct = round(zone2_time_above / total_time * 100, 2)

    
##### Additional workout specific KPIs ######
    
    ## Retrieve all relevant values for the selected workout
    with engine.connect() as connection:
        workout_kpis = pd.read_sql_query(
            text("""
                SELECT aw.metric, aw.value, aw.measurement_type, aw.activity_type 
                FROM apple_workouts aw 
                WHERE aw.workout_id = :selected_workout_id
            """), connection,
            params={"selected_workout_id": int(selected_workout_id)}
        )

    #### Pace ####
    workout_distance = workout_kpis.loc[workout_kpis["metric"] == "DistanceWalkingRunning", "value"].sum()

    # Check to ensure we've got a pace number for only walking and running workouts
    if workout_distance > 0:
        pace_seconds = (total_time * 60) / workout_distance
        pace_str = format_mmss(pace_seconds)
    else:
        # Placeholder string when no pace
        pace_str = "--"


    return render_template('hr_filter.html',
                        # Plots 
                        hr_plot_url=hr_plot_url,

                        # Datsets/values
                        workout_options=workout_options, # list of workout options,
                        selected_workout=selected_workout, # Specific workout selected
                        
                        # KPIs
                        total_time = total_time_str,

                        zone2_time = zone2_time_str,
                        zone2_time_pct = zone2_time_pct,

                        zone2_time_above = zone2_time_above_str,
                        zone2_time_above_pct = zone2_time_above_pct,

                        workout_pace_str = pace_str,
                        workout_distance = workout_distance
    )


########### visualization page for all apple workouts ###########
@app.route('/overview_visualizations', methods=['GET', 'POST'])
def overview_visualization_page():

    # Bringing in df of kpis from pre-ran csv file

    #df = pd.read_csv(r'static\kpi_stats.csv')
    df = pd.read_csv('static/charts/kpi_stats.csv')

    workout_count_year = df['workout_count_year'].iloc[0]
    workout_count_LM = df['workout_count_LM'].iloc[0]
    workout_count_CM = df['workout_count_CM'].iloc[0]
    current_month_name = df['current_month_name'].iloc[0]
    last_month_name = df['last_month_name'].iloc[0]
    workout_time_hrs_avg = df['workout_time_hrs_avg'].iloc[0]
    steps_L3_mon = df['steps_L3_mon'].iloc[0]

    # Opening the html file for the treemap visual
    with open("static/charts/activity_treemap.html", "r", encoding="utf-8") as f:
        treemap_plotly_html_read = f.read()

    return render_template('overview_visualizations.html',
                          #KPIs 
                          ytd_count = workout_count_year,
                          mtd_count_LM = workout_count_LM,
                          mtd_count = workout_count_CM,
                          workout_time_avg=workout_time_hrs_avg,
                          steps_L3_mon = steps_L3_mon,

                          # Month names
                          current_month_name=current_month_name, 
                          last_month_name=last_month_name,

                          # HTML Tables
                          #days_per_month_html=days_per_month_html, 
                          #workouts_by_month_html=workouts_by_month_html,

                          # Interactive plots (non png) 
                          treemap_plotly_html = treemap_plotly_html_read
                          )



########### 10 RM workouts page ###########
@app.route('/10rm_tracker', methods=['GET'])
def tenrm_tracker():
    
    with engine.connect() as connection:
        # Get all workout plans with their latest completion status
        all_10rms = pd.read_sql_query(
            text("""
                SELECT tp.id, tp.workout_type, tp.week_number, tp.exercise_name, tp.target_weight, tp.sets, tp.reps, tp.created_date, tc.completion_date, tc.completed, tc.notes, tc.id as tc_id
                FROM tenrm_plans tp
                LEFT JOIN tenrm_completions tc 
                ON tp.id = tc.plan_id
                ORDER BY tp.workout_type, tp.week_number, tp.exercise_name
                """), connection,
        parse_dates=["created_date"])

        # Grabbing the most recent date I uploaded 10 RM plans for each workout type
        ## This can break if I upload workout plans for the same workout type on different days
        workout_type_dates = pd.read_sql_query(
            text("""
                 SELECT tp.workout_type, MAX(tp.created_date) as max_date
                 FROM tenrm_plans tp
                 GROUP BY tp.workout_type
                 """), connection,
            parse_dates=["max_date"])

    # Merging in max max creation date for each workout type. Then filter out workouts that are not current
    all_10rms = pd.merge(all_10rms, workout_type_dates, on='workout_type', how='left')
    all_10rms = all_10rms[all_10rms['created_date'] == all_10rms['max_date']]

    # Sorting values by tc_id in prep to take the last or max value
    # Group by id because that's the plan idea so that for each plan there's only 1 set of completions data we want
    all_10rms = (
        all_10rms
        .sort_values("tc_id")
        .groupby("id", dropna=False)
        .last()
        .reset_index()
    )

        
        # Organize data by workout type and week
    organized_data = {}

    for _, row in all_10rms.iterrows():
        
        workout_type = row['workout_type']
        week_number = row['week_number']

        if workout_type not in organized_data:
            organized_data[workout_type] = {}
        
        if week_number not in organized_data[workout_type]:
            organized_data[workout_type][week_number] = []
        
        organized_data[workout_type][week_number].append({
            'plan_id': row['id'],
            'exercise_name': row['exercise_name'],
            'target_weight': row['target_weight'],
            'sets': row['sets'],
            'reps': row['reps'],
            'completion_date': row['completion_date'],
            'completed': row['completed'],
            'notes': row['notes']
        })
    
    return render_template('10rm_tracker.html', workout_data=organized_data)


### Logging 10 RM exercises I've completed from the plan page
@app.route('/log_10rm_completion', methods=['POST'])
def log_10rm_completion():
    """Log completion of a 10RM workout"""
    try:
        data = request.json
        plan_id = data.get('plan_id')
        completion_date = data.get('completion_date')
        completed = data.get('completed')
        notes = data.get('notes', '')
        
        ############# Inputting UTC datetime from server as timestamp variable #############
        ## Converting datetime to strftime format plus adding 0s for proper UTC conversion to sqlite
        sever_time_utc = dt.datetime.now(tz=ZoneInfo("UTC")).strftime('%Y-%m-%d %H:%M:%S') + ".000000"
        
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO tenrm_completions (plan_id, completion_date, completed, notes, timestamp)
                VALUES (:plan_id, :completion_date, :completed, :notes, :timestamp)"""), 
            {
                'plan_id': plan_id,
                'completion_date': completion_date,
                'completed': completed,
                'notes': notes,
                'timestamp': sever_time_utc
            })
        
        return jsonify({'status': 'success', 'message': 'Completion logged successfully'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



@app.route('/habit_calendar')
def habit_calendar_page():
    # Used to find default month and year
    today = dt.datetime.now(tz=ZoneInfo("EST")).date()

    # Read ?year= and ?month= from the URL, default to current month
    year  = int(request.args.get('year',  today.year))
    month = int(request.args.get('month', today.month))

    # Clamp month to 1–12 in case of edge values (probaby not necessary)
    if month < 1:  month = 1
    if month > 12: month = 12

    # monthrange returns (first_weekday, days_in_month) and we only care about days in month
    days_in_month = calendar.monthrange(year, month)[1]

    # Aligning weeks to match static calendar in html where we start on Monday 
    first_weekday_mon = calendar.weekday(year, month, 1)   # 0=Mon
    
    # calendar.weekday() returns 0=Mon, but if we want 0=Sun
    # so shift: Mon->1, Tue->2 ... Sat->6, Sun->0
    #first_weekday_sun = (first_weekday_mon + 1) % 7    # 0=Sun

    # Prev / next month for nav arrows
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    # Querying relevant habits for specific year and month given
    
    ## Building month and year string based on given month and year to filter habit data to specific month
    ## Formatting string for month ensures there's a leading 0 for months 1-9
    month_start = f"{year}-{month:02d}-01"
    month_end   = f"{year}-{month:02d}-{days_in_month}"

    with engine.begin() as conn:
        mon_habits_df = pd.read_sql("""SELECT he.log_date,  h.name as habit_type, ha.entry_id, ha.question, ha.answer
                            FROM habit_answers ha
                            LEFT OUTER JOIN habit_entries he
                            ON he.id = ha.entry_id
                            LEFT OUTER JOIN habits h
                            ON h.id = he.habit_id
                            WHERE h.name in ('stretch', 'reading') AND ha.question in ('stretch_type', 'book_title') AND he.log_date BETWEEN :start_mon AND :end_mon
                            ORDER BY date(he.log_date ) DESC """, conn,
                        params= {"start_mon": month_start, "end_mon": month_end },
                        parse_dates=["log_date"])

    # Total distinct habits that exist (for "all completed" check)
    # Not sure if this is calculating correctly based on off the json blob
    # And would want to tailor this to specific habits of importance
    total_habits = len(HABITS)

    calendar_data = {}
    for day in range(1, days_in_month + 1):
        day_date   = dt.datetime(year, month, day)
        is_future  = day_date.date() > today
        habits_logged = []
        mon_habits_df_filt = mon_habits_df[mon_habits_df["log_date"] == day_date]

        for habit_type, group in mon_habits_df_filt.groupby("habit_type"):

            if habit_type == "reading":
                book    = group.loc[group["question"] == "book_title",  "answer"].values
                #pages   = group.loc[group["question"] == "pages",       "answer"].values
                tooltip = f"{book[0]}: page_holder"

            elif habit_type == "stretch":
                stretches = group.loc[group["question"] == "stretch_type", "answer"].values
                #times     = group.loc[group["question"] == "time",  "answer"].values

                tooltip = ""
                for stretch in stretches:
                    tooltip += f"{stretch}: time\n"

            else:
                tooltip = habit_type.title()

            habits_logged.append({
                "habit_type":   habit_type,
                "display_name": habit_type.title(),
                "tooltip":      tooltip,
            })

        #habits_logged = mon_habits_df[mon_habits_df["log_date"] == day_date]["habit_type"].unique().tolist()        
        # habits_logged = mon_habits_df.loc[mon_habits_df["log_date"] == day_date, "habit_type"].unique().tolist()

        count = len(habits_logged)

        # Calculating habit completion status for each day
        if is_future:
            status = "future"
        elif count == 0:
            status = "missed"
        # Setting completed status as 2 logged habits because I'm only tracking reading and stretching 
        elif count >= 2:
            status = "completed"
        else:
            status = "partial"

        calendar_data[day] = {
            "habits": habits_logged,
            "status": status,
            "is_future": is_future,
            }

    # Calculating summary stats for selected month
    days_completed    = sum(1 for d in calendar_data.values() if d["status"] == "completed")
    days_partial      = sum(1 for d in calendar_data.values() if d["status"] == "partial")
    days_missed       = sum(1 for d in calendar_data.values() if d["status"] == "missed")
    total_habits_logged = sum(len(d["habits"]) for d in calendar_data.values())

    return render_template('habit_calendar.html',
        calendar_data    = calendar_data,
        year             = year,
        month            = month,
        month_name       = calendar.month_name[month],
        days_in_month    = days_in_month,
        first_weekday    = first_weekday_mon,
        today_day        = today.day,
        today_month      = today.month,
        today_year       = today.year,
        prev_year        = prev_year,
        prev_month       = prev_month,
        next_year        = next_year,
        next_month       = next_month,
        days_completed   = days_completed,
        days_partial     = days_partial,
        days_missed      = days_missed,
        total_habits_logged = total_habits_logged,
    )


@app.route('/coding_cheatsheet')
def hidden_cheatsheet():
    cheatsheet_path = "static/coding_cheatsheet.md"

    with open(cheatsheet_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Converting markdown file to HTML (actually works pretty well!)
    html_cheatsheet = markdown.markdown(md_text, extensions=["tables"])

    return html_cheatsheet

# Clean shutdown of DB connections
@app.teardown_appcontext
def shutdown_session(exception=None):
    # Remove engine.dispose() entirely — SQLAlchemy manages the pool for you
    # Only checkpoint WAL, which is fine
    try:
        with engine.connect() as conn:
            conn.execute(text("PRAGMA wal_checkpoint(PASSIVE);"))
    except Exception:
        pass  # Don't let teardown errors surface to users

if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=8501)