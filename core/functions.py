from sqlalchemy import create_engine, event, text
from pathlib import Path
from plotnine import *

# Create a single shared engine dynamically
db_path = Path(__file__).resolve().parent.parent / "habits.db"

engine = create_engine(
    f"sqlite:///{db_path}",
    pool_pre_ping=True,
    connect_args={"check_same_thread": False}
)



# Enable WAL mode on every new connection
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")   # Enable Write-Ahead Logging
    cursor.execute("PRAGMA synchronous=FULL") # balance durability vs performance 
    cursor.execute("PRAGMA optimize") 
    cursor.close()



# Statically defining custom workout theme for all plotnine graphs
workout_theme = theme(
    figure_size=(10, 5),
    legend_position=(.5, .96),
    #legend_title=element_text(color="#1E3A52", size=11, weight='bold'),
    legend_direction='horizontal',
    legend_text=element_text(color="#3A5A78", size=11),
    legend_background=element_blank(),
    legend_key=element_blank(),

    plot_background  = element_rect(fill="#FFFFFF", color=None),
    panel_background = element_rect(fill="#F4F7FA", color=None),
    panel_grid_major = element_line(color="#CDDDED", size=0.5),
    panel_grid_minor_y = element_line(color="#CDDDED", linetype="solid"),

    axis_text        = element_text(color="#6B8299", size=10), # X & Y axis labels
    axis_title       = element_text(color="#3A5A78", size=13), # y axis title/label
    #plot_title       = element_text(color="#1E3A52", size=13, weight="bold"),
)





# initalizing habits websites with sql tables needed to support it
# I've already gone through this and changed types to be sqlite compliant
# A foreign key is a "pointer" from one table to another. You put the pointer in the table that needs to look up information elsewhere.
def init_db():
    with engine.begin() as conn:

        # habits table
        conn.execute(text("""CREATE TABLE IF NOT EXISTS habits (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT UNIQUE NOT NULL);"""))

        # habit_entries table
        conn.execute(text("""CREATE TABLE IF NOT EXISTS habit_entries (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            habit_id INTEGER NOT NULL,
                            log_date TEXT NOT NULL,
                            timestamp TEXT NOT NULL,
                            FOREIGN KEY (habit_id) REFERENCES habits(id));"""))

        # habit_answers table
        conn.execute(text("""CREATE TABLE IF NOT EXISTS habit_answers (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            entry_id INTEGER NOT NULL,
                            question TEXT NOT NULL,
                            answer TEXT NOT NULL,
                            FOREIGN KEY (entry_id) REFERENCES habit_entries(id));"""))
        
        # access log table (for IP address logging)
        conn.execute(text("""CREATE TABLE IF NOT EXISTS access_log (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            ip TEXT NOT NULL,
                            endpoint TEXT NOT NULL,
                            timestamp TEXT NOT NULL);"""))
        
        # 10RM workout plans table
        conn.execute(text("""CREATE TABLE IF NOT EXISTS tenrm_plans (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            workout_type TEXT NOT NULL,
                            week_number INTEGER NOT NULL,
                            exercise_name TEXT NOT NULL,
                            target_weight INTEGER NOT NULL,
                            sets INTEGER NOT NULL,
                            reps INTEGER NOT NULL,
                            created_date TEXT NOT NULL,
                            UNIQUE(workout_type, week_number, exercise_name, created_date));"""))
        
        # 10RM workout completions table
        conn.execute(text("""CREATE TABLE IF NOT EXISTS tenrm_completions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            plan_id INTEGER NOT NULL,
                            completion_date TEXT NOT NULL,
                            completed INTEGER NOT NULL,
                            notes TEXT,
                            timestamp TEXT NOT NULL,
                            FOREIGN KEY (plan_id) REFERENCES tenrm_plans(id));"""))

        # apple_data_raw table
        conn.execute(text("""CREATE TABLE IF NOT EXISTS apple_data_raw (
                            type TEXT, 
                            "sourceName" TEXT, 
                            value TEXT, 
                            unit TEXT, 
                            "startDate" TEXT, 
                            "endDate" TEXT, 
                            "creationDate" TEXT, 
                            "sourceVersion" TEXT, 
                            "appleStandHours" REAL, 
                            "appleExerciseTimeGoal" REAL, 
                            bpm REAL, 
                            maximum REAL, 
                            "sum" REAL, 
                            "appleMoveTimeGoal" REAL, 
                            "average" REAL, 
                            time TEXT, 
                            "key" TEXT, 
                            duration REAL, 
                            "dateComponents" TEXT, 
                            "CardioFitnessMedicationsUse" TEXT, 
                            "activeEnergyBurned" REAL, 
                            "appleMoveTime" REAL, 
                            date TEXT, 
                            "activeEnergyBurnedUnit" TEXT, 
                            locale TEXT, 
                            "appleStandHoursGoal" REAL, 
                            "BiologicalSex" TEXT, 
                            "FitzpatrickSkinType" TEXT, 
                            "BloodType" TEXT, 
                            "workoutActivityType" TEXT, 
                            "minimum" REAL, 
                            path TEXT, 
                            "appleExerciseTime" REAL, 
                            "durationUnit" TEXT, 
                            "DateOfBirth" TEXT, 
                            device TEXT, 
                            "activeEnergyBurnedGoal" REAL)"""))


        # Cleaned Apple Workouts table
        conn.execute(text("""CREATE TABLE IF NOT EXISTS apple_workouts (
                            "StartDate" TEXT, 
                            activity TEXT, 
                            metric TEXT, 
                            measurement_type TEXT, 
                            value REAL, 
                            d_unit TEXT, 
                            activity_type TEXT, 
                            workout_id REAL)"""))
        
        # bike workouts table        
        conn.execute(text("""CREATE TABLE IF NOT EXISTS bike_workout (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            start_time TEXT,
                            end_time TEXT,
                            upload_date TEXT)"""))
        
        # Bike Units table (reference table - no foreign keys needed)
        conn.execute(text("""CREATE TABLE IF NOT EXISTS bike_units (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            metric_type TEXT UNIQUE NOT NULL,
                            metric_unit TEXT NOT NULL,
                            unit_name TEXT NOT NULL)"""))
        
        # Bike Workout Metrics table
        conn.execute(text("""CREATE TABLE IF NOT EXISTS bike_metrics (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT NOT NULL,
                            workout_id INTEGER NOT NULL,
                            metric_id INTEGER NOT NULL,
                            value REAL,
                            FOREIGN KEY (workout_id) REFERENCES bike_workout(id),
                            FOREIGN KEY (metric_id) REFERENCES bike_units(id))"""))
        
        # Create food day table from cronometer
        conn.execute(text("""CREATE TABLE IF NOT EXISTS food_daily (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            completed TEXT,
                            food_date TEXT,
                            upload_date TEXT)"""))
        
        # Create fact food table 
        conn.execute(text("""CREATE TABLE IF NOT EXISTS fact_food (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            meal_time TEXT,
                            food_category TEXT, 
                            value INTEGER,
                            food_daily_id INTEGER,
                            FOREIGN KEY (food_daily_id) REFERENCES food_daily(id) )"""))