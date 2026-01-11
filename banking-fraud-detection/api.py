from flask import Flask, request, jsonify
from hybrid_predictor import hybrid_predict
import json, datetime, os

app = Flask(__name__)

LOG_DIR = "forensics_logs"
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, f"{datetime.date.today()}.jsonl")

@app.route("/predict", methods=["POST"])
def predict():
    event = request.json
    result = hybrid_predict(event)
    entry = {
        "ts": datetime.datetime.utcnow().isoformat(),
        "event": event,
        "result": result
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return jsonify(result)

@app.route("/health")
def health():
    return {"status": "ok"}

# 🔧 Add this so Flask actually runs
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
