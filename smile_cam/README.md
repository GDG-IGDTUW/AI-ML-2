# 😄 Smile Photobooth

Smile Photobooth is a small React + Flask app that uses a **face-landmark model** to detect smiles from your webcam and automatically capture a 3-photo strip you can download and share.

---

## 🚀 What It Does

- Uses your **webcam** in the browser.
- Sends frames to a Flask backend, which uses **MediaPipe face landmarker** to decide if you are smiling.
- Automatically captures 3 photos as you smile, with a countdown for each shot.
- Lets you add a short caption under the strip.
- Generates a **vertical photobooth-style collage** and lets you **download** it as a JPEG.

---

## 🧩 Tech Stack

| Layer            | Stack                                                  |
| ---------------- | ------------------------------------------------------ |
| Frontend         | React, Vite, Tailwind-style utilities, `react-webcam` |
| Backend          | Flask, Flask-CORS, OpenCV, MediaPipe face_landmarker  |
| Image Processing | Canvas-based capture and compositing on the frontend  |

---

## 🛠 Local Setup

### 1. Backend (Flask)

From the `smile_cam/backend` directory:

```bash
python -m venv venv              # first time only
venv\Scripts\activate            # Windows (or `source venv/bin/activate` on macOS/Linux)
pip install -r requirements.txt  # if you have a requirements file, or install Flask + mediapipe + opencv-python
python app.py
```

- The backend will start on `http://localhost:5000`.
- Test it with:

```text
GET http://localhost:5000/health
→ {"status": "healthy"}
```

Make sure the `face_landmarker.task` file is present in the `backend` folder; this is the MediaPipe model the server loads at startup.

### 2. Frontend (React)

From the `smile_cam/frontend` directory:

```bash
npm install
npm run dev
```

- Open the printed Vite URL (usually `http://localhost:5173`).
- The app expects the backend at `http://localhost:5000` for:
  - `GET /health`
  - `POST /predict` – for smile detection

If you change the backend URL or port, update the fetch URLs in `src/App.jsx` accordingly.

---

## 📸 Usage Flow

1. Start the backend (`python app.py`) and frontend (`npm run dev`).
2. Open the frontend in your browser and allow **camera access** when prompted.
3. Click **Start Session**.
4. Look at the camera and smile 😄 – the app will detect smiles and start a countdown for each capture.
5. After 3 photos, you can add a short message.
6. Generate the final strip and click **Download** to save the image.

---

## 🤔 Future Ideas

- Add filters or frames to photos.
- Allow different layouts (3×1 horizontal vs 1×3 vertical).
- Show debug overlays for face landmarks and smile score.
- Add a simple analytics mode (e.g., “smile score” over a session).
