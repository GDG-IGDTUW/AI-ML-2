from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import base64
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

app = Flask(__name__)
CORS(app)

# Load the Face Landmarker model
BaseOptions = python.BaseOptions
FaceLandmarker = vision.FaceLandmarker
FaceLandmarkerOptions = vision.FaceLandmarkerOptions
VisionRunningMode = vision.RunningMode

model_path = "face_landmarker.task"  # ← change if using different model file

options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=model_path),
    running_mode=VisionRunningMode.IMAGE,
    num_faces=1,
    min_face_detection_confidence=0.5,
    min_tracking_confidence=0.5,
    min_face_presence_confidence=0.5,
    output_face_blendshapes=True,
    output_facial_transformation_matrixes=False
)

landmarker = FaceLandmarker.create_from_options(options)

# Mouth landmark indices (same as before – adapted for new API)
MOUTH_CORNERS_LEFT = 61
MOUTH_CORNERS_RIGHT = 291
MOUTH_UPPER_POINTS = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291]  # example subset
MOUTH_LOWER_POINTS = [146, 91, 181, 84, 17, 314, 405, 321, 375]

def calculate_smile_score(face_landmarker_result):
    """
    Calculate smile score (0-1) based on mouth corner elevation.
    
    Heuristic:
    - Measures how much mouth corners are pulled up relative to mouth center
    - Higher elevation = higher score
    - Score clamped between 0 and 1
    """
    if not face_landmarker_result.face_landmarks:
        return 0.0

    landmarks = face_landmarker_result.face_landmarks[0]

    # Get coordinates (normalized 0-1)
    left_corner = landmarks[MOUTH_CORNERS_LEFT]
    right_corner = landmarks[MOUTH_CORNERS_RIGHT]

    # Rough mouth center Y
    upper_y = sum(landmarks[i].y for i in MOUTH_UPPER_POINTS[:5]) / 5
    lower_y = sum(landmarks[i].y for i in MOUTH_LOWER_POINTS[:5]) / 5
    center_y = (upper_y + lower_y) / 2

    # Mouth openness filter (penalize talking/yawning)
    mouth_height = lower_y - upper_y
    if mouth_height > 0.08:
        return 0.0

    # Calculate corner elevation
    left_elevation = max(0, center_y - left_corner.y)
    right_elevation = max(0, center_y - right_corner.y)
    avg_elevation = (left_elevation + right_elevation) / 2

    # Scale to 0-1 range (0.015 = threshold, 0.04 = max smile)
    score = min(1.0, max(0.0, (avg_elevation - 0.005) / 0.035))
    
    return round(score, 3)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

@app.route('/predict', methods=['POST'])
def predict_smile():
    try:
        data = request.get_json()
        if 'image' not in data:
            return jsonify({'error': 'No image data'}), 400

        _, encoded = data['image'].split(",", 1)
        img_data = base64.b64decode(encoded)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({'error': 'Decode failed'}), 400

        img = cv2.flip(img, 1)  # mirror
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Convert to MP Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)

        # Detect
        detection_result = landmarker.detect(mp_image)

        score = calculate_smile_score(detection_result)
        smile_detected = score > 0.5

        return jsonify({
            'smile': smile_detected,
            'score': score
        })

    except Exception as e:
        print("Error:", str(e))
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)