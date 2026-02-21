from langdetect import detect
import re

def detect_languages(text):
    words = text.split()
    languages = []

    for word in words:
        try:
            lang = detect(word)
            languages.append(lang)
        except:
            continue

    return list(set(languages))


def is_code_switched(text):
    langs = detect_languages(text)
    return len(langs) > 1
