import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, butter, filtfilt

def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    y = filtfilt(b, a, data)
    return y

# Read data from CSV
file_path = 'ecg_data2.csv'  # Update this to your CSV file path
df = pd.read_csv(file_path)
ecg_data = df['ECG Value'].values

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

# Output results
print("RR Intervals (ms):", rr_intervals)
print("PR Intervals (ms):", pr_intervals)
print("QRS Durations (ms):", qrs_durations)
print("QT Intervals (ms):", qt_intervals)
print("QTc Intervals (ms):", [qtc * 1000 for qtc in qtc_intervals])  # Convert QTc to milliseconds
print("P Wave Axis (degrees):", p_wave_axis)
print("QRS Axis (degrees):", qrs_axis)
print("T Wave Axis (degrees):", t_wave_axis)
