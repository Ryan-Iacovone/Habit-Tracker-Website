# Add this to your Flask application
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