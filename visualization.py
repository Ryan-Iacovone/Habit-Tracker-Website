import matplotlib.pyplot as plt
import matplotlib
import plotly.express as px
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
from plotnine import *
from Data_Cleaning import Read_Apple_Workouts, gen_freq_df, gen_distance_df, gen_mins_df, gen_workout_time_df, gen_activity_treemap_df

matplotlib.use('Agg')  # use non-GUI backend for Flask app

# Database configuration details - IDK if this is even needed?
def create_sql_engine():
    # Create a SQLAlchemy engine to connect to the SQLite database
    Database = "habits.db" 
    engine = create_engine(f"sqlite:///{Database}")
    return engine

# Apple workout data from data_cleaning file
aw_final = Read_Apple_Workouts()

############### Frequency bar chart grouped by exercise type ###############
full_count_data = gen_freq_df(aw_final)

def Freq_BarChart():
    plot = (ggplot(full_count_data, aes(x='month', y='n', fill='activity')) +
        geom_bar(stat='identity', position='dodge') +
        geom_text(aes(label='n'), position=position_dodge(width=0.9), va='bottom') + # va & ha are used for veritcal and horizontal allignment 
        #geom_hline(aes(yintercept='goal', color='activity'), linetype='dashed') +
        scale_fill_brewer(type='qual', palette='Set1') +
        #scale_color_manual(values={'Running': 'black', 'Cycling': 'gray'}) +
        scale_y_continuous(breaks = range(0, 16),
                        limits = [0, 15]) +
        scale_x_discrete(labels=lambda l: [pd.Period(p).strftime('%b %Y') for p in l]) +  #  idk how it works but it does

        labs(title='Workout Frequency by Month and Activity',
            x='Month',
            y='Number of Sessions',
            fill='Activity',
            color='Goal') +
        #theme_matplotlib() +
        theme_seaborn() +
        theme(figure_size=(10, 5)))

    # Render plot to a matplotlib figure
    fig = plot.draw()

    # Save figure to buffer
    static_bytes = io.BytesIO()
    fig.savefig(static_bytes, format='png', bbox_inches='tight')
    static_bytes.seek(0)
    static_base64 = base64.b64encode(static_bytes.read()).decode('utf-8')
    frequency_plot_url = f"data:image/png;base64,{static_base64}"
    plt.close(fig)

    return frequency_plot_url


############### Distance per week grouped by exercise type ###############
full_miles_week = gen_distance_df(aw_final)

def Distance_BarChart():
    plot = (
    ggplot(full_miles_week, aes(x='week_label', y='Total_Miles', fill='activity')) +
    geom_bar(stat='identity', position='dodge') +
    geom_text(aes(label='Total_Miles'), position=position_dodge(width=0.9), va='bottom') +
    labs(title= "Miles per Week by Activity",
         x="Week",
         y="Miles") +
    theme_seaborn() +
    theme(
        figure_size=(10, 5),
        axis_text_x=element_text(angle=20, hjust=1)))

    # Render plot to a matplotlib figure
    fig = plot.draw()

    # Save figure to buffer
    static_bytes = io.BytesIO()
    fig.savefig(static_bytes, format='png', bbox_inches='tight')
    static_bytes.seek(0)
    static_base64 = base64.b64encode(static_bytes.read()).decode('utf-8')
    distance_plot_url = f"data:image/png;base64,{static_base64}"
    plt.close(fig)

    return distance_plot_url


############### Minutes per week grouped by cardio and biking ###############
full_mins_week = gen_mins_df(aw_final)

def Minutes_BarChart():
    plot = (ggplot(full_mins_week, aes(x='week_period', y='Total_min', fill='activity_type')) +
        geom_bar(stat='identity', position='dodge') +
        geom_text(aes(label='Total_min'), format_string='{:.1f}', position=position_dodge(width=5), va='bottom') +
        scale_x_datetime(date_labels='%b %d', date_breaks='1 week') +  # Optional, for clean weekly ticks
        geom_hline(aes(yintercept=150, color='activity_type'), linetype='dashed', size=1) + # Cardio goal
        geom_hline(aes(yintercept=80, color='activity_type'), linetype='dashed', size=1) + # Weights goal
        labs(title= "Minutes per Week by Activity",
            x="Week",
            y="Minutes") +
        theme_seaborn() +
        theme(figure_size=(10, 5),
                axis_text_x = element_text(angle = 20, hjust = 1)))
    
    # Render plot to a matplotlib figure
    fig = plot.draw()

    # Save figure to buffer
    static_bytes = io.BytesIO()
    fig.savefig(static_bytes, format='png', bbox_inches='tight')
    static_bytes.seek(0)
    static_base64 = base64.b64encode(static_bytes.read()).decode('utf-8')
    mins_plot_url = f"data:image/png;base64,{static_base64}"
    plt.close(fig)

    return mins_plot_url

############### Minutes per week for all exercises ############### 
workout_time = gen_workout_time_df(aw_final)
 

def Minutes_LineGraph():
    plot = (ggplot(workout_time, aes(x='week_period', y='Time')) +
        geom_line(color = "blue", size = 1) +
        geom_point(aes(size = "n"), alpha = 0.6, color = "blue") +
        geom_text(aes(label='n'), format_string='{:.0f}', va='bottom') +
        labs(title= "Minutes per Week by Activity",
            x="Week",
            y="Minutes") +
        scale_x_datetime(date_labels='%b %d', date_breaks='1 week') +
        
        theme_seaborn() +
        theme(panel_grid_minor_y = element_line(color = "gray", linetype = "dotted"),
            figure_size=(10, 5),
            axis_text_x=element_text(angle=25, hjust=1),
            legend_position='none',
            axis_ticks_minor_x=element_blank()))

    # Render plot to a matplotlib figure
    fig = plot.draw()

    # Save figure to buffer
    static_bytes = io.BytesIO()
    fig.savefig(static_bytes, format='png', bbox_inches='tight')
    static_bytes.seek(0)
    static_base64 = base64.b64encode(static_bytes.read()).decode('utf-8')
    total_mins_plot_url = f"data:image/png;base64,{static_base64}"
    plt.close(fig)

    return total_mins_plot_url



############### Activity Treemap ############### 
activity_distribution = gen_activity_treemap_df(aw_final)

def activity_treemap():
    # Create treemap
    fig = px.treemap(
        activity_distribution,
        path=['label'],         # use custom label for full text
        values='count',
        color='count',
        color_continuous_scale='Blues')
    
    fig.update_layout(showlegend=False, coloraxis_showscale=False)

    treemap_plotly_html = pio.to_html(fig, full_html=False)

    return treemap_plotly_html