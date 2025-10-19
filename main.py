# Standard Library
import os
import io
import json
import base64
from datetime import datetime, timedelta
import pytz

# Flask
from flask import Flask, render_template, request, jsonify, send_file

# Database import
from db import engine 

# Data Handling
import pandas as pd
import numpy as np
from sqlalchemy import text, MetaData, Table, Column, Integer, String, Text, Date, DateTime, func, insert
from Data_Cleaning import load_book_options, load_workout_options, generate_excise_options, specific_exercise_filter, \
    gen_steps_month_df, get_kpi_stats # only a df with options for a dropdown

# Visualizations
import matplotlib.pyplot as plt
import plotly.graph_objs as go
import plotly.io as pio
from visualization import Freq_BarChart, Distance_BarChart, Minutes_BarChart, Minutes_LineGraph, activity_treemap, Steps_Boxplot


app = Flask(__name__)


def get_client_ip():
    """Helper to get the client IP address, accounting for proxies."""
    if request.headers.get("X-Forwarded-For"):
        # Might contain multiple IPs, take the first one
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    return request.remote_addr or "unknown"


# ------------- NEW: Log every request’s IP ---------------- #
@app.before_request
def log_ip():
    ip = get_client_ip()
    endpoint = request.path
    eastern = pytz.timezone("America/New_York")
    timestamp = datetime.now(eastern).strftime("%Y-%m-%d %H:%M:%S")

    with engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO access_log (ip, endpoint, timestamp)
                    VALUES (:ip, :endpoint, :timestamp)"""),
            {"ip": ip, "endpoint": endpoint, "timestamp": timestamp},
        )
    # no return → request continues normally


# List of habits I want to document and their associated questions

######## Consideratding adding a new movie/show and new food meal habit to start doing more of that ########

HABITS = {
    "workout": {
        "questions": [
            # Add date selector as the first question for all habits
            {"id": "habit_date", "text": "Date:", "type": "date", "required": True},
            {"id": "workout_type", "text": "Exercise:", "type": "select", "required": True, "options": load_workout_options()},
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

# initalizing habits websites with sql tables needed to support it
def init_db():
    with engine.begin() as conn:

        # habits db creation
        conn.execute(text("""CREATE TABLE IF NOT EXISTS habits (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT UNIQUE NOT NULL);"""))

        # habit_entries db creation 
        conn.execute(text("""CREATE TABLE IF NOT EXISTS habit_entries (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            habit_id INTEGER NOT NULL,
                            log_date DATE NOT NULL,
                            timestamp DATETIME NOT NULL,
                            FOREIGN KEY (habit_id) REFERENCES habits(id));"""))

        # habit_answers db creation 
        conn.execute(text("""CREATE TABLE IF NOT EXISTS habit_answers (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            entry_id INTEGER NOT NULL,
                            question TEXT NOT NULL,
                            answer TEXT NOT NULL,
                            FOREIGN KEY (entry_id) REFERENCES habit_entries(id));"""))
        
        # access log table
        conn.execute(text("""CREATE TABLE IF NOT EXISTS access_log (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            ip TEXT NOT NULL,
                            endpoint TEXT NOT NULL,
                            timestamp DATETIME NOT NULL);"""))


@app.route('/')
def index():
    return render_template('index.html', habits=HABITS)


@app.route('/get_questions', methods=['POST'])
def get_questions():
    habit = request.json.get('habit')
    if habit in HABITS:
        return jsonify(HABITS[habit])
    return jsonify({"error": "Habit not found"}), 404


@app.route('/submit_habit', methods=['POST'])
def submit_habit():
    """Receive form data and store it in a normalized SQL structure"""
    try:
        # Convert incoming form data to dict
        form_data = request.form.to_dict()

        # Using EST to input into server since sqlite defaults to utc
        eastern = pytz.timezone('America/New_York')
        local_time = datetime.now(eastern).strftime('%Y-%m-%d %H:%M:%S')
        
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
                conn.execute(text("INSERT INTO habits (name) VALUES (:name)"),
                    {"name": habit_name})
                
                habit_id = conn.execute(text("SELECT id FROM habits WHERE name = :name"),
                    {"name": habit_name}).fetchone()[0] # need the [0] because we're consolidating a step from above

            # Insert into habit_entries
            result = conn.execute(
                text("""INSERT INTO habit_entries (habit_id, log_date, timestamp)
                    VALUES (:habit_id, :log_date, :timestamp)"""),
                {"habit_id": habit_id, "log_date": habit_date, "timestamp": local_time}
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

    

@app.route('/exercise_filter', methods=['GET', 'POST'])
def exercise_filter_page(): 
     # Default selection or user-submitted one
    selected_exercise = request.form.get('exercise')

    # specific_exercise_filter function comes from the visualization.py
    df_html_table = specific_exercise_filter(selected_exercise)

    exercise_options = generate_excise_options()


    return render_template('exercise_filter.html',
                           df_html_table=df_html_table,
                           exercise_options=exercise_options,
                           selected_exercise=selected_exercise)


@app.route('/overview_visualizations', methods=['GET', 'POST'])
def overview_visualization_page():
    frequency_plot_url = Freq_BarChart()
    distance_plot_url = Distance_BarChart()
    mins_plot_url = Minutes_BarChart()
    total_mins_plot_url = Minutes_LineGraph()  
    treemap_plotly_html = activity_treemap()
    steps_boxplot_url = Steps_Boxplot()

    # Bringing in steps df primarily used in visualization section here for KPI analysis
    steps_day = gen_steps_month_df()

    workout_count_year, workout_count_LM, wokrout_count_CM, current_month_name, last_month_name, workout_time_hrs_avg, steps_L3_mon = get_kpi_stats(steps_day)

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
                          frequency_plot_url=frequency_plot_url,
                          distance_plot_url=distance_plot_url,
                          mins_plot_url=mins_plot_url,
                          total_mins_plot_url=total_mins_plot_url,
                          treemap_plotly_html = treemap_plotly_html,
                          steps_boxplot_url = steps_boxplot_url)



# Add this to your main.py file
def init_10rm_db():
    """Initialize 10RM tracking tables"""
    with engine.begin() as conn:
        # 10RM workout plans table
        conn.execute(text("""CREATE TABLE IF NOT EXISTS tenrm_plans (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            workout_type TEXT NOT NULL,
                            week_number TEXT NOT NULL,
                            exercise_name TEXT NOT NULL,
                            target_weight REAL NOT NULL,
                            sets INTEGER NOT NULL,
                            reps TEXT NOT NULL,
                            created_date DATE NOT NULL,
                            UNIQUE(workout_type, week_number, exercise_name));"""))
        
        # 10RM workout completions table
        conn.execute(text("""CREATE TABLE IF NOT EXISTS tenrm_completions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            plan_id INTEGER NOT NULL,
                            completion_date DATE NOT NULL,
                            completed BOOLEAN NOT NULL,
                            notes TEXT,
                            timestamp DATETIME NOT NULL,
                            FOREIGN KEY (plan_id) REFERENCES tenrm_plans(id));"""))


@app.route('/10rm_tracker', methods=['GET'])
def tenrm_tracker():
    """Display 10RM workout tracking page with filters"""
    with engine.begin() as conn:
        # Get all workout plans with their latest completion status
        query = text("""
            SELECT 
                tp.id,
                tp.workout_type,
                tp.week_number,
                tp.exercise_name,
                tp.target_weight,
                tp.sets,
                tp.reps,
                tc.completion_date,
                tc.completed,
                tc.notes
            FROM tenrm_plans tp
            LEFT JOIN tenrm_completions tc ON tp.id = tc.plan_id
            AND tc.id = (
                SELECT MAX(id) 
                FROM tenrm_completions 
                WHERE plan_id = tp.id
            )
            ORDER BY tp.workout_type, tp.week_number, tp.exercise_name
        """)
        
        results = conn.execute(query).fetchall()
        
        # Organize data by workout type and week
        organized_data = {}
        for row in results:
            workout_type = row[1]
            week_number = row[2]
            
            if workout_type not in organized_data:
                organized_data[workout_type] = {}
            
            if week_number not in organized_data[workout_type]:
                organized_data[workout_type][week_number] = []
            
            organized_data[workout_type][week_number].append({
                'plan_id': row[0],
                'exercise_name': row[3],
                'target_weight': row[4],
                'sets': row[5],
                'reps': row[6],
                'completion_date': row[7],
                'completed': row[8],
                'notes': row[9]
            })
    
    return render_template('10rm_tracker.html', workout_data=organized_data)


@app.route('/add_10rm_plan', methods=['POST'])
def add_10rm_plan():
    """Add a new 10RM workout plan for a specific week"""
    try:
        data = request.json
        workout_type = data.get('workout_type')
        week_number = data.get('week_number')
        exercises = data.get('exercises')  # List of {exercise_name, target_weight}
        
        eastern = pytz.timezone('America/New_York')
        current_date = datetime.now(eastern).strftime('%Y-%m-%d')
        
        with engine.begin() as conn:
            for exercise in exercises:
                # Insert or update the plan
                conn.execute(text("""
                    INSERT INTO tenrm_plans (workout_type, week_number, exercise_name, target_weight, created_date)
                    VALUES (:workout_type, :week_number, :exercise_name, :target_weight, :created_date)
                    ON CONFLICT(workout_type, week_number, exercise_name) 
                    DO UPDATE SET target_weight = :target_weight
                """), {
                    'workout_type': workout_type,
                    'week_number': week_number,
                    'exercise_name': exercise['exercise_name'],
                    'target_weight': exercise['target_weight'],
                    'created_date': current_date
                })
        
        return jsonify({'status': 'success', 'message': '10RM plan added successfully'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/log_10rm_completion', methods=['POST'])
def log_10rm_completion():
    """Log completion of a 10RM workout"""
    try:
        data = request.json
        plan_id = data.get('plan_id')
        completion_date = data.get('completion_date')
        completed = data.get('completed')
        notes = data.get('notes', '')
        
        eastern = pytz.timezone('America/New_York')
        timestamp = datetime.now(eastern).strftime('%Y-%m-%d %H:%M:%S')
        
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO tenrm_completions (plan_id, completion_date, completed, notes, timestamp)
                VALUES (:plan_id, :completion_date, :completed, :notes, :timestamp)
            """), {
                'plan_id': plan_id,
                'completion_date': completion_date,
                'completed': completed,
                'notes': notes,
                'timestamp': timestamp
            })
        
        return jsonify({'status': 'success', 'message': 'Completion logged successfully'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# Update your init_db() function to include 10RM tables
# Add this line inside init_db():
# init_10rm_db()




# Clean shutdown of DB connections
@app.teardown_appcontext
def shutdown_session(exception=None):
    engine.dispose()

if __name__ == '__main__':
    init_db()  # Initialize sql database when the app starts for the first time
    init_10rm_db()
    app.run(debug=True, host="0.0.0.0", port=8501)