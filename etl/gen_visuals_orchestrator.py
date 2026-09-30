import papermill as pm
import datetime as dt
import os

# Ensuring that the outputs folder is created
os.makedirs("outputs", exist_ok=True)

today = dt.datetime.now().strftime("%m-%d-%Y")

# Executing the visual creations notebook
pm.execute_notebook(
    r"notebooks\visual_creations.ipynb",
    rf"outputs\visual_creations_output_{today}.ipynb",
)