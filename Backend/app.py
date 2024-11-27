from flask import Flask, jsonify,request
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, jsonify
import numpy as np
import firebase_admin
from firebase_admin import credentials, db,auth
import tensorflow as tf
import numpy as np
from scipy.signal import find_peaks, butter, filtfilt
from sklearn.preprocessing import StandardScaler
from datetime import datetime

#

# Initialize Flask app
app = Flask(__name__)

SERVICE_ACCOUNT_KEY_PATH = "electrolyte-eb1bc-f91269c3cf57.json"

# Initialize Firebase Admin SDK
cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)  # Path to your downloaded service account key
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://electrolyte-eb1bc-default-rtdb.firebaseio.com/'
})

def home():
    return "Flask server is running!"

# Route to trigger the ESP32 via Firebase, user-specific
@app.route('/trigger', methods=['POST'])
def trigger():
    try:
        # Get user_id from the request JSON body, defaulting to a hardcoded value if not provided
        user_id = request.json.get("user_id")  # Use "test_user_12345" as a default user_id

        # Update the Firebase path to start sending data
        ref = db.reference(f'/users/{user_id}/start_signal')
        ref.update({'status': 'on'})

        return jsonify({'message': f'Signal sent to ESP32 for user {user_id}'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


model = tf.keras.models.load_model('my_model.h5')  # Update with your model path


def calculate_intervals(ecg_data):

    def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
        nyq = 0.5 * fs
        low = lowcut / nyq
        high = highcut / nyq
        b, a = butter(order, [low, high], btype='band')
        y = filtfilt(b, a, data)
        return y

    # Parameters
    fs = 250  # Sampling frequency
    lowcut = 0.5  # Low cut-off frequency
    highcut = 45.0  # High cut-off frequency

    # Filter ECG data
    filtered_ecg = butter_bandpass_filter(ecg_data, lowcut, highcut, fs, order=4)

    # Detect R peaks
    r_peaks, _ = find_peaks(filtered_ecg, distance=fs*0.6, height=np.mean(filtered_ecg) + 0.5 * np.std(filtered_ecg))

    # Lists to hold indices of each wave
    p_peaks = []
    q_peaks = []
    s_peaks = []
    t_peaks = []

    # Detect other waves relative to each R peak
    for r_index in r_peaks:
        # P-wave: Search before the R peak
        p_region_start = max(0, r_index - int(0.25*fs))
        p_region_end = r_index
        p_search_region = filtered_ecg[p_region_start:p_region_end]
        if len(p_search_region) > 0:
            p_peak = np.argmax(p_search_region) + p_region_start
            p_peaks.append(p_peak)

        # Q-wave: Search before the R peak
        q_region_start = max(0, r_index - int(0.05*fs))
        q_region_end = r_index
        q_search_region = filtered_ecg[q_region_start:q_region_end]
        if len(q_search_region) > 0:
            q_peak = np.argmin(q_search_region) + q_region_start
            q_peaks.append(q_peak)

        # S-wave: Search after the R peak
        s_region_start = r_index
        s_region_end = min(r_index + int(0.05*fs), len(filtered_ecg))
        s_search_region = filtered_ecg[s_region_start:s_region_end]
        if len(s_search_region) > 0:
            s_peak = np.argmin(s_search_region) + s_region_start
            s_peaks.append(s_peak)

        # T-wave: Search after the R peak
        t_region_start = r_index
        t_region_end = min(r_index + int(0.25*fs), len(filtered_ecg))
        t_search_region = filtered_ecg[t_region_start:t_region_end]
        if len(t_search_region) > 0:
            t_peak = np.argmax(t_search_region) + t_region_start
            t_peaks.append(t_peak)

    # Calculate intervals
    rr_intervals = np.diff(r_peaks) / fs * 1000  # RR intervals in milliseconds
    pr_intervals = [(q_peaks[i] - p_peaks[i]) / fs * 1000 for i in range(min(len(p_peaks), len(q_peaks)))]
    qrs_durations = [(s_peaks[i] - q_peaks[i]) / fs * 1000 for i in range(min(len(q_peaks), len(s_peaks)))]
    qt_intervals = [(t_peaks[i] - q_peaks[i]) / fs * 1000 for i in range(min(len(q_peaks), len(t_peaks)))]

    # Calculate QTc using Bazett's formula
    qtc_intervals = [qt / np.sqrt(rr/1000) for qt, rr in zip(qt_intervals, rr_intervals[:-1])]  # QTc in seconds converted to milliseconds

    # Placeholder axis calculations (assuming each list has at least one entry)
    p_wave_axis = np.random.uniform(-30, 30, size=len(p_peaks))
    qrs_axis = np.random.uniform(-90, 90, size=len(r_peaks))
    t_wave_axis = np.random.uniform(-30, 30, size=len(t_peaks))

    # Default values if the calculated lists are empty
    default_rr = 800  # Typical RR interval in ms
    default_pr = 160  # Typical PR interval in ms
    default_qrs = 100  # Typical QRS duration in ms
    default_qt = 400  # Typical QT interval in ms
    default_qtc = 440  # Typical QTc interval in ms
    default_p_wave_axis = 0  # Default P wave axis
    default_qrs_axis = 0  # Default QRS axis
    default_t_wave_axis = 0  # Default T wave axis

    # Collect only the first value of each calculated metric, or default values if the list is empty
    result_array = np.array([
        rr_intervals[0] if len(rr_intervals) > 0 else default_rr,  # RR interval
        pr_intervals[0] if len(pr_intervals) > 0 else default_pr,  # PR interval
        qrs_durations[0] if len(qrs_durations) > 0 else default_qrs,  # QRS duration
        qt_intervals[0] if len(qt_intervals) > 0 else default_qt,  # QT interval
        qtc_intervals[0] * 1000 if len(qtc_intervals) > 0 else default_qtc,  # QTc interval converted to milliseconds
        p_wave_axis[0] if len(p_wave_axis) > 0 else default_p_wave_axis,  # P wave axis
        qrs_axis[0] if len(qrs_axis) > 0 else default_qrs_axis,  # QRS axis
        t_wave_axis[0] if len(t_wave_axis) > 0 else default_t_wave_axis  # T wave axis
    ])

    result_array = result_array.reshape(-1, 1)
    scaler = StandardScaler()
    result_array = scaler.fit_transform(result_array)
    
    return np.array(result_array)

def preprocess_data(ecg_value):
    print("preprocess_data")
    # Assuming ecg_value is a list of raw values
    ecg_values = np.array(ecg_value).flatten()

    # Step 1: Calculate intervals
    intervals = calculate_intervals(ecg_values)

    # Step 2: Pad or truncate to ensure a consistent input length
    desired_length = 8  # For example, if the model expects (1, 8, 1)

    intervals = intervals[:desired_length]

    print("intervals: ", intervals)
    # Step 3: Reshape to the format (1, 8, 1) as expected by the model
    processed_value = intervals.reshape(1, desired_length, 1)
    return processed_value

def preprocess_data(ecg_value):
    ecg_values = np.array(ecg_value).flatten()
    intervals = calculate_intervals(ecg_values)
    desired_length = 8
    intervals = intervals[:desired_length]
    processed_value = intervals.reshape(1, desired_length, 1)
    return processed_value

def process_new_data(user_id, data_id, ecg_data):
    try:
        # Get today's date
        today_date = datetime.now().strftime("%Y-%m-%d")
        
        # Reference to the user's prediction node
        result_ref = db.reference(f'/users/{user_id}/predictions/{data_id}')
        existing_prediction = result_ref.get()

        # Check if a prediction already exists for today
        if existing_prediction and existing_prediction.get('date') == today_date:
            print(f"Prediction already exists for {user_id} on {today_date}")
            return existing_prediction['prediction_value']
        
        # Proceed with prediction if not done today
        ecg_value = ecg_data.get('ecg_value')
        
        ecg_value = np.array(ecg_value)
        processed_value = preprocess_data(ecg_value)
        print(processed_value.shape)
        prediction = model.predict(processed_value)

        # Electrolyte normal ranges
        electrolyte_ranges = {
            "Potassium": {"low": 3.5, "high": 5.0},
            "Magnesium": {"low": 1.5, "high": 2.5},
            "Calcium": {"low": 8.5, "high": 10.5}
        }

        # Initialize the prediction dictionary with "Normal" values
        prediction_result = {
            "Potassium": "Normal",
            "Magnesium": "Normal",
            "Calcium": "Normal"
        }

        # Identify the predicted electrolyte and its lab value
        electrolytes = ["Potassium", "Magnesium", "Calcium"]
        predicted_index = np.argmax(prediction[0])  # Index of the predicted electrolyte
        predicted_lab_value = prediction[1][0][0]  # Lab value associated with the prediction
        
        # Get the name of the predicted electrolyte
        predicted_electrolyte = electrolytes[predicted_index]

        # Check if the predicted lab value is high, low, or normal for the predicted electrolyte
        if predicted_lab_value < electrolyte_ranges[predicted_electrolyte]["low"]:
            prediction_result[predicted_electrolyte] = "Low"
        elif predicted_lab_value > electrolyte_ranges[predicted_electrolyte]["high"]:
            prediction_result[predicted_electrolyte] = "High"
        else:
            prediction_result[predicted_electrolyte] = "Normal"

        # Save the prediction result along with the date and time back to Firebase
        result_ref.set({
            'prediction_value': prediction_result,
            'date': today_date,
            'time': datetime.now().strftime("%H:%M:%S")
        })

        print(f'Processed data_id {data_id} for user {user_id} and saved prediction.')
        return prediction_result
    except Exception as e:
        result_ref = db.reference(f'/users/{user_id}/predictions/{data_id}')
        result_ref.set({'error': str(e)})
        print(f'Error processing data_id {data_id} for user {user_id}: {e}')

@app.route('/process-data', methods=['POST'])
def monitor_firebase():
    try:
        user_id = request.json.get("user_id")
        today_date = datetime.now().strftime("%Y-%m-%d")

        # Reference for user's predictions
        result_ref = db.reference(f'/users/{user_id}/predictions')
        predictions_data = result_ref.get()

        # Check if there's an existing prediction for today
        existing_prediction = None
        if predictions_data:
            for data_id, data in predictions_data.items():
                if data.get('date') == today_date:
                    existing_prediction = data
                    break

        if existing_prediction:
            # If a prediction for today exists, return it
            return jsonify({'message': f'Prediction already exists for user {user_id}', 'prediction': existing_prediction}), 200
        
        # If no prediction exists for today, process the latest data
        ref = db.reference(f'/users/{user_id}/ecg_data/entries')
        ecg_data = ref.get()
        pred = None  # Initialize pred to avoid referencing an undefined variable

        if ecg_data:
            # Sort entries by keys (or timestamps) to find the last one
            last_entry_id = sorted(ecg_data.keys())[-1]  # Get the last entry ID
            last_entry = ecg_data[last_entry_id]         # Fetch the last entry's data

            # Check if there's already a prediction for this data entry
            result_ref = db.reference(f'/users/{user_id}/predictions/{last_entry_id}')
            if not result_ref.get():
                # Process the latest entry
                pred = process_new_data(user_id, last_entry_id, last_entry)
                # Add today's date to the prediction
                result_ref.update({
                    'date': today_date,
                    'time': datetime.now().strftime("%H:%M:%S")
                })

        return jsonify({'message': f'Prediction made for user {user_id}', 'prediction': {
        'prediction_value': pred
    }}), 200
    except Exception as e:
        print(f'Error monitoring Firebase for user {user_id}: {e}')
        return jsonify({'message': f'Error: {e}'}), 500

    


@app.route('/history', methods=['GET'])
def get_prediction_history():
    try:
        user_id = request.json.get("user_id")
    
        today_date = datetime.now().strftime("%Y-%m-%d")

        # Reference for user's predictions
        result_ref = db.reference(f'/users/{user_id}/predictions')
        predictions_data = result_ref.get()
    
        if not predictions_data:
            return jsonify({"message": "No prediction history found for the user"}), 200

        # Format prediction data
        history = []
        #change accirding to pred value
        for data_id, data in predictions_data.items():
            history.append({
                "date": data.get("date", ""),
                "time": data.get("time", ""),
                "K+": data["prediction_value"].get("Potassium", "Normal"),
                "Ca+": data["prediction_value"].get("Calcium", "Normal"),
                "Mg+": data["prediction_value"].get("Magnesium", "Normal")
            })



        return jsonify({'message': f'Historical data for user: {user_id}', 'prediction': history}), 200
    except Exception as e:
        print(f'Error monitoring Firebase for user {user_id}: {e}')
        return jsonify({'message': f'Error: {e}'}), 500
    
    # try:
    #     # Get user_id from request arguments
    #     user_id = request.args.get('user_id')
    #     print(user_id)
        
    #     # Validate if user_id is provided
    #     if not user_id:
    #         return jsonify({"error": "user_id is required"}), 400
        
    #     # Reference to the user's prediction history in Firebase
    #     result_ref = db.reference(f'/users/{user_id}/predictions')
    #     predictions_data = result_ref.get()

    #     print("did not get here", predictions_data)
    #     # If no predictions found for the user
    #     if not predictions_data:
    #         return jsonify({"message": "No prediction history found for the user"}), 200

    #     # Format prediction data
    #     history = []
    #     for data_id, data in predictions_data.items():
    #         history.append({
    #             "date": data.get("date", ""),
    #             "time": data.get("time", ""),
    #             "K+": data["prediction_value"].get("Potassium", "Normal"),
    #             "Ca+": data["prediction_value"].get("Calcium", "Normal"),
    #             "Mg+": data["prediction_value"].get("Magnesium", "Normal")
    #         })

    #     # Sort history by date and time if needed (optional)
    #     history = sorted(history, key=lambda x: (x["date"], x["time"]), reverse=True)

    #     return jsonify({"user_id": user_id, "history": history}), 200

    # except Exception as e:
    #     print(f"Error retrieving history for user {user_id}: {e}")
    #     return jsonify({"error": str(e)}), 500





if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)