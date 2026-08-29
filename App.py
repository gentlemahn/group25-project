import streamlit as st
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

st.markdown("""
<style>
@keyframes oceanShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

.stApp {
    background: linear-gradient(-45deg, #0A2540, #0B5394, #1CA9C9, #073B4C);
    background-size: 400% 400%;
    animation: oceanShift 15s ease infinite;
}

h1 {
    background: linear-gradient(90deg, #00E5FF, #00B4D8, #90E0EF);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    animation: oceanShift 6s ease infinite;
    background-size: 200% 200%;
}

p, label, .stMarkdown, span {
    color: #E0FBFC !important;
}

div[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.08);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(0, 229, 255, 0.3);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 0 20px rgba(0, 229, 255, 0.15);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-4px);
    box-shadow: 0 0 30px rgba(0, 229, 255, 0.35);
}

div[data-testid="stForm"] {
    background: rgba(255, 255, 255, 0.06);
    backdrop-filter: blur(14px);
    border-radius: 20px;
    padding: 28px;
    border: 1px solid rgba(144, 224, 239, 0.25);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.stButton > button {
    background: linear-gradient(90deg, #00B4D8, #0077B6);
    color: white;
    border-radius: 30px;
    border: none;
    padding: 12px 32px;
    font-weight: 700;
    letter-spacing: 0.5px;
    box-shadow: 0 0 15px rgba(0, 180, 216, 0.5);
    transition: all 0.3s ease;
}
.stButton > button:hover {
    background: linear-gradient(90deg, #0077B6, #023E8A);
    box-shadow: 0 0 25px rgba(0, 180, 216, 0.8);
    transform: scale(1.03);
}

input, textarea, select, div[data-baseweb="select"] > div {
    background: rgba(255, 255, 255, 0.1) !important;
    border-radius: 10px !important;
    border: 1px solid rgba(144, 224, 239, 0.3) !important;
    color: white !important;
}

section[data-testid="stSidebar"] {
    background: rgba(7, 59, 76, 0.95);
    backdrop-filter: blur(10px);
}
@keyframes floatUp {
    0% { transform: translateY(0) translateX(0); opacity: 0; }
    10% { opacity: 0.8; }
    90% { opacity: 0.8; }
    100% { transform: translateY(-120px) translateX(20px); opacity: 0; }
}

.bubble-container {
    position: relative;
    height: 60px;
    width: 100%;
    overflow: hidden;
    margin-bottom: 10px;
}

.bubble {
    position: absolute;
    bottom: 0;
    background: rgba(0, 229, 255, 0.35);
    border-radius: 50%;
    animation: floatUp linear infinite;
}
</style>
""", unsafe_allow_html=True)
st.markdown("""
<div class="bubble-container">
    <div class="bubble" style="left:5%; width:14px; height:14px; animation-duration:4s;"></div>
    <div class="bubble" style="left:20%; width:8px; height:8px; animation-duration:3s; animation-delay:0.5s;"></div>
    <div class="bubble" style="left:35%; width:18px; height:18px; animation-duration:5s; animation-delay:1s;"></div>
    <div class="bubble" style="left:50%; width:10px; height:10px; animation-duration:3.5s; animation-delay:1.5s;"></div>
    <div class="bubble" style="left:65%; width:16px; height:16px; animation-duration:4.5s; animation-delay:0.8s;"></div>
    <div class="bubble" style="left:80%; width:12px; height:12px; animation-duration:3.8s; animation-delay:2s;"></div>
    <div class="bubble" style="left:92%; width:9px; height:9px; animation-duration:4.2s; animation-delay:1.2s;"></div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("About")
    st.write("Get AI-powered planting advice based on real waether data.")

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