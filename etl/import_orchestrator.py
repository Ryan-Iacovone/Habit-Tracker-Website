import papermill as pm
import datetime as dt
import os
import sys

# Ensuring that the outputs folder is created
os.makedirs("outputs", exist_ok=True)

today = dt.datetime.now().strftime("%m-%d-%Y")

# Executing the apple ETL notebook
def run_apple_elt():
    pm.execute_notebook(
        r"notebooks\apple_etl.ipynb",
        rf"outputs\apple_etl_output_{today}.ipynb",
    )

# Executing the Cronometer/food ETL notebook
def run_cronometer_etl():
    pm.execute_notebook(
        r"notebooks\cronometer_etl.ipynb",
        rf"outputs\cronometer_etl_output_{today}.ipynb",
    )

# Executing the MyWhoosh/Bike ETL notebook
def run_mywhoosh_etl():
    pm.execute_notebook(
        r"notebooks\mywhoosh_etl.ipynb",
        rf"outputs\mywhoosh_etl_output_{today}.ipynb",
    )

while True:
    choice = input(f"What import notebooks would you like to run? (apple, cronometer, bike, or all): ").lower().strip()
    if choice == "apple":
        print("\nRunning Apple ETL Notebook")
        run_apple_elt()
        break

    elif choice == "cronometer":
        print("\nRunning Cronometer ETL Notebook")
        run_cronometer_etl()
        break

    elif choice == "bike":
        print("\nRunning MyWhoosh/Bike ETL Notebook")
        run_mywhoosh_etl()
        break

    elif choice == "all":
        print("\nRunning both the Cronometer and Apple ETL Notebook")

        # Apple ETL
        print("\nStarting Apple ETL Notebook")
        run_apple_elt()
        print("Apple ETL Notebook successfully ran")

        # Cronometer ETL
        print("\nStarting Cronometer ETL Notebook")
        run_cronometer_etl()
        print("Cronometer ETL Notebook successfully ran")

########### MyWhoosh ETL commented out until it becomes that season ###########
        # MyWhoosh ETL
        #print("\nStarting MyWhoosh ETL Notebook")
        #run_mywhoosh_etl()
        #print("MyWhoosh ETL Notebook successfully ran")

        break
    elif choice == "quit":
            print("Exiting ETL Orchestrator")
            sys.exit()
    else:
        print("Invalid input. Please enter 'apple', 'cronometer', or 'all' to continue or 'n' to exit.")

print(f"\n{choice.capitalize()} notebooks successfully run and completed!")
