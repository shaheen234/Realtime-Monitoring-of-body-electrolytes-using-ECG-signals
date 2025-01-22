# HeartSync: Real-Time Electrolyte Imbalance Detection Using ECG Signals

HeartSync is a cutting-edge solution for detecting electrolyte imbalances (potassium, calcium, and magnesium) through non-invasive ECG signal analysis. This project integrates hardware, machine learning, and mobile app technology to provide a real-time, user-friendly health monitoring system.

---

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Repository Structure](#repository-structure)
- [Setup Instructions](#setup-instructions)


## Overview

The **HeartSync** system is designed to:
- Detect electrolyte imbalances using ECG signals captured with the **AD8232 sensor**.
- Analyze signals with a deep learning **LSTM model**.
- Display results and historical data via a **React Native mobile app**.
- Ensure seamless integration with Firebase and AWS for cloud storage and real-time feedback.

The **HeartSync Mobile App** is available on GitHub: [HeartSync Mobile App Repository](https://github.com/maryamiqtidar/heart-sync-app)

---

## Features

1. **Real-Time Analysis**:
   - ECG signals are captured and processed in real-time.
   - The system detects electrolyte imbalances with a model accuracy of **76%**.

2. **User-Friendly Mobile App**:
   - Results are displayed on the **HeartSync app**.
   - Users can view historical data and receive alerts.

3. **Cloud Integration**:
   - **Firebase** is used for real-time data synchronization.
   - **AWS** provides scalable backend infrastructure.

---

## Repository Structure

- **Backend**:
  - `app.py`: API to handle data communication between the ESP32, model, and the cloud.
  - `app3.py`: Sends processed ECG signals to the cloud for analysis.
  - `model.h5`: Pre-trained LSTM model for ECG signal analysis.
- **Hardware**:
  - `main.py`: ESP32 configuration using MicroPython.
  - `wifimgr.py`: Wi-Fi manager for ESP32 connectivity.
  - `get_signals_using_esp.ino`: Arduino sketch for capturing ECG signals.
  - `ESP_final_code`: The final code connecting ESP32 to firebase.
- **Model**:
  - `model.h5`: Pre-trained LSTM model for ECG signal analysis.
  - `updated_fyp_model2.ipynb`: Jupyter Notebook implementing and training the LSTM model.
- **Miscellaneous**:
  - `save_raw_signals.py`: Saves raw ECG data to CSV.
  - `convert_to_intervals.py`: Converts ECG signals into intervals for model input.


- **Requirments.txt**
---

## Setup Instructions

### 1. Hardware Setup
1. Connect the **AD8232 sensor** to the **ESP32 microcontroller** as specified in the project report.
2. Ensure proper electrode placement for accurate ECG signal acquisition.

### 2. Software Installation
1. Clone this repository:
   ```bash
   git clone <repository_url>
   cd <repository_name>
2. Install the required Python libraries:
   ```bash
   pip install -r requirements.txt
3. Connect the ESP32 microcontroller to your system via USB:
     1. Use tools like Thonny or ampy to upload the following scripts:
     2. ESP_final_code: Configures ESP32 for ECG data acquisition and processing.
     3. Flash the sketch onto the ESP32.

### 3. Model Deployement
  1. Start the Backend API
  Run the backend API to handle ECG data processing:
        ```bash
      python app.py
### 4. Mobile App Integration
1. Clone and Set Up the Mobile App
Clone the HeartSync mobile app from the HeartSync Mobile App Repository
      ```bash
      git clone https://github.com/maryamiqtidar/heart-sync-app
2. Install the required dependencies
     ```bash
     npm install
3. Add Process-data API Details to the Mobile App
    1. Open the instructions.tsx file in heart-sync-app/app/(tabs).
    2. Update the following details:Backend API URL: Replace the placeholder with the API URL for your backend (e.g., http://<your-backend-ip>:<port>/process-data).
    3. ESP32 IP Address: Add the IP address of your ESP32 device.
    ```bash
        #for process data
        const response = await axios.post(
        'http://<your-backend-ip>:<port>/process-data',
        dataToSend);
        #for ESP32
        const response = await fetch("http://<your-esp32-ip>/ecg", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.uid }),});
4. Add History API Details to the Mobile App
    1. Open the history.tsx file in heart-sync-app/app/(tabs).
    2. Update the following details:Backend API URL: Replace the placeholder with the API URL for your backend (e.g., http://<your-backend-ip>:<port>/...).
       ```bash
         const response = await fetch(
          `http://<your-backend-ip>:<port>/history?user_id=${userId}`,
          {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
            },
          }
        );
    
5. Now after these changes are made on the cmd run the command install the EXPO GO app from App Store
6. After the Installation is done on cmd run the following command
     ```bash
       npx expo start
7. Scan the QR code Generated on the Terminal and Now you will be able to Run mobile app smoothly and you can check your body electrolytes.
     

         
   


    




