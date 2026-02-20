"""
COMP 3610 Assignment 1 - Dashboard Page (Required Visualizations)
"""

import traceback
import streamlit as st
import pandas as pd
import plotly.express as px
import os 
import requests

st.set_page_config(
    page_title="Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

PAYMENT_MAP = {
    0: "Flex Fare",
    1: "Credit Card",
    2: "Cash",
    3: "No Charge",
    4: "Dispute",
    5: "Unknown",
    6: "Voided Trip"
}

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

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

@st.cache_data(show_spinner="Loading & preparing dataset...")
def load_data():
    # Ensure raw files exist in Streamlit Cloud container
    download_file(TRIPS_URL, RAW_TRIPS_PATH)
    download_file(ZONES_URL, RAW_ZONES_PATH)

    zones = pd.read_csv(RAW_ZONES_PATH)[["LocationID", "Borough", "Zone"]]

    # If cleaned parquet exists, use it (fast)
    if os.path.exists(CLEAN_PATH):
        df = pd.read_parquet(CLEAN_PATH)
    else:
        # Build cleaned parquet once
        df = pd.read_parquet(RAW_TRIPS_PATH)

        # Datetime + Jan 2024 filter
        df["tpep_pickup_datetime"] = pd.to_datetime(df["tpep_pickup_datetime"])
        df["tpep_dropoff_datetime"] = pd.to_datetime(df["tpep_dropoff_datetime"])
        df = df[(df["tpep_pickup_datetime"] >= "2024-01-01") & (df["tpep_pickup_datetime"] < "2024-02-01")]

        # Cleaning 
        critical_cols = ["tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID", "DOLocationID", "fare_amount"]
        df = df.dropna(subset=critical_cols)

        df = df[df["trip_distance"] > 0]
        df = df[(df["fare_amount"] >= 0) & (df["fare_amount"] <= 500)]
        df = df[df["tpep_dropoff_datetime"] >= df["tpep_pickup_datetime"]]
        df = df[df["passenger_count"] > 0]
        df = df[df["trip_distance"] < 50]

        # Feature engineering (exact 4 columns)
        df["trip_duration_minutes"] = (df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"]).dt.total_seconds() / 60
        hours = df["trip_duration_minutes"] / 60
        df["trip_speed_mph"] = (df["trip_distance"] / hours).replace([float("inf"), -float("inf")], 0).fillna(0)
        df["pickup_hour"] = df["tpep_pickup_datetime"].dt.hour
        df["pickup_day_of_week"] = df["tpep_pickup_datetime"].dt.day_name()

        os.makedirs(PROCESSED_DIR, exist_ok=True)
        df.to_parquet(CLEAN_PATH, index=False)

    # Make sure pickup datetime exists as datetime for downstream
    df["tpep_pickup_datetime"] = pd.to_datetime(df["tpep_pickup_datetime"])

    # Fields for filtering + labels
    df["pickup_date"] = df["tpep_pickup_datetime"].dt.date
    df["payment_name"] = df["payment_type"].map(PAYMENT_MAP).fillna("Other")

    # Join pickup zone names
    zones_pickup = zones.rename(columns={"Zone": "pickup_zone", "Borough": "pickup_borough"})
    df = df.merge(zones_pickup, left_on="PULocationID", right_on="LocationID", how="left")

    # Ensure weekday ordering
    df["pickup_day_of_week"] = pd.Categorical(df["pickup_day_of_week"], categories=DAY_ORDER, ordered=True)

    return df

# ---- Cached aggregations (optional but good for performance) ----
@st.cache_data
def agg_top10_zones(df_in):
    return (
        df_in.groupby(["pickup_zone", "pickup_borough"])
        .size()
        .reset_index(name="trip_count")
        .sort_values("trip_count", ascending=False)
        .head(10)
    )

@st.cache_data
def agg_hourly_fare(df_in):
    return (
        df_in.groupby("pickup_hour")["fare_amount"]
        .mean()
        .reset_index()
        .sort_values("pickup_hour")
    )

@st.cache_data
def agg_payment(df_in):
    out = df_in["payment_name"].value_counts().reset_index()
    out.columns = ["payment_name", "trip_count"]
    return out

@st.cache_data
def agg_heatmap(df_in):
    heat = (
        df_in.groupby(["pickup_day_of_week", "pickup_hour"], observed=False)
        .size()
        .reset_index(name="trips")
    )
    return heat.pivot(index="pickup_day_of_week", columns="pickup_hour", values="trips").fillna(0)

df = load_data()

st.title("📊 Dashboard")
st.caption("Use the sidebar filters. All charts update instantly.")

st.divider()

# ---------- Sidebar Filters (Req 10) ----------
st.sidebar.header("Filters")

min_date = df["pickup_date"].min()
max_date = df["pickup_date"].max()

date_range = st.sidebar.date_input(
    "Pickup date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range

hour_min, hour_max = st.sidebar.slider("Pickup hour range (0–23)", 0, 23, (0, 23))

payment_options = sorted(df["payment_name"].dropna().unique().tolist())
selected_payments = st.sidebar.multiselect(
    "Payment types",
    options=payment_options,
    default=payment_options
)

filtered = df[
    (df["pickup_date"] >= start_date) &
    (df["pickup_date"] <= end_date) &
    (df["pickup_hour"] >= hour_min) &
    (df["pickup_hour"] <= hour_max) &
    (df["payment_name"].isin(selected_payments))
].copy()

st.sidebar.divider()
st.sidebar.metric("Trips after filters", f"{len(filtered):,}")

if len(filtered) == 0:
    st.warning("No trips match your filters. Try widening date/hour/payment selections.")
    st.stop()

# ---------- Key Metrics (Req 8) ----------
st.subheader("Key Metrics")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Trips", f"{len(filtered):,}")
with col2:
    st.metric("Average Fare", f"${filtered['fare_amount'].mean():.2f}")
with col3:
    st.metric("Total Revenue", f"${filtered['total_amount'].sum():,.0f}")
with col4:
    st.metric("Avg Distance", f"{filtered['trip_distance'].mean():.2f} mi")
with col5:
    st.metric("Avg Duration", f"{filtered['trip_duration_minutes'].mean():.1f} min")

st.divider()

# Pre-aggregations (performance)
top10 = agg_top10_zones(filtered)
hourly_fare = agg_hourly_fare(filtered)
pay = agg_payment(filtered)
pivot = agg_heatmap(filtered)

# --- Persisted "tabs" (fixes: filters resetting to Zones) ---
section = st.radio(
    "View",
    ["Zones", "Time Patterns", "Distance & Payments"],
    horizontal=True,
    key="active_section"
)

st.divider()

# -------------------------
# ZONES (r)
# -------------------------
if section == "Zones":
    st.subheader(" Top 10 Pickup Zones by Trip Count")
    fig_r = px.bar(
        top10,
        x="trip_count",
        y="pickup_zone",
        color="pickup_borough",
        orientation="h",
        title="Top 10 Pickup Zones (Filtered)",
        labels={"trip_count": "Trips", "pickup_zone": "Pickup Zone"}
    )
    fig_r.update_layout(height=450)
    st.plotly_chart(fig_r, width="stretch")

    st.markdown(
        "Under the current filters, these zones generate the most pickups, showing where demand concentrates. "
        "Midtown/Upper East Side zones and airports frequently appear as hotspots, reflecting commuter + traveler activity. "
        "If you narrow to late-night hours, you’ll typically see entertainment districts rise."
    )

# -------------------------
# TIME PATTERNS (s + v)
# -------------------------
elif section == "Time Patterns":
    st.subheader(" Average Fare by Hour of Day")
    fig_s = px.line(
        hourly_fare,
        x="pickup_hour",
        y="fare_amount",
        markers=True,
        title="Average Fare by Hour (Filtered)",
        labels={"pickup_hour": "Hour", "fare_amount": "Average Fare ($)"}
    )
    fig_s.update_xaxes(dtick=1)
    fig_s.update_layout(height=450)
    st.plotly_chart(fig_s, width="stretch")

    st.markdown(
        "Average fares dip in the early morning and rise during periods associated with longer rides (often late-night and airport travel). "
        "The flatter midday section suggests more consistent, shorter urban trips. "
        "If your date range includes weekends, the late-evening average typically increases."
    )

    st.divider()

    st.subheader(" Trips by Day of Week and Hour (Heatmap)")
    fig_v = px.imshow(
        pivot,
        aspect="auto",
        title="Trip Volume Heatmap (Filtered)",
        labels={"x": "Hour", "y": "Day of Week", "color": "Trips"}
    )
    fig_v.update_layout(height=520)
    st.plotly_chart(fig_v, width="stretch")

    st.markdown(
        "Weekdays tend to show stronger morning and late-afternoon peaks consistent with commuting. "
        "Weekend demand usually shifts toward later hours, reflecting leisure/nightlife travel. "
        "The heatmap makes it easy to spot repeated peak windows that TLC operations could plan around."
    )

# -------------------------
# DISTANCE & PAYMENTS (t + u)
# -------------------------
else:
    st.subheader(" Distribution of Trip Distances")
    plot_dist = filtered[filtered["trip_distance"].between(0, 30)]

    fig_t = px.histogram(
        plot_dist,
        x="trip_distance",
        nbins=40,
        title="Trip Distance Distribution (0–30 miles, Filtered)",
        labels={"trip_distance": "Trip Distance (miles)"}
    )
    fig_t.update_layout(height=450)
    st.plotly_chart(fig_t, width="stretch")

    st.markdown(
        "Most trips cluster at short distances, showing taxis are mainly used for local travel in NYC. "
        "The long right tail captures less frequent longer rides, including airport and cross-borough trips. "
        "If the peak shifts right after filtering, it suggests your selection includes more long-distance travel."
    )

    st.divider()

    st.subheader(" Breakdown of Payment Types")
    fig_u = px.bar(
        pay,
        x="payment_name",
        y="trip_count",
        title="Payment Type Breakdown (Filtered)",
        labels={"payment_name": "Payment Type", "trip_count": "Trips"}
    )
    fig_u.update_layout(height=450)
    st.plotly_chart(fig_u, width="stretch")

    st.markdown(
        "Credit card trips dominate, while cash remains a meaningful minority. "
        "Payment mix can shift by location and time (airport trips often skew card-heavy). "
        "This matters for tip analysis because card tips are recorded, while cash tips are often missing."
    )