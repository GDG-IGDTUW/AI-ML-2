import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import time
import random
import requests
import threading
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pathlib import Path
from streamlit_autorefresh import st_autorefresh


from streamlit_folium import st_folium
import folium

# ------------- App Config -------------
st.set_page_config(page_title="BAIDS Dashboard", layout="wide")

# ------------- Globals / State -------------
LOG_DIR = "forensics_logs"
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

if "sim_thread" not in st.session_state:
    st.session_state.sim_thread = None
if "sim_running" not in st.session_state:
    st.session_state.sim_running = False
if "current_profile" not in st.session_state:
    st.session_state.current_profile = "Default"

API_BASE = "http://127.0.0.1:5000"

# ------------- Profiles -------------
def load_profiles() -> Dict[str, Dict[str, Any]]:
    # Prefer profiles/risk_profiles.json; fallback to risk_profiles.json in root
    search_paths = ["profiles/risk_profiles.json", "risk_profiles.json"]
    for p in search_paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    # sensible default if file missing
    return {
        "Default": {
            "ae_threshold_pct": 70,
            "if_contamination": 0.25,
            "hybrid_threshold": 0.6,
            "rule_weight": 0.2,
            "fp_cost": 1.0,
            "fn_cost": 5.0,
        }
    }

PROFILES = load_profiles()
PROFILE_NAMES = list(PROFILES.keys())

# ------------- Helpers -------------
CITY_COORDS = {
    "Delhi, IN": (28.6139, 77.2090),
    "Mumbai, IN": (19.0760, 72.8777),
    "Moscow, RU": (55.7558, 37.6173),
    "Lagos, NG": (6.5244, 3.3792),
    "Sao Paulo, BR": (-23.5558, -46.6396),
    "Beijing, CN": (39.9042, 116.4074),
}

def location_to_latlon(loc: str):
    if not isinstance(loc, str):
        return None
    return CITY_COORDS.get(loc)

def extract_verdict_from_result(result_obj):
    """
    Normalize verdict from API result.
    We accept legacy labels and map to canonical: 'legit' | 'suspicious' | 'fraud'
    """
    v = None
    if isinstance(result_obj, dict):
        v = result_obj.get("verdict")
    elif isinstance(result_obj, str):
        v = result_obj

    if not v:
        return "unknown"

    v_lower = str(v).strip().lower()
    # map a few legacy possibilities
    if "legit" in v_lower or "✅" in v_lower:
        return "legit"
    if "susp" in v_lower or "⚠" in v_lower:
        return "suspicious"
    if "fraud" in v_lower or "🚨" in v_lower:
        return "fraud"
    return v_lower

def load_jsonl(path: str) -> List[Dict[str, Any]]:
    rows = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        pass
    return rows

def get_latest_log_path() -> Optional[str]:
    if not os.path.exists(LOG_DIR):
        return None
    candidates = [os.path.join(LOG_DIR, f) for f in os.listdir(LOG_DIR) if f.endswith(".jsonl")]
    if not candidates:
        return None
    return sorted(candidates, reverse=True)[0]

def load_latest_logs_or_uploaded(uploaded_file) -> pd.DataFrame:
    """
    Priority:
      1) If a file was uploaded in the sidebar, parse it
      2) Else load latest .jsonl from forensics_logs
    Returns empty df if nothing available.
    """
    if uploaded_file is not None:
        try:
            text = uploaded_file.read().decode("utf-8")
            rows = [json.loads(l) for l in text.splitlines() if l.strip()]
            df = pd.DataFrame(rows)
            return df
        except Exception:
            st.sidebar.error("Could not read the uploaded file. Expecting .jsonl lines with {ts, event, result}.")
            return pd.DataFrame()

    latest = get_latest_log_path()
    if not latest:
        return pd.DataFrame()

    rows = load_jsonl(latest)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)

