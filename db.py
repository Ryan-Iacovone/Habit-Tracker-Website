# db.py
from sqlalchemy import create_engine, event, text

# For SQLite file-based DB
DATABASE_URL = "sqlite:///habits.db"

# Create a single shared engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # ensures dead connections are detected/recycled
    connect_args={"check_same_thread": False}  # needed for SQLite in multi-threaded apps
)

# Enable WAL mode on every new connection
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")   # Enable Write-Ahead Logging
    cursor.execute("PRAGMA synchronous=FULL") # balance durability vs performance 
    cursor.execute("PRAGMA optimize") 
    cursor.close()


# initalizing habits websites with sql tables needed to support it
# I've already gone through this and changed types to be sqlite compliant
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
                            UNIQUE(workout_type, week_number, exercise_name));"""))
        
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