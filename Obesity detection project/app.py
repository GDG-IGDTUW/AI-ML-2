from flask import Flask, request, jsonify, render_template
import numpy as np
import pickle

app = Flask(__name__)

# Load the trained SVM model and scaler
with open("model.pkl", "rb") as model_file:
    model = pickle.load(model_file)

with open("scaler.pkl", "rb") as scaler_file:
    scaler = pickle.load(scaler_file)

@app.route('/')
def home():
    return render_template('form.html')

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.form  # Get form data

        # Define feature names
        numerical_features = ['Age', 'Height', 'Weight', 'FCVC', 'NCP', 'CH2O', 'FAF', 'TUE']  # Features to normalize
        categorical_features = ['Gender', 'CALC', 'FAVC', 'SCC', 'SMOKE', 'family_history', 'CAEC', 'MTRANS']  # Features NOT to normalize

        # Extract values from the form
        numerical_values = np.array([float(data[feature]) for feature in numerical_features]).reshape(1, -1)
        categorical_values = np.array([int(data[feature]) for feature in categorical_features]).reshape(1, -1)

        # Normalize numerical values
        numerical_values_scaled = scaler.transform(numerical_values)

        # Combine normalized and categorical features
        user_input_scaled = np.concatenate([numerical_values_scaled, categorical_values], axis=1)

        # Predict using the SVM model
        prediction = model.predict(user_input_scaled)

        # Obesity class mapping
        obesity_classes = {
            0: "Underweight",
            1: "Normal weight",
            2: "Obesity Type 1",
            3: "Obesity Type 2",
            4: "Obesity Type 3",
            5: "Overweight Level 1",
            6: "Overweight Level 2"
        }
        predicted_class = obesity_classes.get(prediction[0], "Unknown")

        return render_template('form.html', prediction_text=f"Predicted Obesity Level: {predicted_class}")

    except Exception as e:
        return render_template('form.html', prediction_text=f"Error: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True)