# ------------- Simulator (inline, so judges can run from UI) -------------
def generate_event(event_type="normal", profile_name="Default"):
    base = {
        "email": f"user{random.randint(1,100)}@example.com",
        "ip": f"192.168.{random.randint(0,1)}.{random.randint(1,254)}",
        "device_id": "DEVICE123",
        "imei": "123456789012345",
        "location": random.choice(list(CITY_COORDS.keys())),
        "timestamp": time.time(),
        # include profile hint (API may ignore if not implemented, but harmless)
        "profile": profile_name,
    }
    if event_type == "normal":
        return base
    elif event_type == "suspicious":
        base["device_id"] = f"DEV{random.randint(1000,9999)}"
        return base
    elif event_type == "fraud":
        base["ip"] = f"203.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        base["imei"] = f"{random.randint(100000000000000,999999999999999)}"
        base["location"] = random.choice(["Moscow, RU", "Lagos, NG", "Sao Paulo, BR", "Beijing, CN"])
        return base
    return base

def simulator_loop(mode="demo", profile_name="Default", api_base=API_BASE):
    st.session_state.sim_running = True
    # traffic mix
    if mode == "demo":
        weights, delay = [0.5, 0.3, 0.2], 2.0
    elif mode == "stress":
        weights, delay = [0.3, 0.3, 0.4], 0.7
    elif mode == "burst":
        weights, delay = [0.15, 0.25, 0.60], 0.4
    else:
        weights, delay = [0.5, 0.3, 0.2], 2.0

    # include profile in querystring (API may adopt it)
    predict_url = f"{api_base}/predict?profile={profile_name}"

    while st.session_state.sim_running:
        choice = random.choices(["normal", "suspicious", "fraud"], weights=weights)[0]
        event = generate_event(choice, profile_name=profile_name)
        try:
            requests.post(predict_url, json=event, timeout=3)
        except Exception:
            pass
        time.sleep(delay)

def replay_loop(file_path, profile_name="Default", api_base=API_BASE):
    st.session_state.sim_running = True
    predict_url = f"{api_base}/predict?profile={profile_name}"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not st.session_state.sim_running:
                    break
                try:
                    entry = json.loads(line)
                    event = entry.get("event", {})
                    # add/override profile hint
                    event["profile"] = profile_name
                    requests.post(predict_url, json=event, timeout=3)
                except Exception:
                    pass
                time.sleep(1.0)
    except Exception as e:
        print(f"Replay error: {e}")

# ------------- Sidebar -------------
st.sidebar.title("⚡ BAIDS Dashboard")

# Profile selector
st.sidebar.markdown("### 🧩 Risk Profile")
profile_name = st.sidebar.selectbox("Active Profile", PROFILE_NAMES, index=PROFILE_NAMES.index(st.session_state.current_profile) if st.session_state.current_profile in PROFILE_NAMES else 0)
st.session_state.current_profile = profile_name

prof = PROFILES.get(profile_name, {})
with st.sidebar.expander("Profile Parameters", expanded=False):
    st.write({
        "ae_threshold_pct": prof.get("ae_threshold_pct"),
        "if_contamination": prof.get("if_contamination"),
        "hybrid_threshold": prof.get("hybrid_threshold"),
        "rule_weight": prof.get("rule_weight"),
        "fp_cost": prof.get("fp_cost"),
        "fn_cost": prof.get("fn_cost"),
    })

# Uploader (moved to sidebar)
st.sidebar.markdown("### 📁 Load a Log (optional)")
uploaded_log = st.sidebar.file_uploader("Upload a .jsonl log", type=["jsonl"])

# Filters (optional)
st.sidebar.markdown("### 🔎 Filters (optional)")
verdict_filter = st.sidebar.multiselect(
    "Filter by verdict",
    options=["legit", "suspicious", "fraud"],
    default=[]  # empty means show all
)
email_filter = st.sidebar.text_input("Filter by email (contains)", "")
location_filter = st.sidebar.text_input("Filter by location (exact e.g., 'Delhi, IN')", "")
date_filter = st.sidebar.date_input("Filter by date", [])

