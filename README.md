# Habit‑Tracker‑Website

## 📌 Project Overview
This lightweight Flask web application lets users log daily habits such as workouts, reading, dental care, stretching, and acne care.  Habit data is stored in a SQLite database and visualized with Plotly/Plotnine.

[Code overview](image%20of%20code.png)

## 🏗️ Architecture
| Layer | Responsibility | Key Files |
|-------|----------------|-----------|
| Web UI | Renders forms and charts | `templates/*.html` |
| Flask Routes | Handle HTTP requests | `main.py` |
| Data Access | SQLAlchemy engine & table definitions | `db.py` |
| Data Loading & Cleaning | Pull Apple‑Health data, normalize, and insert into SQLite | `data_cleaning.py`, `import_new_apple.py` |
| Visualisation | Plotly & Plotnine charts | `visualization.py` |

## ⚙️ Installation
```bash
# Clone the repo and install dependencies
git clone https://github.com/<your-username>/habit-tracker-website.git
cd habit-tracker-website
uv sync
```

## 🚀 Quick Start
```bash
# Initialise the database (first‑time only)
uv sync
python -c "from db import init_db; init_db()"

# Run the development server
uv run python main.py
```
The app will be available at `http://0.0.0.0:8501`.

## ✨ Feature Highlights
- **Habit Logging** – Add, edit, and view habit entries through a user‑friendly web UI.
- **Apple‑Health Import** – Bulk load Apple Health workouts into SQLite using `import_new_apple.py` and `data_cleaning.py`.
- **Visualisations** – Interactive charts powered by Plotly and Plotnine.
- **10RM Workout Planning** – Tables `tenrm_plans` and `tenrm_completions` support automated workout recommendations.

## 🗂️ Database Architecture
The application uses a SQLite database (`habits.db`).  Schema definitions live in `db.py` and include tables such as `habits`, `habit_entries`, `habit_answers`, `access_log`, `tenrm_plans`, `tenrm_completions`, `apple_workouts`, and `apple_data_raw`.

## 📄 License
MIT
