# Standard Libraries
import os
import io
import json
import base64
from datetime import datetime, timedelta
import pytz

# Flask
from flask import Flask, render_template, request, jsonify, send_file

# Local database import
from db import engine, init_db 

# Data Handling
import pandas as pd
import numpy as np
from zoneinfo import ZoneInfo
from sqlalchemy import text, MetaData, Table, Column, Integer, String, Text, Date, DateTime, func, insert
from data_cleaning import load_book_options, load_workout_options, specific_exercise_filter, \
    gen_steps_month_df, get_kpi_stats # only a df with options for a dropdown

# Visualizations
import matplotlib.pyplot as plt
import plotly.graph_objs as go
import plotly.io as pio
from visualization import Monthly_Freq_BarChart, Distance_BarChart, Minutes_BarChart, Minutes_LineGraph, activity_treemap, Steps_Boxplot, l_1_y, l_3_m


app = Flask(__name__)

########### Statically defining list of habits and their associated questions ########### 

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
    "dental": {
        "questions": [
            {"id": "habit_date", "text": "Date:", "type": "date", "required": True},
            {"id": "brushed", "text": "Did you brush your teeth?", "type": "checkbox"},
            {"id": "flossed", "text": "Did you floss?", "type": "checkbox"},
            {"id": "mouthwash", "text": "Did you use mouthwash?", "type": "checkbox"}
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
            {"id": "stretch_type", "text": "Stretch:", "type": "select", "required": True, "options": ["PT-SP Ankle Stabliziation", "Heel Drop"]},
            {"id": "comment", "text": "Notes:", "type": "text"}
        ]
    },
    "Acne": {
        "questions": [
            {"id": "habit_date", "text": "Date:", "type": "date", "required": True},
            {"id": "time", "text": "Time of Day:", "type": "select", "required": True, "options": ["Morning", "Evening", "Both"]},
            {"id": "medication_type", "text": "Medication:", "type": "select", "required": True, "options": ["Benzoyl Peroxide", "Tretinoin", "Cleanser", "Ketoconazole - Face", "Ketoconazole - Arm"]},
            {"id": "comment", "text": "Notes:", "type": "text"}
        ]
    }
}


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
    sever_time_utc = datetime.now(tz=ZoneInfo("UTC")).strftime('%Y-%m-%d %H:%M:%S') + ".000000"

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
        sever_time_utc = datetime.now(tz=ZoneInfo("UTC")).strftime('%Y-%m-%d %H:%M:%S') + ".000000"
        
        # Extracting habit name and date for input into db later 
        habit_name = form_data.pop("habit_type", "unknown")
        habit_date = form_data.pop("habit_date", datetime.now().strftime('%Y-%m-%d'))

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


########### visualization page for all apple workouts ###########
@app.route('/overview_visualizations', methods=['GET', 'POST'])
def overview_visualization_page():
    month_frequency_plot_url = Monthly_Freq_BarChart()
    #week_frequency_plot_url = Weekly_Freq_BarChart()
    distance_plot_url = Distance_BarChart()
    mins_plot_url = Minutes_BarChart()
    #total_mins_plot_url = Minutes_LineGraph()  
    treemap_plotly_html = activity_treemap()
    steps_boxplot_url = Steps_Boxplot()

    # Bringing in steps df primarily used in visualization section here for KPI analysis
    apple_steps = gen_steps_month_df(l_1_y)

    workout_count_year, workout_count_LM, wokrout_count_CM, current_month_name, last_month_name, workout_time_hrs_avg, steps_L3_mon = get_kpi_stats(apple_steps, l_3_m)

    return render_template('overview_visualizations.html',
                          #KPIs 
                          ytd_count = workout_count_year,
                          mtd_count_LM = workout_count_LM,
                          mtd_count = wokrout_count_CM,
                          workout_time_avg=workout_time_hrs_avg,
                          steps_L3_mon = steps_L3_mon,

                          # Month names
                          current_month_name=current_month_name, 
                          last_month_name=last_month_name,

                          # HTML Tables
                          #days_per_month_html=days_per_month_html, 
                          #workouts_by_month_html=workouts_by_month_html,

                          # Plots 
                          month_frequency_plot_url=month_frequency_plot_url,
                          #week_frequency_plot_url=week_frequency_plot_url,
                          distance_plot_url=distance_plot_url,
                          mins_plot_url=mins_plot_url,
                          #total_mins_plot_url=total_mins_plot_url,
                          treemap_plotly_html = treemap_plotly_html,
                          steps_boxplot_url = steps_boxplot_url)


########### 10 RM workouts page ###########
@app.route('/10rm_tracker', methods=['GET'])
def tenrm_tracker():
    
    with engine.connect() as connection:
        # Get all workout plans with their latest completion status
        all_10rms = pd.read_sql_query(
            text("""
                SELECT tp.id, tp.workout_type, tp.week_number, tp.exercise_name, tp.target_weight, tp.sets, tp.reps, tc.completion_date, tc.completed, tc.notes
                FROM tenrm_plans tp
                LEFT JOIN tenrm_completions tc 
                ON tp.id = tc.plan_id
                ORDER BY tp.workout_type, tp.week_number, tp.exercise_name
                """),
            connection)
        
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
        sever_time_utc = datetime.now(tz=ZoneInfo("UTC")).strftime('%Y-%m-%d %H:%M:%S') + ".000000"
        
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


# Clean shutdown of DB connections
@app.teardown_appcontext
def shutdown_session(exception=None):
    # Add a PRAGMA wal_checkpoint call (or VACUUM if you want compaction) in your teardown so WAL pages are flushed to the main DB file.
    with engine.connect() as conn:
        conn.execute(text("PRAGMA wal_checkpoint(FULL);"))
    engine.dispose()

if __name__ == '__main__':
    init_db()  # Initialize sql database when the app starts for the first time (taken from db.py)
    app.run(debug=True, host="0.0.0.0", port=8501) 