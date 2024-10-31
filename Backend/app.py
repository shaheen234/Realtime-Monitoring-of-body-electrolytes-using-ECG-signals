from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, jsonify, request
import numpy as np
import firebase_admin
from firebase_admin import credentials, db
import tensorflow as tf
import threading
import time
import pandas as pd
import numpy as np
from scipy.signal import find_peaks, butter, filtfilt
from sklearn.preprocessing import StandardScaler

# Initialize Flask app
app = Flask(__name__)

# Initialize Firebase Admin SDK
cred = credentials.Certificate('electrolyte-eb1bc-firebase-adminsdk-582sj-42c24ce291.json')  # Path to your downloaded service account key
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://electrolyte-eb1bc-default-rtdb.firebaseio.com/'
})

@app.route('/')
def home():
    return "Flask server is running!"

# Route to trigger the ESP32 via Firebase
@app.route('/trigger', methods=['POST'])
def trigger():
    try:
        # Update the Firebase path to start sending data
        ref = db.reference('/start_signal')
        ref.update({'status': 'on'})
        return jsonify({'message': 'Signal sent to ESP32'}), 200
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


# Function to preprocess the data
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

# Function to handle new data
def process_new_data(data_id, ecg_data):
    print("process_new_data")
    try:
        ecg_value = ecg_data.get('ecg_value')
        ecg_value = np.array(ecg_value)

        # Preprocess the ECG data
        processed_value = preprocess_data(ecg_value)

        # Make a prediction
        print("processed_value",processed_value)
        prediction = model.predict(processed_value)
        print("prediction: ", prediction)
        # Save the prediction result back to Firebase
        result_ref = db.reference(f'/predictions/{data_id}')
        serializable_prediction = [arr.tolist() for arr in prediction]

        electrolytes = ["Potassium", "Magnesium","Calcuim"]
        serializable_prediction[0] = electrolytes[np.argmax(serializable_prediction[0])]
        serializable_prediction[1] = "High" if serializable_prediction[1][0][0] > 5 else "Low"

        result_ref.set({
            'prediction_value': serializable_prediction
        })
        print(f'Processed data_id {data_id} and saved prediction.')
        return serializable_prediction
    except Exception as e:
        # Handle any errors
        result_ref = db.reference(f'/predictions/{data_id}')
        result_ref.set({'error': str(e)})
        print(f'Error processing data_id {data_id}: {e}')

@app.route('/process-data', methods=['POST'])
# Function to continuously monitor Firebase for new data
def monitor_firebase():
    ref = db.reference('/ecg_data')
    # time.sleep(5)
    try:
        ecg_data = ref.get()
        # print(ecg_data)
        if ecg_data:
            for data_id, data in ecg_data.items():
                result_ref = db.reference(f'/predictions/{data_id}')
                if not result_ref.get():
                    pred = process_new_data(data_id, data)
        return jsonify({'message': f'prediction {pred}'}), 200
    except Exception as e:
        print(f'Error monitoring Firebase: {e}')
        return jsonify({'message': f'Error monitoring Firebase: {e}'}), 500

# Run the Firebase monitoring in a separate thread
# threading.Thread(target=monitor_firebase, daemon=True).start()




if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
