import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
import numpy as np
import os
from flask import send_file
import plotly.graph_objs as go
import plotly.io as pio
import io
import base64
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, Text, Date, DateTime, func, insert

matplotlib.use('Agg')  # use non-GUI backend for Flask app

def generate_matlotlib(): 
    plt.figure(figsize=(8, 4))
    x = range(10)
    y = [i**2 for i in x]
    plt.plot(x, y, marker='o')
    plt.title('Static Plot: Squares')
    plt.xlabel('x')
    plt.ylabel('y')

    # Save static plot to bytes
    static_bytes = io.BytesIO()
    plt.savefig(static_bytes, format='png')
    static_bytes.seek(0)
    static_base64 = base64.b64encode(static_bytes.read()).decode('utf-8')
    matplotlib_plot_url = f"data:image/png;base64,{static_base64}"
    plt.close()

    return matplotlib_plot_url

def generate_seaborn():
    sns.set_theme(style="ticks", palette="pastel")

    # Load the example tips dataset
    tips = sns.load_dataset("tips")

    # Draw a nested boxplot to show bills by day and time
    plt.figure(figsize=(8, 4))  # Optional: ensure consistent sizing
    sns.boxplot(x="day", y="total_bill",
                hue="smoker", palette=["m", "g"],
                data=tips)
    sns.despine(offset=10, trim=True)

    # Save static plot to bytes
    static_bytes = io.BytesIO()
    plt.savefig(static_bytes, format='png')
    static_bytes.seek(0)
    static_base64 = base64.b64encode(static_bytes.read()).decode('utf-8')
    seaborn_plot_url = f"data:image/png;base64,{static_base64}"
    plt.close()

    return seaborn_plot_url

def generate_plotly():
    dates = pd.date_range(end=datetime.today(), periods=30)
    habit_counts = np.random.randint(0, 5, size=30)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=habit_counts,
        mode='lines+markers',
        name='Habit Check-ins',
        line=dict(color='royalblue', width=2),
        marker=dict(size=6)
    ))
    fig.update_layout(
        title='Interactive Plot: Habit Check-ins Over 30 Days',
        xaxis_title='Date',
        yaxis_title='Check-ins',
        template='plotly_white',
        autosize=True,
        height=500
    ) 
    plotly_html = pio.to_html(fig, full_html=False)

    return plotly_html

# Generates a table for the dynamic exercise filter page 
def specific_exercise_filter(specific_exercise):
    engine = create_engine("sqlite:///habits.db")
    with engine.connect() as connection:
        # Use SQLAlchemy's text() to safely parameterize the query
        workouts = pd.read_sql_query(
            text("SELECT * FROM workouts WHERE exercise = :activity"),
            connection,
            params={"activity": specific_exercise}  # Correct parameter name to match function argument
        )
    engine.dispose()
    return workouts.to_html(classes='workout-table', index=False, border=1)


def get_kpi_stats():

    # Initializing the SQLite database link
    DATABASE = 'habits.db'
    engine = create_engine(f"sqlite:///{DATABASE}")

    # Read workouts data from database
    with engine.connect() as connection:
        workout_df = pd.read_sql_query(text("SELECT * FROM workouts"), connection)

    # Ensure timestamp is in datetime format
    workout_df['Timestamp'] = pd.to_datetime(workout_df['Timestamp'])

    workout_df['month'] = workout_df['Timestamp'].dt.month_name()
    workout_df['year'] = workout_df['Timestamp'].dt.year
    workout_df['date'] = workout_df['Timestamp'].dt.date

    # Get current date and year/month details
    current_date = pd.Timestamp.now()
    current_year = current_date.year
    current_month = current_date.month

    # Calculate Year-to-Date count
    ytd_count = len(workout_df[workout_df['year'] == current_year])

    # Calculate Month-to-Date count
    mtd_count = len(workout_df[(workout_df['year'] == current_year) & 
                        (workout_df['month'] == current_date.month_name())])

    # You can also calculate previous month's total for comparison
    prev_month = current_month - 1 if current_month > 1 else 12
    year = current_year if current_month > 1 else current_year - 1

    prev_month_count = len(workout_df[(workout_df['Timestamp'].dt.year == year) & 
                                    (workout_df['Timestamp'].dt.month == prev_month)])

    # MTD Workouts w/ tagerts

    # Excersies per workout avg

    # days exercised by month
    workouts_by_month_df = workout_df.groupby(['month', 'year']).agg({'Timestamp': 'count'})

    # Days exercised by month
    days_per_month_df = workout_df.groupby(['date', 'month']).agg({'Timestamp': 'count'}).groupby(['month']).agg({'Timestamp': 'count'})

    # Format your DataFrame tables as HTML with styling
    days_per_month_html = days_per_month_df.to_html(classes='workout-table', index=True, border=0)
    workouts_by_month_html = workouts_by_month_df.to_html(classes='workout-table', index=True, border=0)

    return ytd_count, mtd_count, prev_month_count, days_per_month_html, workouts_by_month_html