import streamlit as st
import random
from datetime import date as dt_date, datetime, timedelta
from config import SUPPORTED_CROPS

# Real backend modules — replacing the dummy data above.
from validators import validate_location_name, validate_coordinate, validate_date, ValidationError
from data_models import FarmPlot, LogEntry
from weather_service import WeatherService, WeatherServiceError
from storage import PlotStorage, StorageError
from AI_advisor import AIAdvisor, AIAdvisorError

# Each of these is created ONCE when the script first loads. Streamlit
# reruns this whole file on every click, but module-level code like this
# only re-executes the cheap parts — these objects don't hold open
# connections, so creating them fresh each rerun is fine and simple.
weather_service = WeatherService()
storage = PlotStorage()

MONTHS = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12
}

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


# ============================================================
# Crop class + season calendar generator
# ============================================================
# The original brief calls for a "Crop" class and a season calendar
# (planting -> weeding -> harvest). Neither was assigned to anyone in
# the group's task-division doc, so it lives here in app.py.
#
# The day-counts below are typical agronomic averages for staple crops
# grown across Nigeria and similar tropical/sub-tropical regions, drawn
# from standard agricultural-extension guidance (FAO crop calendars and
# CGIAR/IITA variety guides). Real durations vary by specific variety,
# local climate, and soil — these are sensible defaults, not a
# substitute for the planting guide that comes with a specific seed
# variety.
class Crop:
    """Represents one crop's typical growth-stage timeline, in days
    counted from the planting date."""

    def __init__(self, name: str, weeding_days: list, harvest_days: int):
        self.name = name
        self.weeding_days = weeding_days  # e.g. [21, 45] -> two weeding rounds
        self.harvest_days = harvest_days  # e.g. 110 -> ready to harvest on day 110

    def build_calendar(self, planting_date) -> list:
        """
        planting_date: a datetime.date object.
        Returns a list of {"stage": str, "date": date} dicts, in order —
        planting, each weeding round, then harvest.
        """
        calendar = [{"stage": "Planting", "date": planting_date}]
        for i, days in enumerate(self.weeding_days, start=1):
            label = "Weeding" if len(self.weeding_days) == 1 else f"Weeding (round {i})"
            calendar.append({"stage": label, "date": planting_date + timedelta(days=days)})
        calendar.append({"stage": "Harvest", "date": planting_date + timedelta(days=self.harvest_days)})
        return calendar


CROP_PROFILES = {
    "Maize":    Crop("Maize",    weeding_days=[21, 42],     harvest_days=110),
    "Rice":     Crop("Rice",     weeding_days=[21, 42],     harvest_days=120),
    "Cassava":  Crop("Cassava",  weeding_days=[30, 90],     harvest_days=300),
    "Yam":      Crop("Yam",      weeding_days=[30, 60, 90], harvest_days=240),
    "Sorghum":  Crop("Sorghum",  weeding_days=[21, 42],     harvest_days=105),
}


def generate_season_calendar(crop_name: str, planting_date_str: str) -> list:
    """
    crop_name: must be a key in CROP_PROFILES (matches SUPPORTED_CROPS).
    planting_date_str: "YYYY-MM-DD" string, already validated by validate_date().
    """
    crop_obj = CROP_PROFILES.get(crop_name)
    if crop_obj is None:
        return []  # unknown crop — nothing to build a calendar from
    planting_date = datetime.strptime(planting_date_str, "%Y-%m-%d").date()
    return crop_obj.build_calendar(planting_date)


# ============================================================
# Weather threat checker
# ============================================================
# Thresholds here are real, commonly-cited meteorological/agronomic
# standards (not arbitrary numbers), so this works for any location
# worldwide that Open-Meteo covers — the same thresholds apply whether
# the plot is in Nigeria, Brazil, or Vietnam:
#
#  - Heavy rain: >=50mm in 24 hours is widely used by national
#    meteorological services (WMO-aligned) as the threshold for
#    "heavy rain" warnings.
#  - Dry spell: agricultural advisories commonly flag 7+ consecutive
#    days with under 1mm rain as a dry-spell risk to crop water needs.
#  - Heat stress: most staple crops (maize, rice, etc.) begin showing
#    heat stress above roughly 35°C, per crop physiology literature.
#    We check BOTH the current reading (immediate alert) and the 7-day
#    forecasted daily highs from weather_service.py's temperature_max_forecast_c
#    (a true multi-day heatwave check — 3+ consecutive hot days is a
#    commonly used meteorological definition of a heatwave).
HEAVY_RAIN_MM = 50
DRY_SPELL_DAYS = 7
DRY_DAY_THRESHOLD_MM = 1.0
HEAT_STRESS_C = 35
HEATWAVE_CONSECUTIVE_DAYS = 3


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


st.set_page_config(page_title="Smart Farming Advisor", page_icon="🧑‍🌾", layout="wide")
st.title("Smart Farming Advisor")

season = st.selectbox("Season", ["Spring (rain)", "Summer (sun)", "Autumn (leaves)", "Winter (snow)"])

