import streamlit as st
import random
from datetime import date as dt_date, datetime, timedelta
from config import SUPPORTED_CROPS
from theme import render_theme, SEASON_CONFIG

# Real backend modules — replacing the dummy data above.
from validators import validate_location_name, validate_coordinate, validate_date, ValidationError
from data_models import FarmPlot, LogEntry, MONTHS, CROP_PROFILES, generate_season_calendar
from weather_service import WeatherService, WeatherServiceError, check_weather_threats
from storage import PlotStorage, StorageError
from AI_advisor import AIAdvisor, AIAdvisorError

# Each of these is created ONCE when the script first loads. Streamlit
# reruns this whole file on every click, but module-level code like this
# only re-executes the cheap parts — these objects don't hold open
# connections, so creating them fresh each rerun is fine and simple.
weather_service = WeatherService()
storage = PlotStorage()



# The AIAdvisor is a bit more expensive to create (it validates the API key
# and sets up the Gemini client), and if the key is missing we want the
# WHOLE APP to still load and show a clear error, rather than crash before
# a single line of UI renders. So we wrap this one in try/except.
try:
    advisor = AIAdvisor()
    advisor_error = None
except AIAdvisorError as e:
    advisor = None
    advisor_error = str(e)

# Load real saved data from disk instead of hardcoded dummy lists.
# Both load_plots() and load_logs() return [] if no file exists yet,
# so a brand-new install just shows "no plots yet" instead of crashing.
try:
    saved_plots = storage.load_plots()
except StorageError as e:
    saved_plots = []
    st.error(f"Couldn't load saved plots: {e}")

try:
    saved_logs = storage.load_logs()
except StorageError as e:
    saved_logs = []
    st.error(f"Couldn't load saved logs: {e}")


st.set_page_config(page_title="Smart Farming Advisor", page_icon="🧑‍🌾", layout="wide")
st.title("Smart Farming Advisor")

season = st.selectbox("Season", ["Spring (rain)", "Summer (sun)", "Autumn (leaves)", "Winter (snow)"])
render_theme(season)

col1, col2 = st.columns(2)
col1.metric("Total plots", len(saved_plots))
col2.metric("Total Logs", len(saved_logs))

tab1 , tab2, tab3, = st.tabs(["Plant advisor", "Saved Plots", "Log history"])

