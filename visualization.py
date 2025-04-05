# Add this to your Flask application
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
from flask import send_file

# Create a directory for static files if it doesn't exist
def ensure_static_dir():
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    return static_dir

def generate_sample_plot():
    """Generate a sample visualization using matplotlib/seaborn"""
    # Clear any existing plots
    plt.figure(figsize=(10, 6))
    
    # Create sample data
    categories = ['Jan', 'Feb', 'Mar', 'Apr', 'May']
    values = [4, 7, 5, 9, 6]
    
    # Create a simple bar chart
    sns.set_style("whitegrid")
    ax = sns.barplot(x=categories, y=values, palette="viridis")
    
    # Add title and labels
    plt.title('Monthly Activity Overview', fontsize=16)
    plt.xlabel('Month', fontsize=12)
    plt.ylabel('Activity Level', fontsize=12)
    
    # Add value labels on top of each bar
    for i, v in enumerate(values):
        ax.text(i, v + 0.2, str(v), ha='center', fontsize=12)
    
    # Save to a file in static directory
    static_dir = ensure_static_dir()
    file_path = os.path.join(static_dir, 'monthly_activity.png')
    plt.savefig(file_path, bbox_inches='tight', dpi=100)
    plt.close()
    
    return file_path

def generate_interactive_plot():
    """Generate a more complex visualization with seaborn"""
    # Create a figure with subplots
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # Sample data
    x = np.linspace(0, 10, 100)
    y1 = np.sin(x)
    y2 = np.cos(x)
    
    # Left subplot - line chart
    axes[0].plot(x, y1, label='Workout Intensity', color='blue', linewidth=2)
    axes[0].plot(x, y2, label='Recovery Rate', color='green', linewidth=2)
    axes[0].set_title('Workout Metrics Over Time')
    axes[0].set_xlabel('Time (days)')
    axes[0].set_ylabel('Value')
    axes[0].legend()
    axes[0].grid(True)
    
    # Right subplot - heatmap
    workout_data = np.random.rand(7, 5)
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    workout_types = ['Cardio', 'Strength', 'Stretch', 'HIIT', 'Rest']
    
    sns.heatmap(workout_data, annot=True, fmt=".2f", cmap="YlGnBu", 
                xticklabels=workout_types, yticklabels=days, ax=axes[1])
    axes[1].set_title('Weekly Workout Distribution')
    
    # Adjust layout
    plt.tight_layout()
    
    # Save to a file
    static_dir = ensure_static_dir()
    file_path = os.path.join(static_dir, 'workout_analytics.png')
    plt.savefig(file_path, bbox_inches='tight', dpi=100)
    plt.close()
    
    return file_path