season_config = {
    "Spring (rain)": {"emoji": "`", "count": 500, "min_dur": 1.2, "max_dur": 2.5, "anim": "rainFall", "ground": "#6B8E23", "ground2": "#556B2F"},
    "Summer (sun)": {"emoji": "", "count": 18, "min_dur": 2, "max_dur": 4, "anim": "sunSparkle", "ground": "#DAA520", "ground2": "#B8860B"},
    "Autumn (leaves)": {"emoji": "🍂", "count": 22, "min_dur": 5, "max_dur": 9, "anim": "leafSwirl", "ground": "#C1440E", "ground2": "#8B4513"},
    "Winter (snow)": {"emoji": "❄️", "count": 30, "min_dur": 6, "max_dur": 11, "anim": "snowDrift", "ground": "#E8F1F8", "ground2": "#C9DCE8"},
}
cfg = season_config[season]

particles_html = ""
for _ in range(cfg["count"]):
    left = random.uniform(0, 100)
    duration = random.uniform(cfg["min_dur"], cfg["max_dur"])
    delay = random.uniform(0, 6)
    size = random.uniform(14, 26)
    drift = random.uniform(-60, 60)
    if season == "Summer (sun)":
        top = random.uniform(0, 85)
        particles_html += f'<div class="particle" style="left:{left}%; top:{top}%; animation-name:{cfg["anim"]}; animation-duration:{duration}s; animation-delay:{delay}s; font-size:{size}px;">{cfg["emoji"]}</div>'
    else:
        particles_html += f'<div class="particle" style="left:{left}%; top:-40px; --drift:{drift}px; animation-name:{cfg["anim"]}; animation-duration:{duration}s; animation-delay:{delay}s; font-size:{size}px;">{cfg["emoji"]}</div>'

stars_html = ""
for _ in range(40):
    sleft = random.uniform(0, 100)
    stop = random.uniform(0, 55)
    ssize = random.uniform(1.5, 3)
    sdelay = random.uniform(0, 4)
    stars_html += f'<div class="star" style="left:{sleft}%; top:{stop}%; width:{ssize}px; height:{ssize}px; animation-delay:{sdelay}s;"></div>'

day_night_stages = [
    (0,   "#FFDAB9", "#87CEEB"),
    (16,  "#FFD580", "#FFA500"),
    (32,  "#C97A5A", "#8A5A8A"),
    (48,  "#0D0D14", "#050508"),
    (64,  "#0D0D18", "#1A1A2E"),
    (80,  "#E88C6E", "#FFB88C"),
    (100, "#FFDAB9", "#87CEEB"),
]

def lerp_color(c1, c2, t):
    c1 = c1.lstrip("#")
    c2 = c2.lstrip("#")
    r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
    r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
    r = round(r1 + (r2 - r1) * t)
    g = round(g1 + (g2 - g1) * t)
    b = round(b1 + (b2 - b1) * t)
    return f"#{r:02X}{g:02X}{b:02X}"

def color_at_percent(p):
    for i in range(len(day_night_stages) - 1):
        p0, top0, bot0 = day_night_stages[i]
        p1, top1, bot1 = day_night_stages[i + 1]
        if p0 <= p <= p1:
            t = 0 if p1 == p0 else (p - p0) / (p1 - p0)
            return lerp_color(top0, top1, t), lerp_color(bot0, bot1, t)
    return day_night_stages[-1][1], day_night_stages[-1][2]

keyframe_lines = ""
for pct in range(0, 101):
    top, bottom = color_at_percent(pct)
    keyframe_lines += f"{pct}% {{ background: linear-gradient(180deg, {top}, {bottom}); }}\n"