# Simulator controls
st.sidebar.markdown("### 🕹️ Simulator Controls")
sim_mode = st.sidebar.selectbox(
    "Mode",
    ["Off", "Demo (Balanced)", "Stress (High Fraud)", "Burst (Fraud Spikes)", "Replay (from log)"],
    index=0
)

replay_upload = None
if sim_mode == "Replay (from log)":
    replay_upload = st.sidebar.file_uploader("Choose a .jsonl to replay", type=["jsonl"], key="replay")

col_a, col_b = st.sidebar.columns(2)
start_button = col_a.button("▶ Start")
stop_button = col_b.button("⏹ Stop")

# Start/Stop simulator threads
if start_button:
    if st.session_state.sim_thread and st.session_state.sim_thread.is_alive():
        st.sidebar.warning("Simulator already running.")
    else:
        mode_key = "off"
        if sim_mode.startswith("Demo"):
            mode_key = "demo"
        elif sim_mode.startswith("Stress"):
            mode_key = "stress"
        elif sim_mode.startswith("Burst"):
            mode_key = "burst"
        elif sim_mode.startswith("Replay"):
            mode_key = "replay"

        if mode_key == "replay":
            if replay_upload is None:
                st.sidebar.error("Please upload a .jsonl file for Replay mode.")
            else:
                tmp_path = f"replay_{int(time.time())}.jsonl"
                with open(tmp_path, "wb") as f:
                    f.write(replay_upload.read())
                st.session_state.sim_thread = threading.Thread(
                    target=replay_loop, args=(tmp_path, profile_name), daemon=True
                )
                st.session_state.sim_thread.start()
                st.session_state.sim_running = True
                st.sidebar.success(f"Replay started with profile: {profile_name}")
        elif mode_key == "off":
            st.sidebar.info("Simulator is Off. Choose a mode first.")
        else:
            st.session_state.sim_thread = threading.Thread(
                target=simulator_loop, args=(mode_key, profile_name), daemon=True
            )
            st.session_state.sim_thread.start()
            st.session_state.sim_running = True
            st.sidebar.success(f"Simulator started in {mode_key.upper()} mode • Profile: {profile_name}")

if stop_button:
    st.session_state.sim_running = False
    st.sidebar.success("Simulator stop signal sent.")

# ------------- Data Load & Filtering -------------
df = load_latest_logs_or_uploaded(uploaded_log)

# Normalize frame
if not df.empty:
    # result/verdict normalization
    df["verdict"] = df["result"].apply(extract_verdict_from_result)
    df["ip"] = df["event"].apply(lambda x: x.get("ip", "Unknown"))
    df["location"] = df["event"].apply(lambda x: x.get("location", "Unknown"))
    df["device_id"] = df["event"].apply(lambda x: x.get("device_id", "Unknown"))
    df["email"] = df["event"].apply(lambda x: x.get("email", "unknown@example.com"))
    df["ts_dt"] = pd.to_datetime(df["ts"], errors="coerce", utc=True)
    df["profile_used"] = df["result"].apply(lambda r: r.get("profile_used") if isinstance(r, dict) else None)
else:
    df = pd.DataFrame(columns=["ts","verdict","ip","location","device_id","email","ts_dt","profile_used"])

# Apply optional filters
df_filtered = df.copy()
if not df_filtered.empty:
    if verdict_filter:
        df_filtered = df_filtered[df_filtered["verdict"].isin(verdict_filter)]
    if email_filter.strip():
        df_filtered = df_filtered[df_filtered["email"].str.contains(email_filter.strip(), case=False, na=False)]
    if location_filter.strip():
        df_filtered = df_filtered[df_filtered["location"] == location_filter.strip()]
    if isinstance(date_filter, list) and len(date_filter) > 0:
        # Support multi-date selection
        dates = [pd.Timestamp(d).date() for d in (date_filter if isinstance(date_filter, list) else [date_filter])]
        df_filtered = df_filtered[df_filtered["ts_dt"].dt.date.isin(dates)]

