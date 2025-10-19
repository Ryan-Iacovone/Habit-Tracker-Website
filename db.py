# db.py
from sqlalchemy import create_engine, event

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
    cursor.execute("PRAGMA journal_mode=WAL;")   # enable Write-Ahead Logging
    cursor.execute("PRAGMA synchronous=NORMAL;") # balance durability vs performance
    cursor.close()
