/***************************************************
  Heart Rate Monitor with AD8232 and ESP32 DevKit V1
  This example uses the AD8232 sensor to read heart rate data.
  The AD8232 OUTPUT is connected to VP (GPIO 36) of the ESP32.

  Connections:
  AD8232   |   ESP32 DevKit V1
  ---------------------------
  3.3V     |   3.3V
  GND      |   GND
  OUTPUT   |   GPIO 36 (VP)
  LO+      |   GPIO 4 (D2)
  LO-      |   GPIO 2 (D4)

***************************************************/

void setup() {
  // Initialize serial communication at 115200 baud
  Serial.begin(1200);

  // Pin setup for leads off detection
  pinMode(23, INPUT); // LO+ connected to GPIO 4 (D2)
  pinMode(22, INPUT); // LO- connected to GPIO 2 (D4)
}

void loop() {
  // Check if leads are off
  if ((digitalRead(23) == 1) || (digitalRead(22) == 1)) {
    Serial.println('!');  // Print '!' if leads are off
  } else {
    // Read the analog value from the AD8232 OUTPUT pin connected to VP (GPIO 36)
    int heartRateValue = analogRead(36); // Read the ECG signal
    Serial.println(heartRateValue);  // Print the ECG signal value
  }

  // Wait for a short time to avoid saturating the serial communication
  delay(1);
}
