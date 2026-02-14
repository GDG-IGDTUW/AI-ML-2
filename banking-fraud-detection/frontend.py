import streamlit as st
import pandas as pd
import json
import os
import datetime
import folium
from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh

# Config
st.set_page_config(page_title="BAIDS Dashboard", layout="wide")

LOG_DIR = "forensics_logs"
os.makedirs(LOG_DIR, exist_ok=True)
today_log = os.path.join(LOG_DIR, f"{datetime.date.today()}.jsonl")


# ------------------------------
# Helper: Load JSONL logs
# ------------------------------
def load_logs(file_path):
    if not os.path.exists(file_path):
        return pd.DataFrame()
    rows = []
    with open(file_path, "r") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                row = {
                    "ts": pd.to_datetime(entry.get("ts")),
                    "email": entry.get("event", {}).get("email"),
                    "ip": entry.get("event", {}).get("ip"),
                    "location": entry.get("event", {}).get("location"),
                    "device_id": entry.get("event", {}).get("device_id"),
                    "verdict": entry.get("result", {}).get("verdict"),
                    "risk_score": entry.get("result", {}).get("final_risk_score"),
                    "explanations": entry.get("result", {}).get("explanations"),
                }
                rows.append(row)
            except Exception:
                continue
    return pd.DataFrame(rows)


# ------------------------------
# Sidebar
# ------------------------------
st.sidebar.title("⚙️ Controls")

uploaded = st.sidebar.file_uploader("Upload a log file (.jsonl)", type=["jsonl"])
if uploaded:
    tmp_path = os.path.join(LOG_DIR, "uploaded.jsonl")
    with open(tmp_path, "wb") as f:
        f.write(uploaded.read())
    log_path = tmp_path
else:
    log_path = today_log

df = load_logs(log_path)

# Filters
verdict_filter = st.sidebar.multiselect(
    "Filter by Verdict", options=["legit", "suspicious", "fraud"], default=[]
)
date_filter = st.sidebar.date_input("Filter by Date", [])
profile_filter = st.sidebar.text_input("Filter by Profile", "")

# Apply filters
if not df.empty:
    if verdict_filter:
        df = df[df["verdict"].isin(verdict_filter)]
    if date_filter:
        df = df[df["ts"].dt.date.isin(date_filter)]
    if profile_filter:
        df = df[df["email"].str.contains(profile_filter, case=False, na=False)]
# ------------------------------
# Sidebar
# ------------------------------
st.sidebar.title("⚙️ Controls")

if uploaded:
    tmp_path = os.path.join(LOG_DIR, "uploaded.jsonl")
    with open(tmp_path, "wb") as f:
        f.write(uploaded.read())
    log_path = tmp_path
else:
    log_path = today_log

# ✅ Add Clear Logs Button
if st.sidebar.button("🗑️ Clear Previous Logs"):
    if os.path.exists(log_path):
        os.remove(log_path)
        st.sidebar.success("Logs cleared!")
    else:
        st.sidebar.info("No log file to clear.")
    # Force a reload by stopping here
    st.stop()

df = load_logs(log_path)



# ------------------------------
# Tabs
# ------------------------------
tabs = st.tabs(["📊 Summary", "🕒 Timeline", "📈 Analytics", "📊 Feature Distribution", "📜 Raw Logs"])

# ------------------------------
# Summary Tab (auto-refresh)
# ------------------------------
with tabs[0]:
    st_autorefresh(interval=5000, key="summary_refresh")
    st.subheader("📊 Forensic Summary")

    if not df.empty:
        legit_count = (df["verdict"] == "legit").sum()
        suspicious_count = (df["verdict"] == "suspicious").sum()
        fraud_count = (df["verdict"] == "fraud").sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("✅ Legitimate", legit_count)
        col2.metric("⚠️ Suspicious", suspicious_count)
        col3.metric("🚨 Fraudulent", fraud_count)

        st.markdown("### 📈 Events Over Time")
        chart_data = df.groupby([df["ts"].dt.floor("min"), "verdict"]).size().unstack(fill_value=0)
        st.line_chart(chart_data)
    else:
        st.info("No events to display yet.")


# ------------------------------
# Timeline Tab (with Folium map)
# ------------------------------
with tabs[1]:
    st_autorefresh(interval=5000, key="timeline_refresh")
    st.subheader("🕒 Timeline of Events")

    if not df.empty:
        # Event feed
        for _, row in df.sort_values("ts", ascending=False).iterrows():
            st.markdown(
                f"**{row['ts']}** — {row['email']} ({row['ip']}) → **{row['verdict'].upper()}** "
                f"<br/>Reason: {', '.join(row['explanations']) if row['explanations'] else 'N/A'}",
                unsafe_allow_html=True,
            )

        # Fraud hotspot map
        st.markdown("### 🌍 Fraud Hotspot Map")
        fmap = folium.Map(location=[20, 0], zoom_start=2)
        for _, row in df.iterrows():
            if row["location"]:
                # crude lat/long mock (you may plug a real geocoder here)
                if "Delhi" in row["location"]:
                    coords = [28.7041, 77.1025]
                elif "Moscow" in row["location"]:
                    coords = [55.7558, 37.6173]
                elif "Lagos" in row["location"]:
                    coords = [6.5244, 3.3792]
                elif "Sao Paulo" in row["location"]:
                    coords = [-23.5505, -46.6333]
                elif "Beijing" in row["location"]:
                    coords = [39.9042, 116.4074]
                else:
                    coords = [20, 0]
                folium.Marker(coords, popup=f"{row['email']} → {row['verdict']}").add_to(fmap)
        st_folium(fmap, width=700, height=500)
    else:
        st.info("No timeline events available.")


# ------------------------------
# Analytics Tab
# ------------------------------
with tabs[2]:
    st.subheader("📈 Analytics")

    if not df.empty:
        avg_score = df["risk_score"].mean()
        max_score = df["risk_score"].max()
        min_score = df["risk_score"].min()

        st.metric("Average Risk Score", round(avg_score, 2))
        st.metric("Max Risk Score", round(max_score, 2))
        st.metric("Min Risk Score", round(min_score, 2))

        st.markdown("### Risk Score Distribution")
        st.bar_chart(df["risk_score"])
    else:
        st.info("No analytics available yet.")

# ------------------------------
# Feature Distribution Tab
# ------------------------------
with tabs[3]:
    st.subheader("📊 Feature Distribution")
    
    if not df.empty:
        import plotly.express as px
        
        st.markdown("### Risk Score Distribution")
        fig = px.histogram(df, x="risk_score", nbins=30, title="Risk Score Distribution")
        st.plotly_chart(fig)
        
        st.markdown("### Box Plot - Outlier Detection")
        fig2 = px.box(df, y="risk_score", title="Risk Score Outliers")
        st.plotly_chart(fig2)
        st.markdown("### Statistics")
        st.write(df["risk_score"].describe())
        
        st.markdown("### Verdict Distribution")
        fig3 = px.pie(df, names="verdict", title="Verdict Breakdown")
        st.plotly_chart(fig3)
    else:
        st.info("No data to visualize.")

# ------------------------------
# Raw Logs Tab
# ------------------------------
with tabs[4]:
    st.subheader("📜 Raw Log Data")
    if not df.empty:
        st.dataframe(df)
    else:
        st.info("No logs loaded.")

