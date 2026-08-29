import requests

from config import OPEN_METEO_FORECAST_URL


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
            "daily": "precipitation_sum",
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
                "forecast_dates": daily["time"],
            }
        except KeyError as missing:
            raise WeatherServiceError(f"Weather data was missing a field we needed ({missing}). Try again later.")

        return conditions
