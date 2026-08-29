import streamlit as st
import random
from datetime import datetime

dummy_plots = [
        {"crop": "Maize", "location_name": "Nsukka", "logs": 2},
        {"crop": "Cassava", "location_name": "Karu", "logs": 0}
    ]

dummy_logs =[
        {"date": "2026-08-20", "activity": "Weeding", "temp": 27},
        {"date": "2026-08-005", "activity": "Planting", "temp": 25}
    ]

st.set_page_config(page_title="Smaart Farming Advisor", page_icon="🧑‍🌾", layout="wide")
st.title("Smart Farming And Crop Planting Advisor")

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
col1.metric("Total plots", len(dummy_plots))
col2.metric("Total Logs", len(dummy_logs))

tab1 , tab2, tab3, = st.tabs(["Plant advisor", "Saved Plots", "Log history"])


with tab1:
    with st.form("plot_form"):
        crop = st.selectbox("Crop", ["Maize", "Cassava", "Tomato", "Rice"])
        location_name = st.text_input("Location name", placeholder="e.g Nsukka")
        col3, col4 = st.columns(2)
        with col3:
            latitude = st.text_input("Latitude", placeholder="6.86")
        with col4:
            longtitude = st.text_input("Longtitude", placeholder="7.40")
        date = st.date_input("Planning date")

        submitted = st.form_submit_button("Get Planting advice")

    if submitted:
        st.success(f"{crop} at {location_name} on {date}")

st.divider()

with tab2:
    st.subheader("Saved Plots")
    
    for p in dummy_plots:
        st.write(f"{p['crop']}, -- {p['location_name']}  ({p['logs']} logs)")

st.divider()

with tab3:
    st.subheader("Log history")
    
    for log in dummy_logs:
        st.write(f"{log['date']}  --  {log['activity']} ({log['temp']} °C)")