# ------------- Live Mode Banner -------------
mode_indicator = "Idle"
banner_color = "gray"
last_event_time = "No events yet"
if not df.empty:
    last_n = df.tail(30)
    fraud_rate = (last_n["verdict"] == "fraud").mean()
    sus_rate = (last_n["verdict"] == "suspicious").mean()
    if fraud_rate > 0.6:
        mode_indicator = "⚡ Burst Mode (Fraud Spike)"
        banner_color = "red"
    elif (fraud_rate + sus_rate) > 0.6:
        mode_indicator = "🔥 Stress Mode"
        banner_color = "orange"
    else:
        mode_indicator = "🟢 Demo Mode"
        banner_color = "green"
    last_ts = df["ts_dt"].max()
    if pd.notnull(last_ts):
        last_event_time = last_ts.strftime("%Y-%m-%d %H:%M:%S UTC")

st.markdown(
    f"""
    <div style='background-color:{banner_color};padding:10px;border-radius:10px;margin-bottom:15px;'>
        <h3 style='color:white;text-align:center;margin:0;'>{mode_indicator}</h3>
        <p style='color:white;text-align:center;margin:0;font-size:14px;'>
            ⏱️ Last Event Received: {last_event_time} &nbsp;•&nbsp; 🧩 Active Profile: <b>{profile_name}</b>
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# ------------- Tabs -------------
tab1, tab2, tab3, tab4 ,tab5 = st.tabs(["📜 Timeline", "📊 Summary", "📈 Analytics", "📜 Raw Logs","🌐 OSINT enrichment"])

# ====== TIMELINE ======
with tab1:
    
    # auto-refresh timeline every 5s
    
    st.subheader("📜 Timeline View")

    if df_filtered.empty:
        st.info("No events found. Start the simulator or clear filters.")
    else:
        # compact table of latest 100
        show_cols = ["ts", "verdict", "email", "ip", "location", "device_id"]
        st.dataframe(df_filtered.sort_values("ts_dt", ascending=False).head(100)[show_cols], use_container_width=True)

        # Map
        st.markdown("#### 🌍 Map of Login Attempts")
        points = []
        for _, row in df_filtered.iterrows():
            ll = location_to_latlon(row["location"])
            if ll:
                label = f"{row['verdict'].upper()} • {row['email']} • {row['ip']} • {row['device_id']}"
                points.append((ll[0], ll[1], row["verdict"], label))

        if points:
            lat_mean = sum(p[0] for p in points) / len(points)
            lon_mean = sum(p[1] for p in points) / len(points)
            fmap = folium.Map(location=[lat_mean, lon_mean], zoom_start=2)
            color_map = {"legit": "green", "suspicious": "orange", "fraud": "red"}
            for lat, lon, v, label in points:
                folium.CircleMarker(
                    location=(lat, lon),
                    radius=6,
                    color=color_map.get(v, "blue"),
                    fill=True,
                    fill_opacity=0.85,
                    popup=label
                ).add_to(fmap)

            # Legend
            legend_html = """
            <div style="position: fixed; bottom: 30px; left: 30px; z-index: 9999;
                        background: white; padding: 8px 10px; border: 1px solid #ccc; border-radius: 6px;">
              <b>Legend</b><br>
              <span style="color:green;">●</span> Legit &nbsp;&nbsp;
              <span style="color:orange;">●</span> Suspicious &nbsp;&nbsp;
              <span style="color:red;">●</span> Fraudulent
            </div>
            """
            fmap.get_root().html.add_child(folium.Element(legend_html))

            st_folium(fmap, use_container_width=True, returned_objects=[])
        else:
            st.info("No mappable locations yet (extend CITY_COORDS or generate events with known cities).")

# ====== SUMMARY ======
with tab2:
    
    
    st.subheader("📊 Summary Dashboard")

    if df_filtered.empty:
        st.info("No events to summarize. Start simulator or clear filters.")
    else:
        # KPI metrics
        legit_count = (df_filtered["verdict"] == "legit").sum()
        suspicious_count = (df_filtered["verdict"] == "suspicious").sum()
        fraud_count = (df_filtered["verdict"] == "fraud").sum()
        total_count = len(df_filtered)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("✅ Legit", int(legit_count))
        c2.metric("⚠️ Suspicious", int(suspicious_count))
        c3.metric("🚨 Fraudulent", int(fraud_count))
        c4.metric("📊 Total", int(total_count))

        st.markdown("---")

        # Verdict distribution (donut)
        verdict_counts = df_filtered["verdict"].value_counts()
        fig = px.pie(
            values=verdict_counts.values,
            names=verdict_counts.index,
            hole=0.4,
            color=verdict_counts.index,
            color_discrete_map={"legit": "green", "suspicious": "orange", "fraud": "red"},
            title="Verdict Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # Events over time by verdict
        df_plot = df_filtered.dropna(subset=["ts_dt"]).copy()
        if not df_plot.empty:
            timeline_counts = (
                df_plot
                .groupby([pd.Grouper(key="ts_dt", freq="1min"), "verdict"])
                .size()
                .reset_index(name="count")
            )
            fig2 = px.line(
                timeline_counts,
                x="ts_dt",
                y="count",
                color="verdict",
                markers=True,
                color_discrete_map={"legit": "green", "suspicious": "orange", "fraud": "red"},
                title="Events Over Time"
            )
            fig2.update_layout(xaxis_title="Time", yaxis_title="Event Count")
            st.plotly_chart(fig2, use_container_width=True)

        # Recent cards
        st.markdown("---")
        st.markdown("#### 📝 Recent Events")
        for _, row in df_filtered.sort_values("ts_dt").tail(5).iterrows():
            verdict = row["verdict"]
            color = {"legit": "green", "suspicious": "orange", "fraud": "red"}.get(verdict, "#444")
            html = f"""
            <div style="border-left: 6px solid {color}; padding: 8px; margin-bottom: 6px; border-radius: 6px; background:#f9f9f9;">
              <b>{verdict.upper()}</b> login attempt from <b>{row['location']}</b><br>
              <small>User: {row['email']} &nbsp;|&nbsp; IP: {row['ip']} &nbsp;|&nbsp; Device: {row['device_id']}</small><br>
              <i>Timestamp: {row.get('ts','')}</i>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)

