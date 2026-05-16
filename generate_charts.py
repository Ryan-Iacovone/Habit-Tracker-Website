# generate_charts.py
import os
from visualization import Monthly_Freq_BarChart, Distance_BarChart, \
    Minutes_BarChart, activity_treemap, weekly_workout_time_linegraph, Steps_Boxplot, \
    activity_treemap, get_kpi_stats

output_dir = "static/charts"
os.makedirs(output_dir, exist_ok=True)

# PNG charts — same as before
charts = {
    "monthly_frequency": Monthly_Freq_BarChart,
    "distance":          Distance_BarChart,
    "minutes":           Minutes_BarChart,
    "weekly":            weekly_workout_time_linegraph,
    "steps":             Steps_Boxplot,
}

for name, fn in charts.items():
    print(f"Generating {name}...")
    buf = fn()
    with open(f"{output_dir}/{name}.png", "wb") as f:
        f.write(buf.read())
    print(f"  ✓ saved to {output_dir}/{name}.png")

# HTML charts — handled separately
print("Generating activity treemap...")
html = activity_treemap()
with open(f"{output_dir}/activity_treemap.html", "w", encoding="utf-8") as f:
    f.write(html)
print(f"  ✓ saved to {output_dir}/activity_treemap.html")

# Create CSV file for KPIs 
print("Generating kpis...")
get_kpi_stats()
print("Saved KPIs CSV to static folder ...")


print("All charts & KPIs generated.")