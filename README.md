# 🚕 COMP 3610 Assignment 1  
## NYC Yellow Taxi Trip Dashboard (January 2024)

This project analyzes NYC Yellow Taxi trip data for January 2024 using:

- Polars / Pandas (data cleaning & feature engineering)
- DuckDB (SQL analysis)
- Streamlit (interactive dashboard)
- Plotly (visualizations)

---

## Dashboard Overview

The dashboard includes:

- Interactive filters (date range, hour range, payment type)
- Key performance metrics
- 5 required visualizations:
  - Top 10 pickup zones
  - Average fare by hour
  - Trip distance distribution
  - Payment type breakdown
  - Day-of-week vs hour heatmap

The application uses caching and pre-aggregations for performance on ~3M rows.

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/182bry/COMP3610-A1.git
cd COMP3610_A1
```
### 2. Create a virtual environment

```python -m venv venv
venv\Scripts\activate
```
### 3. Install dependencies

```pip install -r requirements.txt```

### 4. Run the dashboard 

```streamlit run app.py```

### Deployed Dashboard URL: 
https://comp3610-a1-lmyotw2rogcwuxxpmlixme.streamlit.app/ 
