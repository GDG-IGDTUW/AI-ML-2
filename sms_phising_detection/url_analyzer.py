import re
from urllib.parse import urlparse

def extract_urls(text):
    """Finds links in the SMS."""
    return re.findall(r'(https?://[^\s]+)', text)

def predict_url_risk(url):
    """
    Solves Issue #47: Predicts if a URL is risky 
    based on length, keywords, and structure.
    """
    risk_score = 0
    # 1. Check for suspicious keywords (Phishing Lures)
    keywords = ['login', 'verify', 'bank', 'bit.ly', 'secure', 'update', 'otp']
    for word in keywords:
        if word in url.lower():
            risk_score += 30

    # 2. Check for abnormal length
    if len(url) > 50:
        risk_score += 20

    # 3. Check for IP-based URLs (Common in phishing)
    if re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', url):
        risk_score += 50

    return min(risk_score, 100)
