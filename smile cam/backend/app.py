from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import base64

app = Flask(__name__)
CORS(app)

# Load OpenCV Haar cascades for face and smile detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_smile.xml")

@app.route('/predict', methods=['POST'])
def predict_smile():
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({'error': 'No image data provided'}), 400

    try:
        #first we will convert img to binary we will remove the prefix by split 
        #then we we will convert img_data (binary) to a numpy array 
        #now we will decode the numpy array 
        img_data = base64.b64decode(data['image'].split(',')[1])
        if not img_data:
            return {"error": "No image data"}, 400
        np_arr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        # Convert to grayscale for detection because haarcascade fn only works on grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detect faces 
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

        #here x= x cordinate of top left corner of detected object 
        # y = y cordinate of top left corner of detected object 
        # w= width in pixels of the bounding box
        #h= height in pixels of the bounding box
        for (x, y, w, h) in faces:
            #this line extracts the region of interest -> y to y+h and x to x+w
            roi_gray = gray[y:y+h, x:x+w]
            # Detect smiles in the face region
            #we will only use this fn on the bounded face box not the entire image 
            #gives the similar list [(x ,y , w ,h) ,....] if length of smiles length == no. of detected faces
            smiles = smile_cascade.detectMultiScale(
                roi_gray,
                scaleFactor=1.8,
                minNeighbors=20
            )
            if len(smiles)>0:
                return jsonify({'smile': True})

        return jsonify({'smile': False})

    except Exception as e:
        print("Error:", e)
        return jsonify({'error': f'Error processing image: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True , host='0.0.0.0', port=5000)