# ====== ANALYTICS ======
# ====== BREAKDOWN ======
with tab3:
    st.markdown("### 🕵️ Breakdown Analysis")

    if df_filtered.empty:
        st.info("No events to analyze. Start simulator or clear filters.")
    else:
        # --- FRAUDULENT SECTION ---
        st.markdown("## 🚨 Fraudulent Patterns")
        fraud_df = df_filtered[df_filtered["verdict"] == "fraud"]

        # Fraud by Location
        loc_counts = fraud_df["location"].value_counts().reset_index()
        loc_counts.columns = ["location", "fraud_count"]
        if not loc_counts.empty:
            st.markdown("#### 🌍 Fraud Attempts by Location")
            fig_loc = px.bar(loc_counts, x="location", y="fraud_count", color="fraud_count",
                             color_continuous_scale="Reds")
            st.plotly_chart(fig_loc, use_container_width=True)
        else:
            st.info("No fraudulent attempts by location yet.")

        # Fraud by IP
        ip_counts = fraud_df["ip"].value_counts().head(10).reset_index()
        ip_counts.columns = ["ip", "fraud_count"]
        if not ip_counts.empty:
            st.markdown("#### 🌐 Top Fraudulent IPs")
            fig_ip = px.bar(ip_counts, x="ip", y="fraud_count", color="fraud_count",
                            color_continuous_scale="Reds")
            st.plotly_chart(fig_ip, use_container_width=True)
        else:
            st.info("No fraudulent IPs yet.")

        # Fraud by Device
        dev_counts = fraud_df["device_id"].value_counts().head(10).reset_index()
        dev_counts.columns = ["device_id", "fraud_count"]
        if not dev_counts.empty:
            st.markdown("#### 📱 Fraudulent Device IDs")
            fig_dev = px.bar(dev_counts, x="device_id", y="fraud_count", color="fraud_count",
                             color_continuous_scale="Reds")
            st.plotly_chart(fig_dev, use_container_width=True)
        else:
            st.info("No fraudulent devices yet.")

        st.markdown("---")

        # --- SUSPICIOUS SECTION ---
        st.markdown("## ⚠️ Suspicious Patterns")
        susp_df = df_filtered[df_filtered["verdict"] == "suspicious"]

        # Suspicious by Location
        loc_counts_s = susp_df["location"].value_counts().reset_index()
        loc_counts_s.columns = ["location", "suspicious_count"]
        if not loc_counts_s.empty:
            st.markdown("#### 🌍 Suspicious Attempts by Location")
            fig_loc_s = px.bar(loc_counts_s, x="location", y="suspicious_count", color="suspicious_count",
                               color_continuous_scale="Oranges")
            st.plotly_chart(fig_loc_s, use_container_width=True)
        else:
            st.info("No suspicious attempts by location yet.")

        # Suspicious by IP
        ip_counts_s = susp_df["ip"].value_counts().head(10).reset_index()
        ip_counts_s.columns = ["ip", "suspicious_count"]
        if not ip_counts_s.empty:
            st.markdown("#### 🌐 Top Suspicious IPs")
            fig_ip_s = px.bar(ip_counts_s, x="ip", y="suspicious_count", color="suspicious_count",
                              color_continuous_scale="Oranges")
            st.plotly_chart(fig_ip_s, use_container_width=True)
        else:
            st.info("No suspicious IPs yet.")

        # Suspicious by Device
        dev_counts_s = susp_df["device_id"].value_counts().head(10).reset_index()
        dev_counts_s.columns = ["device_id", "suspicious_count"]
        if not dev_counts_s.empty:
            st.markdown("#### 📱 Suspicious Device IDs")
            fig_dev_s = px.bar(dev_counts_s, x="device_id", y="suspicious_count", color="suspicious_count",
                               color_continuous_scale="Oranges")
            st.plotly_chart(fig_dev_s, use_container_width=True)
        else:
            st.info("No suspicious devices yet.")


# ====== RAW LOGS ======
with tab4:
    st.subheader("📜 Raw Logs")

    if df_filtered.empty:
        st.info("No logs to display. Start simulator or clear filters.")
    else:
        st.dataframe(df_filtered.sort_values("ts_dt", ascending=False), use_container_width=True)

    # Download button
    if not df_filtered.empty:
        csv_data = df_filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Filtered Logs as CSV",
            data=csv_data,
            file_name=f"filtered_logs_{date.today().isoformat()}.csv",
            mime="text/csv"
        ) 
# ====== OSINT ENRICHMENT ======  
with tab5:
    st.subheader("🌐 OSINT Enrichment (demo)")
    if not df.empty:
        sample_ips=df["ip"].dropna().unique()[:5]
        data=[{"ip":ip,"asn":"AS"+str(random.randint(1000,9999)),"vpn":random.choice(["Yes","No"]),"leaked":random.choice(["Yes","No"])} for ip in sample_ips]
        st.table(pd.DataFrame(data))



st.caption("BAIDS • Hybrid Risk Analytics • Streamlit Demo")
