# streamlit_phishing_forensics.py

import streamlit as st
# App config
st.set_page_config(page_title="📱 Forensic Phishing Analyzer", layout="wide")
import pandas as pd
import os, glob, sqlite3, re
import torch
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime
from collections import Counter
from transformers import BertTokenizer, BertForSequenceClassification
from utils import (
    predict, extract_urls, detect_otp, keyword_reason, explain_message,
    render_timeline_card, extract_app_df
)
import datetime



# --- Sidebar Input ---
st.sidebar.header("📩 SMS Data Source")
source = st.sidebar.radio("Select data source:", [ "Extract from Logical Image","Upload CSV"])
DEFAULT_IMAGE_DIR = "android_logical_image_sample"

df, call_df = None, None

if source == "Upload CSV":
    uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
else:
    image_dir = st.sidebar.text_input("Enter local path to logical image folder", value=DEFAULT_IMAGE_DIR)
    df = None
    call_df = None
    app_df = None
    if os.path.isdir(image_dir):
        sms_files = glob.glob(os.path.join(image_dir, "**", "mmssms.db"), recursive=True)
        call_files = glob.glob(os.path.join(image_dir, "**", "calllog.db"), recursive=True)
        usage_db_files = glob.glob(os.path.join(image_dir, "**", "event_logs.db"), recursive=True)

        if sms_files:
            st.sidebar.success(f"Found: {os.path.basename(sms_files[0])}")
            conn = sqlite3.connect(sms_files[0])
            query = "SELECT address as sender, date/1000 as timestamp,body as text FROM sms WHERE text IS NOT NULL"
            df = pd.read_sql_query(query, conn)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        else:
            st.sidebar.error("No mmssms.db found in directory")

        # --- Optional: Parse call logs ---
        if call_files:
            st.sidebar.success(f"Found: {os.path.basename(call_files[0])}")
            call_conn = sqlite3.connect(call_files[0])
            call_df = pd.read_sql_query("""
                SELECT number, date/1000 as timestamp, duration, type
                FROM calls
                WHERE number IS NOT NULL
            """, call_conn)
            call_df['timestamp'] = pd.to_datetime(call_df['timestamp'], unit='s')
            


       
        # Optional: App usage extraction
        if usage_db_files:
            st.sidebar.success(f"Found: {os.path.basename(usage_db_files[0])}")
            app_df = extract_app_df(usage_db_files[0])

