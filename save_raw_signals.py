import serial
import csv
from datetime import datetime

# Set up the serial connection (the COM port may vary)
ser = serial.Serial('COM4', 750)  # Change 'COM3' to whatever port your Arduino is connected to

# Open or create a CSV file
with open('ecg_data2.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Timestamp', 'ECG Value'])  # Write header

    try:
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                # Read the line from serial
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Get the current time
                writer.writerow([timestamp, line])  # Write timestamp and ECG value
    except KeyboardInterrupt:
        print("Data collection stopped by user")
        ser.close()  # Close serial port
