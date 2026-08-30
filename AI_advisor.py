"""
ai_advisor.py
Person 4 — AI Advisor

Turns crop + location + weather data into plain-language planting
advice, using Google's Gemini API through the google-genai SDK.
"""

from google import genai  # the official Gemini SDK — pip install google-genai

from config import GEMINI_API_KEY, GEMINI_MODEL_NAME
# GEMINI_API_KEY and GEMINI_MODEL_NAME already live in config.py, read from
# the environment there — we just import the finished values, we don't
# touch os.environ ourselves in this file.


class AIAdvisorError(Exception):
    # One error type for every way the Gemini call can fail: no key, bad
    # key, network failure, empty response. app.py only needs to catch
    # this ONE exception type to handle all of them.
    pass


class AIAdvisor:
    def __init__(self):
        # Fail fast and clearly if there's no key, instead of letting a
        # confusing error surface later when we actually try to call Gemini.
        if not GEMINI_API_KEY:
            raise AIAdvisorError(
                "No Gemini API key found. Set the GEMINI_API_KEY environment "
                "variable before running the app."
            )

        try:
            # genai.Client is the object that actually talks to Google's servers.
            self.client = genai.Client(api_key=GEMINI_API_KEY)
        except Exception as e:
            # Catching the SDK's own exception and re-raising as OUR
            # exception type keeps app.py's except blocks simple —
            # it only ever needs to know about AIAdvisorError.
            raise AIAdvisorError(f"Failed to initialize the Gemini client: {e}")

        self.model = GEMINI_MODEL_NAME

    def _build_prompt(self, crop: str, location: str, weather_dict: dict) -> str:
        """
        Turns the structured weather dict into a plain English prompt.
        Leading underscore means "internal helper" — not meant to be
        called from outside this class (app.py never calls this directly).

        weather_dict comes straight from WeatherService.get_conditions(),
        so the keys here match that file exactly:
        temperature_Celsius, humidity_pct, soil_temperature_c,
        soil_moisture, rain_forecast_mm (list of 7 values).
        """
        temp = weather_dict.get("temperature_Celsius", "unknown")
        humidity = weather_dict.get("humidity_pct", "unknown")
        soil_temp = weather_dict.get("soil_temperature_c", "unknown")
        soil_moisture = weather_dict.get("soil_moisture", "unknown")
        rain_forecast = weather_dict.get("rain_forecast_mm", [])
        max_temp_forecast = weather_dict.get("temperature_max_forecast_c", [])

        rain_forecast_str = ", ".join(str(mm) for mm in rain_forecast) or "unknown"
        max_temp_forecast_str = ", ".join(str(t) for t in max_temp_forecast) or "unknown"

        # An f-string with triple quotes lets us write a multi-line prompt
        # cleanly, with {variables} filled in automatically.
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
        """
        Public method — this is the one app.py calls.
        Returns Gemini's advice as a plain string.
        Raises AIAdvisorError on any failure so app.py can show
        a clean error message instead of crashing.
        """
        prompt = self._build_prompt(crop, location, weather_dict)

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
        except Exception as e:
            # Any SDK/network failure lands here — rate limits, timeouts,
            # invalid key rejected server-side, etc.
            raise AIAdvisorError(f"Gemini API request failed: {e}")

        # getattr(response, "text", None) safely reads response.text,
        # returning None instead of crashing if that attribute is missing.
        text = getattr(response, "text", None)
        if not text:
            raise AIAdvisorError("Gemini returned an empty response. Please try again.")

        return text.strip()  # strip() removes leading/trailing whitespace


if __name__ == "__main__":
    # Manual test — run with: python ai_advisor.py
    # Requires GEMINI_API_KEY to be set in your environment first.
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