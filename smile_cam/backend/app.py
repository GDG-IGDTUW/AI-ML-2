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

def is_smiling(face_landmarker_result):
    if not face_landmarker_result.face_landmarks:
        return False

    landmarks = face_landmarker_result.face_landmarks[0]  # first face

    # Get coordinates (normalized 0-1)
    left_corner = landmarks[MOUTH_CORNERS_LEFT]
    right_corner = landmarks[MOUTH_CORNERS_RIGHT]

    # Rough mouth center Y
    upper_y = sum(landmarks[i].y for i in MOUTH_UPPER_POINTS[:5]) / 5
    lower_y = sum(landmarks[i].y for i in MOUTH_LOWER_POINTS[:5]) / 5
    center_y = (upper_y + lower_y) / 2

    # Mouth openness filter
    mouth_height = lower_y - upper_y
    if mouth_height > 0.08:  # talking/yawning
        return False

    # Corners pulled up → smile
    left_up = left_corner.y < center_y - 0.015
    right_up = right_corner.y < center_y - 0.015

    return left_up and right_up

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

        smile_detected = is_smiling(detection_result)

        return jsonify({'smile': smile_detected})

    except Exception as e:
        print("Error:", str(e))
        return jsonify({'error': str(e)}), 500
@app.route('/manual_capture', methods=['POST'])
def manual_capture():
    try:
        data = request.get_json()
        
        # Validate presence of image field
        if 'image' not in data:
            return jsonify({'error': 'No image data'}), 400
        
        # Decode image safely
        _, encoded = data['image'].split(",", 1)
        img_data = base64.b64decode(encoded)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return jsonify({'error': 'Failed to decode image'}), 400
        
        # Successfully received and decoded image
        return jsonify({'ok': True})
    
    except Exception as e:
        print("Error in manual_capture:", str(e))
        return jsonify({'error': str(e)}), 500
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)