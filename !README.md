# 🌾 Smart Farming & Crop Planting Advisor

Streamlit app: enter a crop + location → get real weather/soil data, AI planting
advice (Gemini), weather threat warnings, and a season calendar. Everything saves
to disk.

📊 See `DIAGRAMS.md` for the module map + submit workflow diagrams.

---

## Setup

```bash
pip install -r requirements.txt
```

`requirements.txt`:
```
streamlit
requests
python-dotenv
google-genai
```

Create a `.env` file (already in `.gitignore`):
```
GEMINI_API_KEY=your_real_key_here
```
Get a key at [aistudio.google.com](https://aistudio.google.com) → Get API key → Create API key.

Run:
```bash
streamlit run app.py
```

---

## Project structure

```
app.py               # Streamlit UI — run this file
config.py             # Constants: URLs, file paths, crop list, ranges
validators.py          # Regex-based input validation
data_models.py         # FarmPlot + LogEntry dataclasses
weather_service.py     # Open-Meteo API client
storage.py             # JSON/CSV save + load
AI_advisor.py          # Gemini API client
.env                   # GEMINI_API_KEY (never committed)
data/
  farm_plots.json      # auto-created on first save
  farm_logs.csv        # auto-created on first save
```

---

## Modules

### `config.py`
Imports: `os`, `dotenv.load_dotenv`

Just constants — no functions. Holds `OPEN_METEO_FORECAST_URL`, `SUPPORTED_CROPS`,
`GEMINI_API_KEY`/`GEMINI_MODEL_NAME`, `PLOTS_FILE`/`LOGS_FILE`, and the valid
lat/lon ranges. Everything else reads from here.

### `validators.py`
Imports: `re`, `datetime`

- `validate_location_name(name)` — checks 2-80 chars, letters/spaces/hyphens/
  apostrophes/commas only. Returns the cleaned name.
- `validate_coordinate(value, kind)` — checks it's a decimal number, then checks
  the range for `"latitude"` or `"longitude"`. Returns a `float`.
- `validate_date(date_str)` — checks strict `YYYY-MM-DD` shape + that it's a real
  calendar date (catches Feb 30 etc).
- All three raise `ValidationError` on bad input.

### `data_models.py`
Imports: `dataclasses`, `datetime`, `uuid`

- **`FarmPlot`** — crop, location_name, latitude, longitude + auto `plot_id`/
  `created_at`. `to_dict()` / `from_dict()` convert to/from JSON-ready dicts.
- **`LogEntry`** — plot_id, date, crop, location_name, temperature_Celsius,
  humidity_pct, advice_summary + auto `log_id`. `to_row()` converts to a flat
  dict for CSV.

### `weather_service.py`
Imports: `requests`, `config.OPEN_METEO_FORECAST_URL`

- `WeatherService.get_conditions(lat, lon)` — calls Open-Meteo, handles
  timeouts/connection errors/bad JSON, returns a dict of current temp, humidity,
  soil data, and a 7-day rain + max-temp forecast.
- Raises `WeatherServiceError` on any failure.

### `storage.py`
Imports: `csv`, `json`, `os`, `config.PLOTS_FILE`, `config.LOGS_FILE`

**`PlotStorage`** methods:
- `save_plot(plot)` / `load_plots()` / `delete_plot(plot_id)` / `clear_plots()` — JSON
- `append_log(entry)` / `load_logs()` / `clear_logs()` — CSV
- Raises `StorageError` on any file read/write failure.

### `AI_advisor.py`
Imports: `google.genai`, `config.GEMINI_API_KEY`, `config.GEMINI_MODEL_NAME`

**`AIAdvisor`**:
- `__init__()` — checks the API key exists, sets up the Gemini client
- `_build_prompt(...)` — internal helper, formats crop/location/weather into a prompt
- `get_planting_advice(crop, location, weather_dict)` — sends the prompt to
  Gemini, returns plain-text advice
- Raises `AIAdvisorError` on missing key / bad key / network failure / empty response

### `app.py`
Imports: `streamlit`, `random`, `datetime`, `config.SUPPORTED_CROPS`, plus everything
public from the six modules above.

- **`Crop`** class + `CROP_PROFILES` dict — growth-stage day-offsets per crop
- `generate_season_calendar(crop_name, planting_date_str)` — builds the planting →
  weeding → harvest schedule
- `check_weather_threats(conditions)` — flags heavy rain (≥50mm/day), a dry spell
  (7+ dry days), or a heatwave (3+ days ≥35°C)
- The rest is the UI itself: page setup, the animated background, the form, and
  three tabs (**Plant advisor**, **Saved Plots**, **Log history**)

---

## Custom exceptions

| Exception | From |
|---|---|
| `ValidationError` | `validators.py` |
| `WeatherServiceError` | `weather_service.py` |
| `StorageError` | `storage.py` |
| `AIAdvisorError` | `AI_advisor.py` |

---