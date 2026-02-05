import re

def detect_multilingual_lures(text):
    """
    Addresses #45: Detects phishing lures in Hinglish and Hindi Script.
    """
    text = text.lower()
    
    # 1. Hindi Keywords in English Script (Hinglish)
    hinglish_patterns = {
        'lottery_lure': r'\b(inami|jeeta|lucky|inaam|jeete)\b',
        'urgency_lure': r'\b(jaldi|turant|band|sampark)\b',
        'banking_lure': r'\b(khata|aadhar|kyc_update|paisa)\b'
    }
    
    # 2. Hindi Script (Devanagari) patterns
    hindi_script_patterns = {
        'otp': r'ओटीपी',
        'account': r'खाता|बैंक',
        'prize': r'बधाई|जीता'
    }
    
    flags = []
    for label, pattern in hinglish_patterns.items():
        if re.search(pattern, text):
            flags.append(label)
            
    for label, pattern in hindi_script_patterns.items():
        if re.search(pattern, text):
            flags.append(label)
            
    return flags

def clean_text_for_model(text):
    """Removes noise while preserving multilingual context."""
    # Basic cleaning but keeping emojis as they are often used in Indian scams 🚨
    text = re.sub(r'\s+', ' ', text).strip()
    return text
