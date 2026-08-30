import os

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
SUPPORTED_CROPS = ["Maize", "Rice", "Cassava", "Yam", "Sorghum"]

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME = "gemini-3.6-flash"

DATA_DIR = "data"
PLOTS_FILE = os.path.join(DATA_DIR, "farm_plots.json")
LOGS_FILE = os.path.join(DATA_DIR, "farm_logs.csv")

MIN_LATITUDE, MAX_LATITUDE = -90.0, 90.0
MIN_LONGITUDE, MAX_LONGITUDE = -180.0, 180.0