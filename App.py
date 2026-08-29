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