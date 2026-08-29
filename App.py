import streamlit as st
import random
from datetime import datetime
from config import SUPPORTED_CROPS
from data_models import FarmPlot, LogEntry
from validators import validate_location_name, validate_coordinate, validate_date, ValidationError
from weather_service import WeatherService, WeatherServiceError
from storage import PlotStorage, StorageError

weather_service = WeatherService()
storage = PlotStorage()

try:
    saved_plots = storage.load_plots()
except StorageError as e:
    saved_plots = []
    st.error(f"Couldn't load plots: {e}")

try:
    saved_logs = storage.load_logs()
except StorageError as e:
    saved_logs = []
    st.error(f"Couldn't load logs: {e}")

st.set_page_config(page_title="Smart Farming Advisor", page_icon="🧑‍🌾", layout="wide")
st.title("Smart Farming And Crop Planting Advisor")

season = st.selectbox("Season", ["Spring (rain)", "Summer (sun)", "Autumn (leaves)", "Winter (snow)"])

season_config = {
    "Spring (rain)": {"emoji": "`", "count": 100, "min_dur": 1.2, "max_dur": 2.5, "anim": "rainFall", "ground": "#6B8E23", "ground2": "#556B2F"},
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

st.markdown(f"""
<style>
:root {{
    --ground1: {cfg['ground']};
    --ground2: {cfg['ground2']};
}}
@property --sky-top {{ syntax: '<color>'; inherits: false; initial-value: #FFDAB9; }}
@property --sky-bottom {{ syntax: '<color>'; inherits: false; initial-value: #87CEEB; }}
@keyframes dayNightCycle {{
    0%   {{ --sky-top: #FFDAB9; --sky-bottom: #87CEEB; }}
    16%  {{ --sky-top: #FFD580; --sky-bottom: #FFA500; }}
    32%  {{ --sky-top: #C97A5A; --sky-bottom: #8A5A8A; }}
    48%  {{ --sky-top: #0D0D14; --sky-bottom: #050508; }}
    64%  {{ --sky-top: #0D0D18; --sky-bottom: #1A1A2E; }}
    80%  {{ --sky-top: #E88C6E; --sky-bottom: #FFB88C; }}
    100% {{ --sky-top: #FFDAB9; --sky-bottom: #87CEEB; }}
}}
.stApp {{ background: linear-gradient(180deg, var(--sky-top), var(--sky-bottom)); animation: dayNightCycle 40s linear infinite; overflow-x: hidden; }}
.stAppHeader {{ background: transparent !important; }}
.stAppDeployButton {{ background: transparent !important; border: 1px solid rgba(255,255,255,0.7) !important; border-radius: 12px !important; color: white !important; box-shadow: none !important; }}
.stAppDeployButton:hover {{ background: rgba(255,255,255,0.08) !important; border-color: white !important; }}
h1 {{ color: #FFF8E7 !important; font-weight: 800; text-shadow: 0 2px 6px rgba(0,0,0,0.4); }}
p, label, .stMarkdown, span {{ color: #FFF8E7 !important; }}
div[data-testid="stMetric"] {{ background: rgba(255,255,255,0.15); backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.3); border-radius: 16px; padding: 20px; }}
div[data-testid="stForm"] {{ background: rgba(255,255,255,0.12); backdrop-filter: blur(10px); border-radius: 20px; padding: 28px; border: 1px solid rgba(255,255,255,0.25); }}
.stButton > button {{ background: linear-gradient(90deg, var(--ground1), var(--ground2)); color: white; border-radius: 30px; border: none; padding: 12px 32px; font-weight: 700; }}
.stButton > button:hover {{ transform: scale(1.03); }}
.scene {{ position: fixed; top:0; left:0; width:100%; height:100%; pointer-events:none; overflow:hidden; z-index:0; }}
.sun, .moon {{ position: absolute; width: 70px; height: 70px; border-radius: 50%; top: 12%; right: 10%; animation-duration: 40s; animation-timing-function: linear; animation-iteration-count: infinite; }}
.sun {{ background: radial-gradient(circle, #FFF6B0, #FFD23F); box-shadow: 0 0 50px 14px rgba(255,210,63,0.55); animation-name: sunGlow; }}
.moon {{ background: radial-gradient(circle, #F4F6FF, #C9CEE0); box-shadow: 0 0 30px 10px rgba(200,210,255,0.5); animation-name: moonGlow; }}
@keyframes sunGlow {{ 0% {{ opacity: 1; }} 36% {{ opacity: 1; }} 46% {{ opacity: 0; }} 86% {{ opacity: 0; }} 96% {{ opacity: 1; }} 100% {{ opacity: 1; }} }}
@keyframes moonGlow {{ 0% {{ opacity: 0; }} 36% {{ opacity: 0; }} 46% {{ opacity: 1; }} 86% {{ opacity: 1; }} 96% {{ opacity: 0; }} 100% {{ opacity: 0; }} }}
.star {{ position: absolute; background: white; border-radius: 50%; box-shadow: 0 0 6px 1px rgba(255,255,255,0.8); animation-name: starTwinkle; animation-duration: 40s; animation-iteration-count: infinite; }}
@keyframes starTwinkle {{ 0% {{ opacity: 0; }} 30% {{ opacity: 0; }} 50% {{ opacity: 1; }} 75% {{ opacity: 0.5; }} 100% {{ opacity: 0; }} }}
.hills {{ position: fixed; bottom:0; left:0; width:100%; height:120px; background: linear-gradient(180deg, var(--ground1), var(--ground2)); border-radius: 50% 50% 0 0 / 100% 100% 0 0; z-index: 0; transition: background 1.5s ease; }}
.particle {{ position: absolute; animation-timing-function: linear; animation-iteration-count: infinite; }}
@keyframes rainFall {{ 0% {{ transform: translateY(0) rotate(15deg); opacity: 0.8; }} 100% {{ transform: translateY(110vh) translateX(40px) rotate(15deg); opacity: 0.3; }} }}
@keyframes snowDrift {{ 0% {{ transform: translateY(0) translateX(0) rotate(0deg); opacity: 0.9; }} 50% {{ transform: translateY(55vh) translateX(var(--drift)) rotate(180deg); opacity: 0.7; }} 100% {{ transform: translateY(110vh) translateX(0) rotate(360deg); opacity: 0.2; }} }}
@keyframes leafSwirl {{ 0% {{ transform: translateY(0) translateX(0) rotate(0deg); opacity: 0.9; }} 50% {{ transform: translateY(55vh) translateX(var(--drift)) rotate(200deg); opacity: 0.8; }} 100% {{ transform: translateY(110vh) translateX(-20px) rotate(400deg); opacity: 0.2; }} }}
@keyframes sunSparkle {{ 0%, 100% {{ opacity: 0.2; transform: scale(0.8); }} 50% {{ opacity: 1; transform: scale(1.2); }} }}
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

tab1, tab2, tab3 = st.tabs(["Plant advisor", "Saved Plots", "Log history"])

with tab1:
    with st.form("plot_form"):
        crop = st.selectbox("Crop", SUPPORTED_CROPS)
        location_name = st.text_input("Location name", placeholder="e.g Nsukka")
        col3, col4 = st.columns(2)
        with col3:
            latitude = st.text_input("Latitude", placeholder="6.86")
        with col4:
            longtitude = st.text_input("Longtitude", placeholder="7.40")
        date = st.date_input("Planning date")

        submitted = st.form_submit_button("Get Planting advice")

    if submitted:
        try:
            clean_location = validate_location_name(location_name)
            clean_lat = validate_coordinate(latitude, "latitude")
            clean_lon = validate_coordinate(longtitude, "longitude")
            clean_date = validate_date(str(date))

            conditions = weather_service.get_conditions(clean_lat, clean_lon)

            plot = FarmPlot(
                crop=crop,
                location_name=clean_location,
                latitude=clean_lat,
                longitude=clean_lon,
            )
            storage.save_plot(plot)
            log = LogEntry(
                plot_id=plot.plot_id,
                date=clean_date,
                crop=crop,
                location_name=clean_location,
                temperature_Celsius=conditions["temperature_Celsius"],
                humidity_pct=conditions["humidity_pct"],
                advice_summary="AI advice not available yet.",
            )
            storage.append_log(log)
            st.session_state.last_success = (
                f"[{datetime.now().strftime('%H:%M:%S')}] Saved {crop} at {clean_location}. "
                f"Current temp: {conditions['temperature_Celsius']}°C"
            )
            st.rerun()

        except ValidationError as e:
            st.error(f"Invalid input: {e}")
        except WeatherServiceError as e:
            st.error(f"Weather error: {e}")
        except StorageError as e:
            st.error(f"Storage error: {e}")

    if "last_success" in st.session_state:
        st.success(st.session_state.last_success)

    st.divider()

with tab2:
    st.subheader("Saved Plots")
    for p in saved_plots:
        col_a, col_b = st.columns([4, 1])
        with col_a:
            st.write(f"{p['crop']} -- {p['location_name']}")
        with col_b:
            if st.button("Delete", key=f"del_{p['plot_id']}"):
                try:
                    storage.delete_plot(p['plot_id'])
                    st.rerun()
                except StorageError as error:
                    st.error(f"Couldn't delete: {error}")

    st.divider()

with tab3:
    st.subheader("Log history")

    if st.button("Clear all logs"):
        try:
            storage.clear_logs()
            st.rerun()
        except StorageError as e:
            st.error(f"Couldn't clear logs: {e}")

    for log in saved_logs:
        st.write(f"{log['date']} — {log['crop']} at {log['location_name']} ({log['temperature_Celsius']}°C, {log['humidity_pct']}% humidity)")