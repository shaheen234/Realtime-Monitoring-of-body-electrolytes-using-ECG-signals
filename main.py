import network
import ubluetooth
import time

class BLEProvisioning:
    def __init__(self):
        self.ble = ubluetooth.BLE()
        self.ble.active(True)
        self.ble.config(gap_name="ESP32-BLE-WiFi")
        self.ble.irq(self.ble_irq)
        self.conn_handle = None

        # Define service and characteristic UUIDs
        self.service_uuid = ubluetooth.UUID("12345678-1234-5678-1234-56789abcdef0")
        self.tx_char_uuid = ubluetooth.UUID("12345678-1234-5678-1234-56789abcdef1")
        self.rx_char_uuid = ubluetooth.UUID("12345678-1234-5678-1234-56789abcdef2")

        # Start the BLE service
        self.start_ble_service()

    def start_ble_service(self):
        # Define BLE service and characteristics
        service = (
            self.service_uuid,
            (
                (self.tx_char_uuid, ubluetooth.FLAG_READ | ubluetooth.FLAG_NOTIFY),
                (self.rx_char_uuid, ubluetooth.FLAG_WRITE),
            )
        )

        # Register the service
        ((self.tx_handle, self.rx_handle),) = self.ble.gatts_register_services([service])

        # Start advertising
        self.ble.gap_advertise(
            100,  # Advertising interval (ms)
            b'\x02\x01\x06' + b'\x03\x03\xef\xbe'
        )
        print("BLE advertising started")

    def ble_irq(self, event, data):
        if event == 1:  # Connection event
            self.conn_handle, _, _ = data
            print("BLE connected")
        elif event == 2:  # Disconnection event
            print("BLE disconnected")
            self.conn_handle = None
            self.start_ble_service()
        elif event == 3:  # GATT write event
            conn_handle, attr_handle = data
            if attr_handle == self.rx_handle:
                received_data = self.ble.gatts_read(self.rx_handle).decode('utf-8').strip()
                print(f"Received: {received_data}")
                self.process_received_data(received_data)

    def send_data(self, message):
        if self.conn_handle is not None:
            self.ble.gatts_notify(self.conn_handle, self.tx_handle, message.encode('utf-8'))

    def process_received_data(self, data):
        # Process Wi-Fi credentials
        if ":" in data:
            ssid, password = data.split(":", 1)
            print(f"SSID: {ssid}, Password: {password}")
            self.connect_to_wifi(ssid, password)

    def connect_to_wifi(self, ssid, password):
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(ssid, password)

        print("Connecting to Wi-Fi...")
        for _ in range(10):  # Wait up to 10 seconds for connection
            if wlan.isconnected():
                print("Connected to Wi-Fi!")
                self.send_data("Wi-Fi Connected")
                print("IP Address:", wlan.ifconfig()[0])
                return
            time.sleep(1)

        print("Failed to connect to Wi-Fi")
        self.send_data("Wi-Fi Connection Failed")

# Start BLE Provisioning
ble_prov = BLEProvisioning()
