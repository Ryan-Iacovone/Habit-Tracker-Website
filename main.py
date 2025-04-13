from visualization import generate_matlotlib, generate_seaborn, generate_plotly
import os
from flask import send_file
from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime, timedelta
import json
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
from flask import send_file
import plotly.graph_objs as go
import plotly.io as pio
import io
import base64
import pandas as pd 

app = Flask(__name__)

# List of habits and their associated questions
HABITS = {
    "workout": {
        "questions": [
            # Add date selector as the first question for all habits
            {"id": "habit_date", "text": "Date:", "type": "date", "required": True},
            {"id": "workout_type", "text": "Exercise:", "type": "text", "required": True},
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
            {"id": "book_title", "text": "What book did you read?", "type": "select", 
             "options": [
                 "1984", 
                 "Atomic Habits",
                 "The Hobbit",
                 "The Fifth Season",
                 "Blood Over Bright Haven",
                 "Foundryside",
                 "Other"
             ]},
            {"id": "custom_title", "text": "If Other, specify book title:", "type": "text", "conditional": {"field": "book_title", "value": "Other"}},
            {"id": "pages", "text": "How many pages did you read?", "type": "number"}
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

DATABASE = "habits.db"

def init_db():
    """Initialize the SQLite database and create the habits table."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS habit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_type TEXT,
            data TEXT,
            log_date DATE,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

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
    """Receive form data and store it in SQLite with user-specified date and server timestamp."""
    try:
        data = request.form.to_dict()
        habit_type = data.pop('habit_type', 'unknown')
        
        # Extract the habit date (or use today if not provided)
        habit_date = data.pop('habit_date', datetime.now().strftime('%Y-%m-%d'))

        ### What I also imagine I can do here is parse the rest of the form data, clean it, and then direct it out to the appropriate table in the database. ###
        
        # Special handling for book titles
        if habit_type == "reading" and "book_title" in data:
            if data["book_title"] == "Other" and "custom_title" in data and data["custom_title"].strip():
                # Replace "Other" with the custom title
                data["book_title"] = data["custom_title"]
                # Remove the custom_title field
                data.pop("custom_title", None)

        # Convert form data to a JSON string for better storage
        data_str = json.dumps(data)

        # Generate a timestamp for when the server received the request
        server_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Insert data into SQLite with both the log date and server timestamp
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO habit_logs (habit_type, data, log_date, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (habit_type, data_str, habit_date, server_timestamp))
        conn.commit()
        conn.close()

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
    
@app.route('/visualizations')
def visualization_page():
    matplotlib_plot_url= generate_matlotlib()
    seaborn_plot_url = generate_seaborn()  
    plotly_html = generate_plotly()

    return render_template('visualizations.html',
                           matplotlib_plot_url=matplotlib_plot_url,
                           seaborn_plot_url=seaborn_plot_url,
                           plotly_html=plotly_html)


if __name__ == '__main__':
    init_db()  # Initialize database when the app starts
    app.run(debug=True, host="0.0.0.0", port=8080)