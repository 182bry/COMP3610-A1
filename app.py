"""
COMP 3610 Assignment 1 - Overview Page
=====================================
NYC Yellow Taxi Trip Dashboard (Jan 2024)

Run:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import os
import requests

st.set_page_config(
    page_title="NYC Yellow Taxi Dashboard (A1)",
    page_icon="🚕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Header ---
st.markdown("""
<style>
    .hero {
        padding: 1.25rem 1.25rem 0.75rem 1.25rem;
        border-radius: 18px;
        background: linear-gradient(135deg, rgba(255,107,107,0.18), rgba(30,58,95,0.18));
        border: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 1rem;
    }
    .hero-title {
        font-size: 2.6rem;
        font-weight: 900;
        margin: 0;
        line-height: 1.1;
    }
    .hero-sub {
        font-size: 1.05rem;
        opacity: 0.85;
        margin-top: 0.5rem;
        margin-bottom: 0;
    }
    .small-note {
        font-size: 0.95rem;
        opacity: 0.8;
    }
</style>
""", unsafe_allow_html=True)

# Remote Dataset Configuration (Streamlit Cloud Compatibility)
TRIPS_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet"
ZONES_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"
RAW_TRIPS_PATH = os.path.join(RAW_DIR, "yellow_tripdata_2024-01.parquet")
RAW_ZONES_PATH = os.path.join(RAW_DIR, "taxi_zone_lookup.csv")
CLEAN_PATH = os.path.join(PROCESSED_DIR, "taxi_clean.parquet")

def download_file(url: str, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        return
    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()
    with open(path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)

@st.cache_data(show_spinner="Loading dataset for overview...")
def load_overview_data():
    # Ensure raw files exist in Streamlit Cloud container
    download_file(TRIPS_URL, RAW_TRIPS_PATH)
    download_file(ZONES_URL, RAW_ZONES_PATH)

    # If cleaned parquet exists, use it (fast)
    if os.path.exists(CLEAN_PATH):
        df = pd.read_parquet(CLEAN_PATH)
        df["tpep_pickup_datetime"] = pd.to_datetime(df["tpep_pickup_datetime"])
        df["pickup_date"] = df["tpep_pickup_datetime"].dt.date
        return df

    # Otherwise: build cleaned parquet once
    df = pd.read_parquet(RAW_TRIPS_PATH)

    # Basic cleaning 
    df["tpep_pickup_datetime"] = pd.to_datetime(df["tpep_pickup_datetime"])
    df["tpep_dropoff_datetime"] = pd.to_datetime(df["tpep_dropoff_datetime"])
    df = df[(df["tpep_pickup_datetime"] >= "2024-01-01") & (df["tpep_pickup_datetime"] < "2024-02-01")]

    critical_cols = ["tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID", "DOLocationID", "fare_amount"]
    df = df.dropna(subset=critical_cols)

    df = df[df["trip_distance"] > 0]
    df = df[(df["fare_amount"] >= 0) & (df["fare_amount"] <= 500)]
    df = df[df["tpep_dropoff_datetime"] >= df["tpep_pickup_datetime"]]
    df = df[df["passenger_count"] > 0]
    df = df[df["trip_distance"] < 50]

    # Feature engineering 
    df["trip_duration_minutes"] = (df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"]).dt.total_seconds() / 60
    hours = df["trip_duration_minutes"] / 60
    df["trip_speed_mph"] = (df["trip_distance"] / hours).replace([float("inf"), -float("inf")], 0).fillna(0)
    df["pickup_hour"] = df["tpep_pickup_datetime"].dt.hour
    df["pickup_day_of_week"] = df["tpep_pickup_datetime"].dt.day_name()
    df["pickup_date"] = df["tpep_pickup_datetime"].dt.date

    # Save for re-use
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    df.to_parquet(CLEAN_PATH, index=False)

    return df

df = load_overview_data()

st.markdown("""
<div class="hero">
  <p class="hero-title">🚕 NYC Yellow Taxi Dashboard (Jan 2024)</p>
  <p class="hero-sub">
    Interactive analysis of cleaned taxi trips: demand hotspots, fares, distance patterns,
    payment behavior, and weekly trends.
  </p>
</div>
""", unsafe_allow_html=True)

st.write(
    "Use the **sidebar** to switch between pages. Start here for a quick summary, "
    "then go to **Dashboard** for the required 5 visualizations with filters."
)

st.divider()

# ---- Quick metrics (overview only) ----
st.subheader("Key Metrics at a Glance")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Trips", f"{len(df):,}")
with col2:
    st.metric("Average Fare", f"${df['fare_amount'].mean():.2f}")
with col3:
    st.metric("Total Revenue", f"${df['total_amount'].sum():,.0f}")
with col4:
    st.metric("Avg Distance", f"{df['trip_distance'].mean():.2f} mi")
with col5:
    st.metric("Avg Duration", f"{df['trip_duration_minutes'].mean():.1f} min")

st.divider()

# ---- Coverage / notes ----
st.subheader("Data Coverage")

c1, c2, c3 = st.columns(3)
with c1:
    st.info(f"**Date Range:** {df['pickup_date'].min()} → {df['pickup_date'].max()}")
with c2:
    st.info("**Data Source:** NYC TLC (Yellow Taxi Trip Records)")
with c3:
    st.info("**Rows Loaded:** {:,}".format(len(df)))

st.markdown(
    """
**What’s in the Dashboard page**
- Filters: date range, pickup hour range, payment type multiselect  
- 5 required charts (r–v) with 2–3 sentence insights under each  
- Uses caching to avoid recomputing heavy aggregations repeatedly  
""",
)

st.sidebar.success("Pick a page above to explore!")
st.sidebar.markdown("---")
st.sidebar.markdown("**Dataset:** NYC Yellow Taxi (Jan 2024)")
st.sidebar.markdown(f"**Trips (cleaned):** {len(df):,}")



