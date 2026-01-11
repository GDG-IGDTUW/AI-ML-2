import random
import requests
import time
import argparse

API_URL = "http://127.0.0.1:5000/predict"

def generate_event(event_type="normal"):
    base = {
        "email": f"user{random.randint(1,100)}@example.com",
        "ip": f"192.168.{random.randint(0,1)}.{random.randint(1,254)}",
        "device_id": "DEVICE123",
        "imei": "123456789012345",
        "location": "Delhi, IN",
        "timestamp": time.time()
    }

    if event_type == "normal":
        # Use a realistic public IP range (Indian ISP blocks, not private 192.168.x.x)
        base["ip"] = f"103.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
        # Simulate business-hour logins (9 AM – 8 PM local)
        now = time.time()
        random_hour = random.randint(9, 20)
        # pick a random time today within business hours
        base["timestamp"] = now - (now % 86400) + random_hour * 3600 + random.randint(0, 3600)
        # Simulate known devices (to avoid "new_device" flag)
        base["device_id"] = random.choice(["DEVICE123", "DEVICE456", "DEVICE789"])
        base["imei"] = random.choice([
        "123456789012345",
        "987654321098765",
        "543216789012345"
    ])
        # Keep location consistent (small geo drift like in training data)
        base["location"] = "Delhi, IN"
        return base


    elif event_type == "suspicious":
        # Slight anomaly: new device or odd login time
        base["device_id"] = f"DEV{random.randint(1000,9999)}"
        return base

    elif event_type == "fraud":
        # Multiple anomalies: new SIM, new IP, foreign location
        base["ip"] = f"203.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        base["imei"] = f"{random.randint(100000000000000,999999999999999)}"
        base["location"] = random.choice(["Moscow, RU", "Lagos, NG", "Sao Paulo, BR", "Beijing, CN"])
        return base


def run_simulator(mode="demo"):
    if mode == "demo":
        weights = [0.5, 0.3, 0.2]   # Normal, Suspicious, Fraud
        delay = 2
    elif mode == "stress":
        weights = [0.3, 0.3, 0.4]   # More frauds
        delay = 0.5
    else:
        weights = [0.5, 0.3, 0.2]
        delay = 2

    while True:
        choice = random.choices(["normal", "suspicious", "fraud"], weights=weights)[0]
        event = generate_event(choice)
        try:
            r = requests.post(API_URL, json=event)
            print(f"Sent {choice} event → {r.status_code}")
        except Exception as e:
            print(f"Error sending event: {e}")
        time.sleep(delay)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BAIDS Simulator")
    parser.add_argument("--mode", choices=["demo", "stress"], default="demo", help="Mode: demo (balanced) or stress (high volume fraud)")
    args = parser.parse_args()
    run_simulator(args.mode)
