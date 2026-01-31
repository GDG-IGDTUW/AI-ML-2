import re
import whois
from urllib.parse import urlparse

class URLForensics:
    def __init__(self):
        self.suspicious_tlds = ['.zip', '.support', '.xyz', '.click', '.top']

    def extract_urls(self, text):
        return re.findall(r'(https?://[^\s]+)', text)

    def get_domain_age(self, url):
        """Forensic check: New domains are often used for phishing."""
        try:
            domain = urlparse(url).netloc
            w = whois.whois(domain)
            return w.creation_date
        except:
            return "Unknown"

    def calculate_risk(self, url):
        score = 0
        parsed = urlparse(url)
        
        # 1. Lexical Check (Issue #47 Core)
        if len(url) > 60: score += 20
        if parsed.netloc.count('.') > 3: score += 15
        
        # 2. Sensitive Keyword Check
        if any(keyword in url.lower() for keyword in ['login', 'verify', 'bank', 'otp']):
            score += 30
            
        # 3. Protocol Check
        if parsed.scheme == 'http': score += 10 # Unencrypted is riskier

        return min(score, 100)
