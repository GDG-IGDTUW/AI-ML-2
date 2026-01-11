import streamlit as st
import pandas as pd
import torch
from transformers import BertTokenizer, BertForSequenceClassification
import matplotlib.pyplot as plt
import seaborn as sns
import re
from datetime import datetime
import os
import glob
import sqlite3
import numpy as np
from fpdf import FPDF

def correlate_sms_app_call(sms_df, call_df, app_df, window_minutes=5):
    correlated = []

    for _, sms in sms_df.iterrows():
        sms_time = sms['timestamp']
        window_start = sms_time
        window_end = sms_time + pd.Timedelta(minutes=window_minutes)
        
        related_calls = call_df[(call_df['timestamp'] >= window_start) & (call_df['timestamp'] <= window_end)]
        chrome_launch = app_df[(app_df['timestamp'] >= window_start) & (app_df['timestamp'] <= window_end) & 
                               (app_df['package'] == 'com.android.chrome')]

        correlation_result = {
            'sms_text': sms['text'],
            'sms_time': sms_time,
            'url': sms.get('urls', [None])[0],
            'chrome_opened': not chrome_launch.empty,
            'call_found': not related_calls.empty,
            'confidence': sms['confidence']
        }

        # 🔼 Boost score if both call + chrome usage seen
        if correlation_result['chrome_opened'] or correlation_result['call_found']:
            correlation_result['confidence'] = min(1.0, correlation_result['confidence'] + 0.05)

        correlated.append(correlation_result)

    return pd.DataFrame(correlated)

# --- Load Model and Tokenizer ---
@st.cache_resource
def load_model():
    model_path = os.path.join(os.path.dirname(__file__), "phishing_bert_tiny_model")
    tokenizer = BertTokenizer.from_pretrained(model_path)
    model = BertForSequenceClassification.from_pretrained(model_path)
    return tokenizer, model


tokenizer, model = load_model()
model.eval()

# --- Functions ---
import re

# Extract all URLs from SMS text
def extract_urls(text):
    if not isinstance(text, str):
        return []
    url_pattern = r"(https?://[^\s]+)"
    return re.findall(url_pattern, text)


def predict(texts):
    inputs = tokenizer(texts, padding=True, truncation=True, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=1)
        preds = torch.argmax(probs, axis=1)
    return preds.numpy(), probs[:, 1].numpy()  # label, phishing confidence
def render_stylized_timeline(df, call_df=None):
    import streamlit as st

    st.markdown("### 🧾 Stylized Forensic Timeline")

    # Create unified timeline DataFrame
    df["event"] = df.apply(
        lambda row: f"SMS from {row.get('sender', 'Unknown')} → \"{row['text'][:40]}...\" "
                    f"(Conf: {row['confidence']:.2f}, OTP: {'✅' if row['otp_flag'] else '❌'})",
        axis=1
    )
    df["time_str"] = df["timestamp"].dt.strftime("[%H:%M]")

    if call_df is not None:
        call_df["event"] = call_df.apply(
            lambda row: f"📞 Call to {row['number']} ({'Missed' if row.get('type')==3 else 'Answered'})",
            axis=1
        )
        call_df["time_str"] = call_df["timestamp"].dt.strftime("[%H:%M]")
        call_df["text"] = ""
        call_df["confidence"] = 0.0
        call_df["otp_flag"] = False
        call_df["pred_label"] = "Call"
        combined = pd.concat([df, call_df], ignore_index=True)
    else:
        combined = df

    combined = combined.sort_values("timestamp")

    # Render timeline with style
    for _, row in combined.iterrows():
        bg = "#d1ecf1"  # default blue
        icon = "📩"
        if row["pred_label"] == "Phishing":
            bg = "#f8d7da"  # light red
            icon = "🚨"
        elif row["otp_flag"]:
            bg = "#fff3cd"  # yellow
            icon = "🔐"
        elif row["pred_label"] == "Call":
            bg = "#f0f0f0"
            icon = "📞"

        styled = f"""
        <div style="background-color:{bg}; padding:8px; margin-bottom:6px; border-radius:6px">
            <b>{row['time_str']}</b> {icon} {row['event']}
        </div>
        """
        st.markdown(styled, unsafe_allow_html=True)


        


def detect_otp(text):
    return bool(re.search(r'\b(otp|one time password|ओटीपी)\b', str(text).lower()))


