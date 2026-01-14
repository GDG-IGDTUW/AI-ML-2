## 📊 WhatsApp Chat Analyzer

WhatsApp Chat Analyzer is a Streamlit app that takes an **exported WhatsApp chat file** and gives you visual insights about activity, words, emojis, links and more – either for the whole group or a single participant.

---

## 🧠 Features

- 📈 Total messages, words, links, and media shared
- 👤 Most active users with percentage contribution
- ☁️ Word cloud excluding Hinglish stop words
- 🧠 Most common words used
- 😂 Emoji usage analysis
- 🕒 Monthly and daily timeline of activity
- 📅 Weekly and monthly activity distribution
- 🔥 Heatmap showing activity by hour and day

---

## 🛠 Tech Stack

- Python  
- Pandas  
- Matplotlib, Seaborn  
- WordCloud  
- URLExtract  
- Emoji  
- Streamlit (UI)

---

## 📂 Project Structure (core files)

- `app.py` – Streamlit app entrypoint (sidebar upload, user selection, all charts).
- `preprocessor.py` – Parses exported WhatsApp text file into a clean `pandas` DataFrame (dates, users, messages, etc.).
- `helper.py` – Helper functions for stats, timelines, wordclouds, emojis, and activity maps.
- `stop_hinglish.txt` – Custom stopword list used for word analysis.

---

## 📥 Preparing Your WhatsApp Chat

1. On your phone, open the chat or group you want to analyze.
2. Use **Export chat** (without media is recommended).
   - On Android: *More options → More → Export chat*  
   - On iOS: *Contact info / Group info → Export Chat*
3. Choose **“Without media”** to keep the file small.
4. Transfer the exported `.txt` file to your computer.

---

## 🧪 Local Setup & Running

### 1. Create a virtual environment (optional but recommended)

From the `Whatsapp-Chat-Analyser-main` directory:

```bash
python -m venv venv          # first time
venv\Scripts\activate        # Windows (or `source venv/bin/activate` on macOS/Linux)
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Streamlit app

```bash
streamlit run app.py
```

Then open the URL shown in the terminal (usually `http://localhost:8501`).

---

## 💻 Using the App

1. Start the app with `streamlit run app.py`.
2. In the left **sidebar**, use the file uploader to select your exported `.txt` chat file.
3. Once loaded:
   - Choose **“Overall”** or a specific user from the dropdown.
   - Click **“Show Analysis”**.
4. Scroll through:
   - Top-level stats (messages, words, media, links).
   - Timelines and activity heatmap.
   - Most active users (for overall view).
   - Wordcloud, common words, and emoji breakdown.

---

## 🌱 Ideas for Extensions

- Add sentiment analysis per user or per time period.
- Add response-time analysis and “conversation bursts”.
- Add more robust parsing for different WhatsApp export formats/locales.
- Export insights as a PDF or image report.

