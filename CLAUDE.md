# Habit‑Tracker‑Website

## 📌 Project Overview
This is a lightweight Flask web application that allows users to log daily habits such as workouts, reading, dental care, stretching, and acne care.  The data is stored in a SQLite database and is queried via SQLAlchemy.

## 🏗️ Architecture

| Layer | Responsibility | Key Files |
|-------|----------------|-----------|
| Web UI | Renders forms and charts | `templates/*.html` |
| Flask Routes | Handle HTTP requests | `main.py` |
| Data Access | SQLAlchemy engine & table definitions | `db.py` |
| Data Loading & Cleaning | Pull Apple‑Health data, normalize, and insert into SQLite | `data_cleaning.py` |
| Visualisation | Plotly & Plotnine charts | `visualization.py` |

### Database Schema
The app uses a single SQLite file `habits.db` with the following tables:
- **habits** – id, name
- **habit_entries** – id, habit_id, log_date, timestamp
- **habit_answers** – id, entry_id, question, answer
- **access_log** – id, ip, endpoint, timestamp
- **tenrm_plans / tenrm_completions** – support for 10RM workout plans
- **apple_workouts / apple_data_raw** – raw Apple Health data

## 🚀 Common Commands
| Purpose | Command | Notes |
|---------|---------|-------|
| Install dependencies | `pip install -r requirements.txt` | Runs in the project root |
| Initialise database | `python -c "from db import init_db; init_db()"` | Creates tables if missing |
| Run development server | `python main.py` | Starts Flask on `0.0.0.0:8501` |
| View logs | `tail -f habits.db` | Quick debugging |
| Run unit tests | (no dedicated test runner) | Use the ETL functions directly or create a new test harness when needed |

## 📦 Dependencies
- Python 3.12+ (uses `zoneinfo` and `datetime`)
- Flask
- SQLAlchemy
- pandas, numpy, plotly, plotnine
- dateutil

## 👷️ Development Workflow
1. **Edit**: Make code changes locally.
2. **Test**: Run your own tests or validate ETL functions manually.
3. **Commit**: `git add <files>` and `git commit -m "..."`.
4. **Push**: `git push` to sync with remote.
5. **Deploy**: Use your CI/CD pipeline or run `python main.py` on the server.

## 🎯 Future Enhancements
- **Switch to Plotnine** for all chart generation to unify the visualisation API and improve styling.
- **ETL Optimization**: Refactor `data_cleaning.py` to batch‑insert Apple Health data into SQLite, use `executemany` and SQLAlchemy bulk‑save for speed.
- **Unit Tests for ETL**: Add a `tests/` package with `test_etl.py` that validates the end‑to‑end flow from raw data to normalized tables.
- **CI Integration**: Configure GitHub Actions to run the tests on every PR.
- **Database Migration**: Consider Alembic for schema changes when moving to PostgreSQL.

---
*Generated with [Claude Code](https://claude.com/claude-code)*