with tab1:
    with st.form("plot_form"):
        crop = st.selectbox("Crop", SUPPORTED_CROPS)
        location_name = st.text_input("Location name", placeholder="e.g Nsukka")
        
        st.write(" ")
        st.write("Planting date:")    
        col5, col6, col7 = st.columns(3)
        with col5:
            day = st.selectbox("Day", range(1, 32))

        with col6:
            month_name = st.selectbox("Month", list(MONTHS.keys()))
            month = MONTHS[month_name]

        with col7:
            year = st.selectbox("Year", range(2026, 2035))

        planning_date = dt_date(year, month, day)

        submitted = st.form_submit_button("Get Planting advice")

    if submitted:
        # --- Step 1: validate inputs (Person 1's regex-based validators) ---
        # We validate everything BEFORE touching the network. No point
        # calling a weather API with a location name that has invalid
        # characters in it — fail cheap and fast first.
        try:
            clean_location = validate_location_name(location_name)
            clean_date = validate_date(str(planning_date))

            with st.spinner(f"Looking up {clean_location}..."):
                clean_lat, clean_lon = weather_service.geocode_location(clean_location)
        except ValidationError as e:
            st.error(f"Invalid input: {e}")
            # st.stop() halts execution of the rest of the script for this
            # rerun. Without it, the code below would still try to run
            # with variables like clean_location that were never created.
            st.stop()

        # --- Step 2: fetch real weather data (Person 3's WeatherService) ---
        try:
            with st.spinner("Fetching weather data..."):
                conditions = weather_service.get_conditions(clean_lat, clean_lon)
        except WeatherServiceError as e:
            st.error(f"Weather error: {e}")
            st.stop()

        # --- Step 3: get AI planting advice (your AIAdvisor) ---
        if advisor is None:
            # This happens if GEMINI_API_KEY was missing when the app started.
            advice = f"AI advice unavailable: {advisor_error}"
        else:
            try:
                with st.spinner("Asking the AI advisor..."):
                    advice = advisor.get_planting_advice(
                        crop=crop, location=clean_location, weather_dict=conditions
                    )
            except AIAdvisorError as e:
                # We deliberately DON'T st.stop() here. Losing the AI text
                # is disappointing but not critical — the farmer's plot and
                # weather reading are still worth saving. A totally failed
                # weather/validation step above is worse, so those DO stop.
                #
                # We put the real error message INSIDE advice itself (instead
                # of a separate st.warning() call) because Step 5 stashes
                # `advice` into session_state before st.rerun() fires — a
                # bare st.warning() here would get wiped out by that rerun
                # before you ever got to read it.
                advice = f"AI advice unavailable right now. Error: {e}"

        # --- Step 4: build and save the plot + log entry ---
        try:
            plot = FarmPlot(
                crop=crop,
                location_name=clean_location,
                latitude=clean_lat,
                longitude=clean_lon,
            )
            storage.save_plot(plot)  # PlotStorage calls plot.to_dict() internally

            log = LogEntry(
                plot_id=plot.plot_id,
                date=clean_date,
                crop=crop,
                location_name=clean_location,
                temperature_Celsius=conditions["temperature_Celsius"],
                humidity_pct=conditions["humidity_pct"],
                advice_summary=advice[:200],  # keep CSV rows a manageable length
            )
            storage.append_log(log)
        except StorageError as e:
            st.error(f"Storage error: {e}")
            st.stop()

        # --- Step 5: stash the results in session_state, then refresh ---
        # st.rerun() restarts the script from the top immediately, which is
        # needed so the "Saved Plots"/"Log history" tabs and the metric
        # counters pick up the new plot/log right away. But that rerun
        # happens instantly — anything just printed with st.write/st.info
        # would flash and vanish before you could read it. Storing the
        # result in session_state means it survives the rerun and renders
        # normally on the next pass through this code.
        st.session_state.last_result = {
            "crop": crop,
            "location": clean_location,
            "temperature": conditions["temperature_Celsius"],
            "advice": advice,
            "threats": check_weather_threats(conditions),
            "calendar": generate_season_calendar(crop, clean_date),
        }
        st.rerun()

    # Show the most recent result, if any — persists across the rerun above.
    if "last_result" in st.session_state:
        result = st.session_state.last_result
        st.success(f"Saved {result['crop']} at {result['location']}. Current temp: {result['temperature']}°C")

        st.subheader("Planting Advice")
        st.info(result["advice"])

        st.subheader("⚠️ Weather Warnings")
        if result["threats"]:
            for warning in result["threats"]:
                st.warning(warning)
        else:
            st.success("No heavy rain, dry spell, or heat stress flagged in the forecast.")

        st.subheader("📅 Season Calendar")
        for stage in result["calendar"]:
            st.write(f"**{stage['stage']}**: {stage['date'].isoformat()}")

st.divider()

with tab2:
    st.subheader("Saved Plots")

    if not saved_plots:
        st.info("No plots saved yet — add one in the Plant advisor tab.")

    for p in saved_plots:
        # Two columns: plot info on the left, a delete button on the right.
        col_a, col_b = st.columns([4, 1])
        with col_a:
            st.write(f"{p['crop']} -- {p['location_name']}")
        with col_b:
            # key=f"del_{p['plot_id']}" gives each button a UNIQUE identity.
            # Without a unique key, Streamlit can't tell the delete buttons
            # for different plots apart, since they'd all be labeled "Delete".
            if st.button("Delete", key=f"del_{p['plot_id']}"):
                try:
                    storage.delete_plot(p["plot_id"])
                    st.rerun()
                except StorageError as e:
                    st.error(f"Couldn't delete: {e}")

        # A plot's planting date isn't stored on the plot itself — only on
        # its log entries. Find this plot's earliest log to use as the
        # planting date, then rebuild its season calendar from that.
        plot_logs = [log for log in saved_logs if log.get("plot_id") == p["plot_id"]]
        if plot_logs:
            earliest_date = min(log["date"] for log in plot_logs)
            with st.expander(f"📅 Season calendar for {p['crop']} at {p['location_name']}"):
                calendar = generate_season_calendar(p["crop"], earliest_date)
                for stage in calendar:
                    st.write(f"**{stage['stage']}**: {stage['date'].isoformat()}")

st.divider()

with tab3:
    st.subheader("Log history")

    if st.button("Clear all logs"):
        try:
            storage.clear_logs()
            st.rerun()
        except StorageError as e:
            st.error(f"Couldn't clear logs: {e}")

    if not saved_logs:
        st.info("No log entries yet.")

    for log in saved_logs:
        st.write(
            f"{log['date']} -- {log['crop']} at {log['location_name']} "
            f"({log['temperature_Celsius']}°C, {log['humidity_pct']}% humidity)"
        )
        if log.get("advice_summary"):
            st.caption(log["advice_summary"])