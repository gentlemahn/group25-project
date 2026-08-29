import csv
import json
import os

from config import PLOTS_FILE, LOGS_FILE


class StorageError(Exception):
    pass


class PlotStorage:
    """Handles saving/loading farm plots (JSON) and log entries (CSV)."""

    def __init__(self, plots_file=PLOTS_FILE, logs_file=LOGS_FILE):
        self.plots_file = plots_file
        self.logs_file = logs_file

        # make sure the folders exist so we don't blow up on first save
        os.makedirs(os.path.dirname(self.plots_file), exist_ok=True)
        os.makedirs(os.path.dirname(self.logs_file), exist_ok=True)

    # ---------- plots (json) ----------

    def save_plot(self, plot):
        plots = self.load_plots()
        plots.append(plot.to_dict())

        try:
            with open(self.plots_file, "w") as f:
                json.dump(plots, f, indent=2)
        except OSError:
            raise StorageError("Couldn't write the plot to disk — check file permissions.")

    def load_plots(self):
        if not os.path.exists(self.plots_file):
            return []

        try:
            with open(self.plots_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            raise StorageError("The plots file is corrupted and couldn't be read.")
        except OSError:
            raise StorageError("Couldn't open the plots file.")

    def delete_plot(self, plot_id):
        plots = self.load_plots()
        remaining = [p for p in plots if p.get("plot_id") != plot_id]

        if len(remaining) == len(plots):
            raise StorageError(f"No plot found with id {plot_id}.")

        try:
            with open(self.plots_file, "w") as f:
                json.dump(remaining, f, indent=2)
        except OSError:
            raise StorageError("Couldn't update the plots file.")

    def clear_plots(self):
        try:
            with open(self.plots_file, "w") as f:
                json.dump([], f, indent=2)
        except OSError:
            raise StorageError("Couldn't clear the plots file.")

    def clear_logs(self):
        try:
            if os.path.exists(self.logs_file):
                os.remove(self.logs_file)
        except OSError:
            raise StorageError("Couldn't clear the logs file.")

    # ---------- logs (csv) ----------

    def append_log(self, entry):
        row = entry.to_row()
        file_exists = os.path.exists(self.logs_file)

        try:
            with open(self.logs_file, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=row.keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)
        except OSError:
            raise StorageError("Couldn't write the log entry to disk.")

    def load_logs(self):
        if not os.path.exists(self.logs_file):
            return []

        try:
            with open(self.logs_file, "r", newline="") as f:
                reader = csv.DictReader(f)
                return list(reader)
        except OSError:
            raise StorageError("Couldn't read the logs file.")
        except csv.Error:
            raise StorageError("The logs file looks corrupted.")
