import re
from urllib.parse import urlparse

def extract_urls(text):
    """Finds all URLs in a string."""
    return re.findall(r'(https?://[^\s]+)', text)

def calculate_url_risk(url):
    """
    Calculates a basic risk score based on lexical features.
    Addresses Issue #47.
    """
    score = 0
    suspicious_keywords = ['login', 'bank', 'verify', 'otp', 'update', 'bit.ly', 'free']
    
    # 1. Check for suspicious keywords
    for word in suspicious_keywords:
        if word in url.lower():
            score += 30
            
    # 2. Check for unusual length (many phishing links are long)
    if len(url) > 50:
        score += 20
        
    # 3. Check for IP address instead of domain name
    if re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', url):
        score += 50

    return min(score, 100) # Cap score at 100

def analyze_message_urls(text):
    urls = extract_urls(text)
    results = []
    for url in urls:
        risk = calculate_url_risk(url)
        results.append({"url": url, "risk_score": risk})
    return results
