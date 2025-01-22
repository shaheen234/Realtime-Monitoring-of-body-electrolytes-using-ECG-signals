import network
import socket
import ujson
import urequests
import time
import machine
import os  # For file handling

# Firebase Configuration
FIREBASE_HOST = "https://electrolyte-eb1bc-default-rtdb.firebaseio.com"
FIREBASE_AUTH = "6Y45koNKRiHOg01It9w2tPyMBNoiFVmMsuBnYdPi"

# ADC Configuration for AD8232 ECG Sensor
adc = machine.ADC(machine.Pin(32))  # ECG signal pin
adc.atten(machine.ADC.ATTN_11DB)  # Full range: 0 - 3.3V
adc.width(machine.ADC.WIDTH_12BIT)  # 12-bit resolution (0-4095)

# WiFi Credentials File
WIFI_CONFIG_FILE = "wifi_config.json"


# Utility Functions
def load_wifi_credentials():
    """Load WiFi credentials from a JSON file."""
    try:
        if WIFI_CONFIG_FILE in os.listdir():
            with open(WIFI_CONFIG_FILE, "r") as f:
                credentials = ujson.load(f)
                print(f"[INFO] Loaded WiFi credentials: {credentials}")
                return credentials.get("ssid"), credentials.get("password")
        else:
            print("[INFO] No WiFi configuration file found.")
            return None, None
    except Exception as e:
        print(f"[ERROR] Failed to load WiFi credentials: {e}")
        return None, None


def save_wifi_credentials(ssid, password):
    """Save WiFi credentials to a JSON file."""
    try:
        with open(WIFI_CONFIG_FILE, "w") as f:
            ujson.dump({"ssid": ssid, "password": password}, f)
            print("[INFO] WiFi credentials saved.")
    except Exception as e:
        print(f"[ERROR] Failed to save WiFi credentials: {e}")


