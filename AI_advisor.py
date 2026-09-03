from google import genai  # the official Gemini SDK — pip install google-genai

from config import GEMINI_API_KEY, GEMINI_MODEL_NAME

class AIAdvisorError(Exception):
    pass


class AIAdvisor:
    def __init__(self):

        if not GEMINI_API_KEY:
            raise AIAdvisorError("No Gemini API key found. Set GEMINI_API_KEY in your .env file.")

        try:
            self.client = genai.Client(api_key=GEMINI_API_KEY)
        except Exception as e:
            raise AIAdvisorError(f"Failed to initialize the Gemini client: {e}")

        self.model = GEMINI_MODEL_NAME

    def _build_prompt(self, crop: str, location: str, weather_dict: dict) -> str:
        temp = weather_dict.get("temperature_Celsius", "unknown")
        humidity = weather_dict.get("humidity_pct", "unknown")
        soil_temp = weather_dict.get("soil_temperature_c", "unknown")
        soil_moisture = weather_dict.get("soil_moisture", "unknown")
        rain_forecast = weather_dict.get("rain_forecast_mm", [])
        max_temp_forecast = weather_dict.get("temperature_max_forecast_c", [])

        rain_forecast_str = ", ".join(str(mm) for mm in rain_forecast) or "unknown"
        max_temp_forecast_str = ", ".join(str(t) for t in max_temp_forecast) or "unknown"
        prompt = f"""You are an agricultural advisor helping a smallholder farmer.

Crop: {crop}
Location: {location}
Current temperature: {temp} °C
Humidity: {humidity}%
Soil temperature: {soil_temp} °C
Soil moisture: {soil_moisture}
7-day rainfall forecast (mm/day): {rain_forecast_str}
7-day forecasted daily high temperatures (°C): {max_temp_forecast_str}

Based on this data, give the farmer clear, practical advice covering:
1. Whether now is a good time to plant {crop} (yes/no/wait, with a short reason)
2. The best planting window in the coming days
3. Irrigation needs given current soil moisture and rainfall
4. Likely pest or disease risks for {crop} in this weather/season

Keep the answer short, plain-language, and actionable — no more than 150 words.
"""
        return prompt

    def get_planting_advice(self, crop: str, location: str, weather_dict: dict) -> str:
        prompt = self._build_prompt(crop, location, weather_dict)

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
        except Exception as e:
            raise AIAdvisorError(f"Gemini API request failed: {e}")

        text = getattr(response, "text", None)
        if not text:
            raise AIAdvisorError("Gemini returned an empty response. Please try again.")

        return text.strip()


if __name__ == "__main__":
    try:
        advisor = AIAdvisor()
        fake_weather = {
            "temperature_Celsius": 28.5,
            "humidity_pct": 60,
            "soil_temperature_c": 26.0,
            "soil_moisture": 0.22,
            "rain_forecast_mm": [0, 3.2, 15.0, 8.1, 0, 0, 0],
        }
        advice = advisor.get_planting_advice("maize", "Kano, Nigeria", fake_weather)
        print(advice)
    except AIAdvisorError as e:
        print(f"AIAdvisorError: {e}")