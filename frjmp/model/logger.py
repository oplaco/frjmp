import time
import threading
import csv
from ortools.sat.python import cp_model


class IncrementalSolverLogger(cp_model.CpSolverSolutionCallback):
    def __init__(
        self,
        objective_var,
        csv_file="logs/logs.csv",
        inactivity_timeout=120,
        log=False,
    ):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._objective_var = objective_var
        self._csv_file = csv_file
        self._last_activity_time = time.time()  # Time of the last solution or activity
        self._inactivity_timeout = inactivity_timeout  # Timeout in seconds
        self._step = 1
        self._stop_flag = threading.Event()  # Flag to stop the solver gracefully
        self._lock = threading.Lock()
        self._start_time = time.time()  # Start time of the solving process
        self._log = log
        self.step_time_limit_reached = False
        self.at_least_one_solution_found = False

        # Write the header to the CSV file at initialization
        if self._log:
            with open(self._csv_file, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(
                    ["Iteration", "Timestamp (ms)", "Objective Value", "Bound Value"]
                )

    def on_solution_callback(self):
        # Update the last activity time when a solution is found
        with self._lock:
            self.at_least_one_solution_found = True
            self._last_activity_time = time.time()
            obj_value = self.Value(self._objective_var)
            elapsed_time = (time.time() - self._start_time) * 1000  # Milliseconds
            bound_value = self.BestObjectiveBound()
            message = f"Step {self._step}. Objective function = {obj_value}. Lower bound = {bound_value}"
            print(message)

            # Append the current solution to the CSV file
            if self._log:
                with open(self._csv_file, "a", newline="") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow([self._step, elapsed_time, obj_value, bound_value])

            self._step += 1

    def monitor_inactivity(self):
        while not self._stop_flag.is_set():
            with self._lock:
                elapsed_time = time.time() - self._last_activity_time
                if elapsed_time > self._inactivity_timeout and self._step > 1:
                    message = f"Stopping search, step time limit reached. No better solution was found for {elapsed_time:.2f} seconds."
                    print(message)
                    self.step_time_limit_reached = True
                    self.StopSearch()  # Gracefully stop the solver
                    self._stop_flag.set()
            time.sleep(1)  # Check every second

    def start_monitoring(self):
        # Start a thread to monitor inactivity
        monitoring_thread = threading.Thread(
            target=self.monitor_inactivity, daemon=True
        )
        monitoring_thread.start()
