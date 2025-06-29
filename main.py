# Standard Library
import os
import io
import json
import base64
from datetime import datetime, timedelta 

# Flask
from flask import Flask, render_template, request, jsonify, send_file

# Data Handling
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, Text, Date, DateTime, func, insert
from Data_Cleaning import load_book_options, load_workout_options, generate_excise_options, \
specific_exercise_filter, get_kpi_stats # only a df with options for a dropdown

# Visualizations
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objs as go
import plotly.io as pio
from visualization import Freq_BarChart, Distance_BarChart, Minutes_BarChart, Minutes_LineGraph, activity_treemap


app = Flask(__name__)

# Initializing the SQLite database link for the entire app
DATABASE = 'habits.db'


# List of habits I want to document and their associated questions

######## Consideratding adding a new movie/show and new food meal habit to start doing more of that ########

HABITS = {
    "workout": {
        "questions": [
            # Add date selector as the first question for all habits
            {"id": "habit_date", "text": "Date:", "type": "date", "required": True},
            {"id": "workout_type", "text": "Exercise:", "type": "select", "required": True, "options": load_workout_options()},
            {"id": "new_workout", "text": "What new workout would you like to log?", "type": "text", "conditional": {"field": "workout_type", "value": "Other"}},
            
            {"id": "weight", "text": "Weight:", "type": "number", "required": True},
            {"id": "sets", "text": "Sets:", "type": "number", "required": True},
            {"id": "reps", "text": "Reps:", "type": "number", "required": True},
            {"id": "effort", "text": "Effort Level", "type": "range", "min": 1, "max": 10, "required": True},
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
            {"id": "stretch", "text": "Did you stretch today?", "type": "checkbox", "required": True},
            {"id": "comment", "text": "Notes:", "type": "text"}
        ]
    }
}


def init_db():
    engine = create_engine(f"sqlite:///{DATABASE}")
    metadata = MetaData()

    habit_logs = Table(
        "habit_logs", metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("habit_type", String),
        Column("data", Text),
        Column("log_date", Date),
        Column("timestamp", DateTime, server_default=func.current_timestamp()))

    # Create the table if it doesn't exist
    metadata.create_all(engine)
    engine.dispose()

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
    """Receive form data, clean some inputs, and then store it in my SQL lite db"""
    try:
        data = request.form.to_dict()
        habit_type = data.pop('habit_type', 'unknown')
        
        # Extract the habit date (or use today if not provided)
        habit_date = data.pop('habit_date', datetime.now().strftime('%Y-%m-%d'))

        ### What I also imagine I can do here is parse the rest of the form data, clean it, and then direct it out to the appropriate table in the database. ###
        
        # New book titles special handling into the database
        if habit_type == "reading":
            if data["book_title"] == "Other" and "custom_title" in data:
                # Replace "Other" with the custom title
                data["book_title"] = data["custom_title"]
                # Remove the custom_title field
                data.pop("custom_title", None)

            # Cleans up data by removing the custom book title from json 
            if data["book_title"] != "Other":
                # Remove the custom_title field
                data.pop("custom_title", None)
        
        # New workouts special handling into the database
        if habit_type == "workout":
            if data["workout_type"] == "Other" and "new_workout" in data:
                # Replace the new_wokrout variable with the standard workout_type 
                data["workout_type"] = data["new_workout"]
                # Remove the new_workout field
                data.pop("new_workout", None)

            # Cleans up data by removing the new_workout variable from json  
            if data["workout_type"] != "Other":
                data.pop("new_workout", None)

            # Adds 10Rm suffix to workout name if the 10RM checkbox is checked
            if data["10RM"] == "on":
                data["workout_type"] = data['workout_type'] + " 10RM"

        # Convert form data to a JSON string for better storage
        data_str = json.dumps(data)

        # Generate a timestamp for when the server received the request
        server_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Insert data into SQLite with both the log date and server timestamp
        engine = create_engine(f"sqlite:///{DATABASE}")

        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO habit_logs (habit_type, data, log_date, timestamp) VALUES (:habit_type, :data, :log_date, :timestamp)"),
                {"habit_type": habit_type,
                    "data": data_str,
                    "log_date": habit_date,
                    "timestamp": server_timestamp})
        
        engine.dispose()

        return jsonify({
            "status": "success", 
            "message": "Data saved to database", 
            "data": data,
            "log_date": habit_date,
            "timestamp": server_timestamp
        })
    
    except Exception as e:
        # Log the full error for server-side debugging
        print(f"Error in submit_habit: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500
    

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


    workout_count_year, workout_count_LM, wokrout_count_CM, current_month_name, last_month_name, workout_time_hrs_avg = get_kpi_stats()

    return render_template('overview_visualizations.html',
                          #KPIs 
                          ytd_count = workout_count_year,
                          mtd_count_LM = workout_count_LM,
                          mtd_count = wokrout_count_CM,
                          workout_time_avg=workout_time_hrs_avg,

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
                          treemap_plotly_html = treemap_plotly_html)


if __name__ == '__main__':
    init_db()  # Initialize database when the app starts
    app.run(debug=True, host="0.0.0.0", port=8501)