# Proceed if df is available
if df is not None:
    df = df.dropna(subset=["text"])
    df["urls"] = df["text"].apply(extract_urls)
    df["otp_flag"] = df["text"].apply(detect_otp)
    df["keyword_reason"] = df["text"].apply(keyword_reason)
    df["explanation"] = df.apply(explain_message, axis=1)
    df["pred_label"], df["confidence"] = predict(df["text"].tolist())
    df["pred_label"] = df["pred_label"].map({0: "Legitimate", 1: "Phishing"})



    # --- Filters ---
    st.sidebar.markdown("## 🔍 Filters")
    only_phishing = st.sidebar.checkbox("🚨 Only Phishing SMS")
    only_otp = st.sidebar.checkbox("🔐 Only OTP-related")
    sender_filter = st.sidebar.text_input("Filter by sender")
    date_range = st.sidebar.date_input(
    "Select date range:",
    [datetime.date.today() - datetime.timedelta(days=7), datetime.date.today()]
)
    
    
    filtered_df = df.copy()
    if only_phishing:
        filtered_df = filtered_df[filtered_df["pred_label"] == "Phishing"]
    if only_otp:
        filtered_df = filtered_df[filtered_df["otp_flag"]]
    if sender_filter:
        filtered_df = filtered_df[filtered_df["sender"].str.contains(sender_filter)]
    if isinstance(date_range, list) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = None  # or set default
    

    # Summary stats
    st.markdown("### 📈 Summary")
    top_senders = filtered_df["sender"].value_counts().head(5)
    st.write("**Top SMS Senders**")
    st.write(top_senders)

    all_urls = sum(filtered_df["urls"].dropna().tolist(), [])
    top_domains = Counter([re.sub(r'^https?://(www\.)?', '', u).split('/')[0] for u in all_urls]).most_common(5)
    st.write("**Top Domains in SMS:**")
    for domain, count in top_domains:
        st.markdown(f"- 🔗 **{domain}** — {count} times")

    high_risk = filtered_df[(filtered_df["pred_label"] == "Phishing") & (filtered_df["confidence"] > 0.9)]
    st.markdown(f"**High-Risk Phishing Messages:** {len(high_risk)}")


    # --- TABS ---
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Preview", "🧠 Detection", "🕒 Timeline", "📥 Export"])

    with tab1:
        st.markdown("### 📊 SMS Preview")
        st.dataframe(filtered_df[["timestamp", "sender", "text"]].sort_values("timestamp", ascending=False), use_container_width=True)
        st.markdown("### 📞 Call Log Preview")
        st.dataframe(call_df.sort_values("timestamp", ascending=False).head(10), use_container_width=True)

        # Summary stats
        st.markdown("### 📈 Summary")
        top_senders = filtered_df["sender"].value_counts().head(5)
        st.write("**Top SMS Senders**")
        st.write(top_senders)

        all_urls = sum(filtered_df["urls"].dropna().tolist(), [])
        top_domains = Counter([re.sub(r'^https?://(www\.)?', '', u).split('/')[0] for u in all_urls]).most_common(5)
        st.write("**Top Domains in SMS:**")
        for domain, count in top_domains:
            st.markdown(f"- 🔗 **{domain}** — {count} times")

        high_risk = filtered_df[(filtered_df["pred_label"] == "Phishing") & (filtered_df["confidence"] > 0.9)]
        st.markdown(f"**High-Risk Phishing Messages:** {len(high_risk)}")

    with tab2:
        st.markdown("### 🧠 Phishing Detection")
        st.dataframe(filtered_df[["timestamp", "sender", "text", "pred_label", "confidence", "urls", "explanation"]], use_container_width=True)

        # Confidence chart
        st.markdown("### 🔬 Confidence Score Distribution")
        fig, ax = plt.subplots()
        sns.histplot(filtered_df["confidence"], bins=20, ax=ax, kde=True)
        st.pyplot(fig)

    with tab3:
        st.markdown("### 🕒 Correlated Forensic Timeline")
        timeline = filtered_df.copy()
        timeline["event"] = timeline.apply(
        lambda row: f"📩 SMS from **{row['sender']}** → \"{row['text'][:50]}...\"<br>"
                    f"🔗 URLs: {', '.join(row['urls']) if row['urls'] else 'None'}<br>"
                    f"🧠 Reason: {row['keyword_reason']}<br>"
                    f"🛡️ Explanation: {row['explanation']}",
        axis=1
    )
        timeline["time_str"] = timeline["timestamp"].dt.strftime("[%H:%M]")
        if call_df is not None:
            call_df["event"] = call_df.apply(
            lambda row: f"📞 Call to **{row['number']}** ({'Missed' if row['type']==3 else 'Answered'})",
            axis=1
        )
            call_df["time_str"] = call_df["timestamp"].dt.strftime("[%H:%M]")
            combined = pd.concat([
            timeline[["timestamp", "time_str", "event"]],
            call_df[["timestamp", "time_str", "event"]]]).sort_values("timestamp")
        else:
            combined = timeline[["timestamp", "time_str", "event"]]
        for _, row in combined.iterrows():
            is_phishing = "phishing" in row.get("event", "").lower()
            render_timeline_card(row["time_str"], row["event"], is_phishing=is_phishing)


    with tab4:
        st.markdown("### 📥 Export CSV Report")
        export_csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ Download Full Report", export_csv, "phishing_report.csv", "text/csv")

else:
    st.warning("⚠️ Upload a CSV or select a valid logical image path.")





