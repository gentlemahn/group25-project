import requests
from config import OPEN_METEO_FORECAST_URL, OPEN_METEO_GEOCODING_URL
from validators import validate_coordinate, ValidationError

HEAVY_RAIN_MM = 50
DRY_SPELL_DAYS = 7
DRY_DAY_THRESHOLD_MM = 1.0
HEAT_STRESS_C = 35
HEATWAVE_CONSECUTIVE_DAYS = 3


class WeatherServiceError(Exception):
    # raised whenever something goes wrong talking to Open-Meteo
    pass


class WeatherService:
    """Pulls current + forecast weather data from Open-Meteo for a given spot."""

    def get_conditions(self, latitude, longitude):
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,soil_temperature_0cm,soil_moisture_0_to_1cm",
            # Added temperature_2m_max: gives a forecasted daily HIGH for each
            # of the next 7 days, not just the single current-moment reading.
            # Needed for a genuine multi-day heatwave check, since the
            # current temperature alone only tells you about right now.
            "daily": "precipitation_sum,temperature_2m_max",
            "forecast_days": 7,
            "timezone": "auto",
        }

        try:
            response = requests.get(OPEN_METEO_FORECAST_URL, params=params, timeout=10)
        except requests.exceptions.Timeout:
            raise WeatherServiceError("The weather service took too long to respond. Try again in a bit.")
        except requests.exceptions.ConnectionError:
            raise WeatherServiceError("Couldn't reach the weather service — check your internet connection.")

        # non-200 responses don't raise on their own, so check manually
        if response.status_code != 200:
            raise WeatherServiceError(f"Weather service returned an error (status {response.status_code}).")

        try:
            data = response.json()
        except ValueError:
            raise WeatherServiceError("Got a response back but it wasn't valid data. Please try again.")

        try:
            current = data["current"]
            daily = data["daily"]

            conditions = {
                "temperature_Celsius": current["temperature_2m"],
                "humidity_pct": current["relative_humidity_2m"],
                "soil_temperature_c": current["soil_temperature_0cm"],
                "soil_moisture": current["soil_moisture_0_to_1cm"],
                "rain_forecast_mm": daily["precipitation_sum"],  # list of 7 values, one per day
                "temperature_max_forecast_c": daily["temperature_2m_max"],  # 7 daily highs
                "forecast_dates": daily["time"],
            }
        except KeyError as missing:
            raise WeatherServiceError(f"Weather data was missing a field we needed ({missing}). Try again later.")

        return conditions
    
    def geocode_location(self, location_name):
        """
        Converts a location name (e.g. 'Gombe') into (latitude, longitude)
        using Open-Meteo's free geocoding API. Raises WeatherServiceError
        if the location can't be found or the request fails.
        """
        params = {"name": location_name, "count": 1, "language": "en", "format": "json"}

        try:
            response = requests.get(OPEN_METEO_GEOCODING_URL, params=params, timeout=10)
        except requests.exceptions.Timeout:
            raise WeatherServiceError("The location lookup took too long to respond. Try again in a bit.")
        except requests.exceptions.ConnectionError:
            raise WeatherServiceError("Couldn't reach the location lookup service — check your internet connection.")
        except requests.exceptions.RequestException as e:
            raise WeatherServiceError(f"Unexpected error looking up the location: {e}")

        if response.status_code != 200:
            raise WeatherServiceError(f"Location lookup returned an error (status {response.status_code}).")

        try:
            data = response.json()
        except ValueError:
            raise WeatherServiceError("Location lookup returned data we couldn't understand.")

        results = data.get("results")
        if not results:
            raise WeatherServiceError(
                f"Couldn't find a location matching '{location_name}'. Try a different spelling or a nearby larger town."
            )

        top_match = results[0]
        lat, lon = top_match["latitude"], top_match["longitude"]

        # Even though Open-Meteo should always return sane
        # values, we validate them before trusting an external API's
        # response, rather than assuming it's always correct.
        try:
            validate_coordinate(lat, "latitude")
            validate_coordinate(lon, "longitude")
        except ValidationError:
            raise WeatherServiceError(f"Location lookup for '{location_name}' returned invalid coordinates.")

        return lat, lon
def check_weather_threats(conditions: dict) -> list:
    """Returns a list of plain-language warning strings, or [] if nothing
    of concern is forecast."""
    warnings = []

    rain_forecast = conditions.get("rain_forecast_mm", [])
    forecast_dates = conditions.get("forecast_dates", [])

    # --- Heavy rain check ---
    for i, mm in enumerate(rain_forecast):
        if mm is not None and mm >= HEAVY_RAIN_MM:
            day_label = forecast_dates[i] if i < len(forecast_dates) else f"day {i + 1}"
            warnings.append(f"Heavy rain expected on {day_label} ({mm}mm) — risk of waterlogging or erosion.")
        
    TOTAL_WEEKLY_RAIN_MM = 70  # cumulative rain over the week that's worth flagging

    # --- Sustained heavy rain check (total, not just single-day) ---
    total_rain = sum(mm for mm in rain_forecast if mm is not None)
    if total_rain >= TOTAL_WEEKLY_RAIN_MM:
        warnings.append(f"Sustained heavy rain expected this week — {total_rain}mm total forecast. Risk of waterlogging.")

    # --- Dry spell check ---
    # We scan the week for the LONGEST run of consecutive dry days,
    # not just whether the whole week is dry.
    consecutive_dry = 0
    longest_dry_run = 0
    for mm in rain_forecast:
        if mm is not None and mm < DRY_DAY_THRESHOLD_MM:
            consecutive_dry += 1
            longest_dry_run = max(longest_dry_run, consecutive_dry)
        else:
            consecutive_dry = 0  # any real rain resets the streak
    if longest_dry_run >= DRY_SPELL_DAYS:
        warnings.append(
            f"Dry spell risk: {longest_dry_run} consecutive days with little or no rain forecast."
        )

    # --- Heat stress check ---
    # 1) Immediate alert: is it hot RIGHT NOW?
    temp = conditions.get("temperature_Celsius")
    if temp is not None and temp >= HEAT_STRESS_C:
        warnings.append(f"High temperature alert: {temp}°C right now — heat stress risk for most crops.")

    # 2) True heatwave check: are there 3+ CONSECUTIVE forecasted days
    # with a daily high above the threshold? A single hot day isn't a
    # heatwave — a sustained run of them is what actually stresses crops
    # and depletes soil moisture faster than expected.
    max_temps = conditions.get("temperature_max_forecast_c", [])
    consecutive_hot = 0
    longest_hot_run = 0
    hot_run_start_index = None
    longest_run_start_index = None
    for i, day_max in enumerate(max_temps):
        if day_max is not None and day_max >= HEAT_STRESS_C:
            if consecutive_hot == 0:
                hot_run_start_index = i
            consecutive_hot += 1
            if consecutive_hot > longest_hot_run:
                longest_hot_run = consecutive_hot
                longest_run_start_index = hot_run_start_index
        else:
            consecutive_hot = 0
    if longest_hot_run >= HEATWAVE_CONSECUTIVE_DAYS:
        start_label = (
            forecast_dates[longest_run_start_index]
            if longest_run_start_index is not None and longest_run_start_index < len(forecast_dates)
            else "the coming days"
        )
        warnings.append(
            f"Heatwave risk: {longest_hot_run} consecutive days forecast at or above "
            f"{HEAT_STRESS_C}°C, starting {start_label}."
        )

    return warnings