st.markdown(f"""
<style>
:root {{
    --ground1: {cfg['ground']};
    --ground2: {cfg['ground2']};
}}

@property --sky-top {{
    syntax: '<color>';
    inherits: false;
    initial-value: #FFDAB9;
}}
@property --sky-bottom {{
    syntax: '<color>';
    inherits: false;
    initial-value: #87CEEB;
}}

@keyframes dayNightCycle {{
    0%   {{ --sky-top: #FFDAB9; --sky-bottom: #87CEEB; }}
    16%  {{ --sky-top: #FFD580; --sky-bottom: #FFA500; }}
    32%  {{ --sky-top: #C97A5A; --sky-bottom: #8A5A8A; }}
    48%  {{ --sky-top: #0D0D14; --sky-bottom: #050508; }}
    64%  {{ --sky-top: #0D0D18; --sky-bottom: #1A1A2E; }}
    80%  {{ --sky-top: #E88C6E; --sky-bottom: #FFB88C; }}
    100% {{ --sky-top: #FFDAB9; --sky-bottom: #87CEEB; }}
}}

.stApp {{
    background: linear-gradient(180deg, var(--sky-top), var(--sky-bottom));
    animation: dayNightCycle 40s linear infinite;
    overflow-x: hidden;
}}

.stAppHeader {{
    background: transparent !important;
}}

.stAppDeployButton {{
    background: transparent !important;
    border: 1px solid rgba(255,255,255,0.7) !important;
    border-radius: 12px !important;
    color: white !important;
    box-shadow: none !important;
}}

.stAppDeployButton:hover {{
    background: rgba(255,255,255,0.08) !important;
    border-color: white !important;
}}
h1 {{ color: #FFF8E7 !important; font-weight: 800; text-shadow: 0 2px 6px rgba(0,0,0,0.4); }}
p, label, .stMarkdown, span {{ color: #FFF8E7 !important; }}

div[data-testid="stMetric"] {{
    background: rgba(255,255,255,0.15); backdrop-filter: blur(8px);
    border: 1px solid rgba(255,255,255,0.3); border-radius: 16px; padding: 20px;
}}
div[data-testid="stForm"] {{
    background: rgba(255,255,255,0.12); backdrop-filter: blur(10px);
    border-radius: 20px; padding: 28px; border: 1px solid rgba(255,255,255,0.25);
}}
.stButton > button {{
    background: linear-gradient(90deg, var(--ground1), var(--ground2));
    color: white; border-radius: 30px; border: none; padding: 12px 32px; font-weight: 700;
}}
.stButton > button:hover {{ transform: scale(1.03); }}

.scene {{ position: fixed; top:0; left:0; width:100%; height:100%; pointer-events:none; overflow:hidden; z-index:0; }}

.sun, .moon {{
    position: absolute;
    width: 70px; height: 70px;
    border-radius: 50%;
    top: 12%; right: 10%;
    animation-duration: 40s;
    animation-timing-function: linear;
    animation-iteration-count: infinite;
}}
.sun {{
    background: radial-gradient(circle, #FFF6B0, #FFD23F);
    box-shadow: 0 0 50px 14px rgba(255,210,63,0.55);
    animation-name: sunGlow;
}}
.moon {{
    background: radial-gradient(circle, #F4F6FF, #C9CEE0);
    box-shadow: 0 0 30px 10px rgba(200,210,255,0.5);
    animation-name: moonGlow;
}}
@keyframes sunGlow {{
    0%   {{ opacity: 1; }}
    36%  {{ opacity: 1; }}
    46%  {{ opacity: 0; }}
    86%  {{ opacity: 0; }}
    96%  {{ opacity: 1; }}
    100% {{ opacity: 1; }}
}}
@keyframes moonGlow {{
    0%   {{ opacity: 0; }}
    36%  {{ opacity: 0; }}
    46%  {{ opacity: 1; }}
    86%  {{ opacity: 1; }}
    96%  {{ opacity: 0; }}
    100% {{ opacity: 0; }}
}}

.star {{
    position: absolute; background: white; border-radius: 50%;
    box-shadow: 0 0 6px 1px rgba(255,255,255,0.8);
    animation-name: starTwinkle; animation-duration: 40s; animation-iteration-count: infinite;
}}
@keyframes starTwinkle {{
    0%   {{ opacity: 0; }}
    30%  {{ opacity: 0; }}
    50%  {{ opacity: 1; }}
    75%  {{ opacity: 0.5; }}
    100% {{ opacity: 0; }}
}}

.hills {{
    position: fixed; bottom:0; left:0; width:100%; height:120px;
    background: linear-gradient(180deg, var(--ground1), var(--ground2));
    border-radius: 50% 50% 0 0 / 100% 100% 0 0;
    z-index: 0; transition: background 1.5s ease;
}}

.particle {{ position: absolute; animation-timing-function: linear; animation-iteration-count: infinite; }}

@keyframes rainFall {{
    0%   {{ transform: translateY(0) rotate(15deg); opacity: 0.8; }}
    100% {{ transform: translateY(110vh) translateX(40px) rotate(15deg); opacity: 0.3; }}
}}
@keyframes snowDrift {{
    0%   {{ transform: translateY(0) translateX(0) rotate(0deg); opacity: 0.9; }}
    50%  {{ transform: translateY(55vh) translateX(var(--drift)) rotate(180deg); opacity: 0.7; }}
    100% {{ transform: translateY(110vh) translateX(0) rotate(360deg); opacity: 0.2; }}
}}
@keyframes leafSwirl {{
    0%   {{ transform: translateY(0) translateX(0) rotate(0deg); opacity: 0.9; }}
    50%  {{ transform: translateY(55vh) translateX(var(--drift)) rotate(200deg); opacity: 0.8; }}
    100% {{ transform: translateY(110vh) translateX(-20px) rotate(400deg); opacity: 0.2; }}
}}
@keyframes sunSparkle {{
    0%, 100% {{ opacity: 0.2; transform: scale(0.8); }}
    50%      {{ opacity: 1;   transform: scale(1.2); }}
}}

.fade-in {{ animation: fadeIn 1.2s ease; }}
@keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}

</style>

<div class="scene fade-in">
    <div class="sun"></div>
    <div class="moon"></div>
    {stars_html}
    <div class="hills"></div>
    {particles_html}
</div>
""", unsafe_allow_html=True)

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