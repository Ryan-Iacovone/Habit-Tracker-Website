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

# Visualization
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objs as go
import plotly.io as pio
from visualization import generate_matlotlib, generate_seaborn, generate_plotly, specific_exercise_filter, get_kpi_stats


app = Flask(__name__)

# Initializing the SQLite database link for the entire app
DATABASE = 'habits.db'


# Update the list of book titles table in my database with any potential new entries
def load_book_options():
    engine = create_engine(f"sqlite:///{DATABASE}")

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


def load_workout_options():
    engine = create_engine(f"sqlite:///{DATABASE}")

    # read_sql_query simple 
    with engine.connect() as connection:
        workouts = pd.read_sql_query(
            text("""SELECT DISTINCT exercise FROM workouts"""), connection)

    engine.dispose()

    workouts_list = sorted(workouts["Exercise"].tolist())

    # Add "Other" option to the list of book titles and works. This way other is not saved to the database
    workouts_list.append("Other")

    return workouts_list


# List of habits I want to document and their associated questions
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
    

@app.route('/dynamic_visualizations', methods=['GET', 'POST'])
def dynamic_visualization_page():
     # Default selection or user-submitted one
    selected_exercise = request.form.get('exercise')

    # specific_exercise_filter function comes from the visualization.py
    df_html_table = specific_exercise_filter(selected_exercise)

    # Get unique exercises for dropdown
    engine = create_engine("sqlite:///habits.db") 
    with engine.connect() as connection:
        workouts = pd.read_sql_query(
            text("SELECT DISTINCT Exercise FROM workouts" 
        "         ORDER BY Exercise"), connection)
        exercise_options = workouts['Exercise'].dropna().tolist()

    return render_template('dynamic_visualizations.html',
                           df_html_table=df_html_table,
                           exercise_options=exercise_options,
                           selected_exercise=selected_exercise)


@app.route('/static_visualizations', methods=['GET', 'POST'])
def static_visualization_page():
    matplotlib_plot_url = generate_matlotlib()
    seaborn_plot_url = generate_seaborn()  
    plotly_html = generate_plotly()

    ytd_count, mtd_count, prev_month_count, days_per_month_html, workouts_by_month_html = get_kpi_stats()

    return render_template('static_visualizations.html',
                          ytd_count=ytd_count,
                          mtd_count=mtd_count,
                          prev_month_count=prev_month_count,
                          days_per_month_html=days_per_month_html,
                          workouts_by_month_html=workouts_by_month_html,
                          matplotlib_plot_url=matplotlib_plot_url,
                          seaborn_plot_url=seaborn_plot_url,
                          plotly_html=plotly_html)


if __name__ == '__main__':
    init_db()  # Initialize database when the app starts
    app.run(debug=True, host="0.0.0.0", port=8501)