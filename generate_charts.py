# generate_charts.py
import os
from visualization import Monthly_Freq_BarChart, Distance_BarChart, \
    Minutes_BarChart, weekly_workout_time_linegraph, Steps_Boxplot

# Ensure the output directory exists
output_dir = "static/charts"
os.makedirs(output_dir, exist_ok=True)

# Static map of all chart functions we'd like to generate
charts = {
    "monthly_frequency": Monthly_Freq_BarChart,
    "distance":          Distance_BarChart,
    "minutes":           Minutes_BarChart,
    "weekly":            weekly_workout_time_linegraph,
    "steps":             Steps_Boxplot,
}

# Looping through each chart generation function and saving the resulting image to disk (output directory)
for name, fn in charts.items():
    print(f"Generating {name}...")

    buf = fn()

    with open(f"{output_dir}/{name}.png", "wb") as f:
        f.write(buf.read())
        
    print(f"  ✓ saved to {output_dir}/{name}.png")

print("All charts generated.")