import sqlite3
import pandas as pd


def extract_app_df(sqlite_path):
        conn = sqlite3.connect(sqlite_path)
        df = pd.read_sql("SELECT time, package_name, event_type FROM usage_events", conn)
        df = df[df["event_type"] == 1]  # ACTIVITY_RESUMED
        df["timestamp"] = pd.to_datetime(df["time"], unit="ms", errors="coerce")
        return df[["timestamp", "package_name"]]



import re
import whois
import socket
import requests
from urllib.parse import urlparse
from datetime import datetime

# ✅ 1. URL Extractor
def extract_urls(text):
    if not isinstance(text, str):
        return []
    url_pattern = r"(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9.-]+\.(com|in|org|net|xyz|online|co|biz)[^\s]*)"
    return re.findall(url_pattern, text)

# ✅ 2. Labeling logic
def keyword_reason(text):
    text = text.lower()
    keywords = {
        "kyc": "KYC-related",
        "otp": "Mentions OTP",
        "recharge": "Recharge request",
        "lucky": "Lottery keyword",
        "win": "Prize keyword",
        "click": "Clickbait",
        "urgent": "Urgency tone",
        "verify": "Verification trap",
        "account": "Account-related"
    }
    reasons = [desc for k, desc in keywords.items() if k in text]
    return ", ".join(reasons) if reasons else "Legit-looking"

# ✅ 3. WHOIS Lookup (safe fallback)
def whois_domain_info(url):
    if isinstance(url, bytes):  # optional safety check
            url = url.decode()

    domain = urlparse(url).netloc or url
    try:
        w = whois.whois(domain)
        return {
            "domain": domain,
            "created": str(w.creation_date)[:10] if w.creation_date else "Unknown",
            "registrar": w.registrar or "Unknown"
        }
    except Exception:
        return {
            "domain": domain,
            "created": "Unknown",
            "registrar": "Unknown"
        }

# ✅ 4. Port Scan (shallow optional)
def scan_ports(domain, ports=[80, 443, 8080]):
    try:
        ip = socket.gethostbyname(domain)
        open_ports = []
        for port in ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((ip, port))
            if result == 0:
                open_ports.append(port)
            sock.close()
        return open_ports
    except:
        return []

# ✅ 5. Explanation engine
def explain_message(row):
    explanation = []
    if row["urls"]:
        for u in row["urls"]:
            info = whois_domain_info(str(u))
            if "xyz" in info["domain"] or "online" in info["domain"]:
                explanation.append(f"🧠 Fake TLD ({info['domain']})")
            if info["created"] == "Unknown":
                explanation.append("🌐 Domain age unknown")
            elif int(datetime.now().year) - int(info["created"][:4]) < 2:
                explanation.append("🧠 Newly registered domain")

            ports = scan_ports(info["domain"])
            if 8080 in ports:
                explanation.append("🔎 Suspicious port 8080 open")

    if "otp_flag" in row and row["otp_flag"]:
        explanation.append("🔐 OTP-related content")

    if "keyword_reason" in row and row["keyword_reason"] != "Legit-looking":
        explanation.append(f"💡 Keywords: {row['keyword_reason']}")

    return "; ".join(explanation) if explanation else "✅ No red flags"


def render_timeline_card(time, event_html, is_phishing=False):
    color = "#ffcccc" if is_phishing else "#e8f0fe"
    st.markdown(f"""
    <div style="background-color: {color}; padding: 10px 15px; margin-bottom: 10px;
                border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <strong style="color: #444;">{time}</strong> → <span style="color: #222;">{event_html}</span>
    </div>
    """, unsafe_allow_html=True)




def custom_serializer(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    if isinstance(obj, set):
        return list(obj)
    return str(obj)  # Fallback

from datetime import datetime
import json, os
import ast

import ast

def format_event(row):
    try:
        urls = row["urls"]
        if isinstance(urls, str):
            urls = ast.literal_eval(urls)
        if not isinstance(urls, list):
            urls = []
    except Exception:
        urls = []

    return (
        f"📩 SMS from **{row.get('sender', 'Unknown')}**: \"{str(row.get('text',''))[:50]}...\"\n"
        f"🔗 URLs: {', '.join(urls) if urls else 'None'}\n"
        f"🧐 Reason: {row.get('keyword_reason','N/A')}\n"
        f"🛡️ Explanation: {row.get('explanation','')}"
    )