def connect_to_wifi(ssid, password):
    """Connect ESP32 to WiFi."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    print(f"[INFO] Connecting to WiFi: {ssid}")
    wlan.connect(ssid, password)

    retries = 10  # Number of retries before giving up
    while not wlan.isconnected() and retries > 0:
        print(f"[DEBUG] Waiting for connection... ({10 - retries + 1}/10)")
        time.sleep(1)
        retries -= 1

    if wlan.isconnected():
        print(f"[INFO] Connected to WiFi. IP Address: {wlan.ifconfig()[0]}")
        return True
    else:
        print("[ERROR] Failed to connect to WiFi.")
        return False


def start_wifi_configuration_mode():
    """Start a web server to configure WiFi credentials."""
    print("[INFO] Entering WiFi configuration mode...")
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="ESP32_Config", password="12345678")
    print("[INFO] Access Point started. SSID: ESP32_Config, Password: 12345678")

    server = socket.socket()
    server.bind(addr)
    server.listen(1)
    print(f"[INFO] WiFi configuration server started on {addr}")

    while True:
        conn, addr = server.accept()
        print(f"[INFO] Connection from {addr}")
        try:
            request = conn.recv(1024).decode()
            print("[DEBUG] HTTP Request:", request)

            if "POST /configure" in request:
                try:
                    payload = request.split("\r\n\r\n")[1]
                    if not payload:
                        raise ValueError("Empty request payload")
                    data = ujson.loads(payload)
                    ssid = data.get("ssid")
                    password = data.get("password")
                    if not ssid or not password:
                        raise ValueError("SSID or Password is missing.")

                    # Save WiFi credentials
                    save_wifi_credentials(ssid, password)
                    conn.send("HTTP/1.1 200 OK\r\n\r\nConfiguration saved. Restarting...")
                    print("[INFO] WiFi credentials configured. Restarting...")
                    time.sleep(2)
                    machine.reset()
                except Exception as e:
                    print(f"[ERROR] Failed to configure WiFi: {e}")
                    conn.send("HTTP/1.1 400 Bad Request\r\n\r\nInvalid configuration.")
            else:
                html = """<!DOCTYPE html>
                <html>
                <body>
                    <h1>Configure WiFi</h1>
                    <form method="POST" action="/configure">
                        SSID: <input type="text" name="ssid"><br><br>
                        Password: <input type="password" name="password"><br><br>
                        <input type="submit" value="Save">
                    </form>
                </body>
                </html>
                """
                conn.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + html)
        except Exception as e:
            print(f"[ERROR] Error handling connection: {e}")
        finally:
            conn.close()


# ECG and Firebase Functions
def capture_ecg():
    """Capture ECG data for 10 seconds."""
    print("[INFO] Starting ECG data capture for 10 seconds...")
    ecg_values = []
    start_time = time.time()

    while time.time() - start_time < 10:
        try:
            value = adc.read()
            ecg_values.append(value)
        except Exception as e:
            print(f"[ERROR] Error reading ECG data: {e}")
            break
        time.sleep(0.004)  # 250 Hz sampling rate

    print(f"[INFO] ECG data capture complete. {len(ecg_values)} samples captured.")
    return ecg_values


def send_to_firebase(user_id, ecg_values):
    """Send ECG data to Firebase."""
    url = f"{FIREBASE_HOST}/users/{user_id}/ecg_data/entries.json"
    payload = {
        "timestamp": time.time(),
        "ecg_values": ecg_values
    }
    print(f"[INFO] Sending data to Firebase: {url}")
    try:
        response = urequests.post(url, json=payload)
        print(f"[INFO] Firebase Response: {response.status_code} - {response.text}")
        response.close()
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] Failed to send data to Firebase: {e}")
        return False


def start_webserver():
    """Start a web server for handling ECG capture requests."""
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    try:
        # Create and configure the server socket
        server = socket.socket()
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow reusing the address
        server.bind(addr)
        server.listen(5)
        print(f"[INFO] Web server started on {addr}")

        while True:
            try:
                # Accept incoming client connection
                conn, client_addr = server.accept()
                print(f"[INFO] Connection from {client_addr}")

                # Handle the client's request in a separate function
                handle_request(conn)
            except Exception as e:
                print(f"[ERROR] Error accepting connection: {e}")
    except Exception as e:
        print(f"[ERROR] Error starting web server: {e}")
    finally:
        server.close()
        print("[INFO] Web server socket closed.")

def handle_request(conn):
    """Handle incoming HTTP requests."""
    try:
        request = conn.recv(1024).decode()  # Receive the HTTP request
        print("[DEBUG] HTTP Request:", request)

        if "POST /ecg" in request:
            try:
                # Parse the request payload
                payload = request.split("\r\n\r\n")[1]
                if not payload:
                    raise ValueError("Empty request payload")

                data = ujson.loads(payload)  # Parse JSON payload
                user_id = data.get("user_id", "Unknown")
                print(f"[INFO] Triggering ECG capture for User ID: {user_id}")

                # Simulate ECG data capture and Firebase upload
                ecg_values = capture_ecg()
                if not ecg_values:
                    raise ValueError("Captured ECG data is empty.")

                success = send_to_firebase(user_id, ecg_values)

                # Send response to the client
                if success:
                    response_data = {"status": "success", "user_id": user_id}
                    conn.send(
                        "HTTP/1.1 200 OK\r\n"
                        "Content-Type: application/json\r\n"
                        "Connection: close\r\n\r\n" +
                        ujson.dumps(response_data)
                    )
                else:
                    conn.send(
                        "HTTP/1.1 500 Internal Server Error\r\n"
                        "Connection: close\r\n\r\n"
                    )
            except Exception as e:
                print(f"[ERROR] Error processing POST /ecg request: {e}")
                conn.send(
                    "HTTP/1.1 400 Bad Request\r\n"
                    "Connection: close\r\n\r\n"
                )
        else:
            # Handle unknown routes
            conn.send(
                "HTTP/1.1 404 Not Found\r\n"
                "Connection: close\r\n\r\n"
            )
    except Exception as e:
        print(f"[ERROR] Error handling request: {e}")
    finally:
        conn.close()  # Ensure the connection is closed after handling
        print("[INFO] Connection closed.")



# Main Execution Logic
try:
    ssid, password = load_wifi_credentials()

    if ssid and password:
        if connect_to_wifi(ssid, password):
            print("[INFO] Starting web server...")
            start_webserver()
        else:
            print("[ERROR] WiFi connection failed. Entering configuration mode...")
            start_wifi_configuration_mode()
    else:
        print("[INFO] No WiFi credentials found. Entering configuration mode...")
        start_wifi_configuration_mode()
except Exception as e:
    print(f"[ERROR] Unexpected error: {e}")