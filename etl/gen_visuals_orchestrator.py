import papermill as pm
import datetime as dt
from pathlib import Path

# __file__ is the path Python uses for the current script whereas 'Path().' starts from the CWD 
script_dir = Path(__file__).resolve().parent
notebook_path = script_dir / "notebooks" / "visual_creations.ipynb"
output_dir = script_dir / "outputs" # In pathlib, / is overloaded by Path objects to join path components:
output_dir.mkdir(parents=True, exist_ok=True) # Ensuring the outputs directory exists

today = dt.datetime.now().strftime("%m-%d-%Y")

# Executing the visual creations notebook
pm.execute_notebook(
    notebook_path,
    output_dir / f"visual_creations_output_{today}.ipynb",
)