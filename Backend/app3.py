import pandas as pd
import firebase_admin
from firebase_admin import credentials, db

"""
Run this script to send data only if the start signal status is "on".

"""
def send_ecg_data_to_firebase(file_path, firebase_url, firebase_cred):
    # Initialize Firebase Admin SDK
    cred = credentials.Certificate(firebase_cred)
    firebase_admin.initialize_app(cred, {
        'databaseURL': firebase_url
    })

    # Reference to the start_signal node
    start_signal_ref = db.reference('/start_signal')

    # Get the current status
    start_signal_status = start_signal_ref.get()

    # Check if the start signal status is "on"
    if start_signal_status and start_signal_status.get('status') == 'on':
        # Read the raw ECG data from the CSV file
        df = pd.read_csv(file_path)
        ecg_values = df['ECG Value'].values.tolist()  # Convert to a list

        # Push the data to Firebase
        ref = db.reference('/ecg_data')
        new_data_ref = ref.push({'ecg_value': ecg_values})

        print("Data sent to Firebase with ID:", new_data_ref.key)
    else:
        print("Start signal status is not 'on'. Data was not sent.")

# Example usage
file_path = "ecg_data2.csv"  # Update with your file path
firebase_url = 'https://electrolyte-eb1bc-default-rtdb.firebaseio.com/'  # Update with your Firebase Realtime Database URL
firebase_cred = 'electrolyte-eb1bc-firebase-adminsdk-582sj-42c24ce291.json'  # Update with the path to your Firebase service account key

send_ecg_data_to_firebase(file_path, firebase_url, firebase_cred)
