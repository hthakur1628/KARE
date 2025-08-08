# ESP8266 Temperature Sensor Setup

## Required Libraries
Install these libraries through Arduino IDE Library Manager:

1. **ESP8266WiFi** (built-in with ESP8266 board package)
2. **ESP8266HTTPClient** (built-in with ESP8266 board package)
3. **OneWire** by Jim Studt
4. **DallasTemperature** by Miles Burton
5. **ArduinoJson** by Benoit Blanchon (version 6.x)

## Hardware Connections

### DS18B20 Temperature Sensor Wiring:
- **VCC** → 3.3V on ESP8266
- **GND** → GND on ESP8266  
- **DATA** → GPIO2 (D4 pin on NodeMCU)
- **4.7kΩ pull-up resistor** between VCC and DATA lines

### Pin Configuration:
```
ESP8266 GPIO2 (D4) ←→ DS18B20 DATA pin
ESP8266 3.3V       ←→ DS18B20 VCC
ESP8266 GND        ←→ DS18B20 GND
```

## Configuration Steps

1. **Update WiFi Credentials:**
   ```cpp
   const char* ssid = "YOUR_WIFI_SSID";
   const char* password = "YOUR_WIFI_PASSWORD";
   ```

2. **Update Server URL:**
   ```cpp
   const char* serverURL = "http://your-server.com/device";
   ```

3. **Adjust Reading Interval (optional):**
   ```cpp
   const unsigned long readingInterval = 30000; // 30 seconds
   ```

## Features

- **Automatic WiFi connection** with reconnection handling
- **NTP time synchronization** for accurate timestamps
- **Temperature reading** from DS18B20 sensor
- **JSON payload creation** matching your server format
- **HTTP POST** to your healthcare server
- **Error handling** for sensor disconnection and network issues
- **Serial monitoring** for debugging

## JSON Output Format
The sensor sends data in this format:
```json
{
  "device_id": "ESP8266-ABC123",
  "timestamp": "2025-08-05T02:31:00Z",
  "data": {
    "temperature_f": 98.2,
    "heart_rate_bpm": 0,
    "spo2_percent": 0,
    "ecg_mV": []
  }
}
```

## Device Linking Requirement

**IMPORTANT:** Before the ESP8266 can send data successfully, the device must be linked to a user account:

### Option 1: Using the Web App
1. **Get Device ID:** Check the serial monitor for the device ID (currently set to "ESP8266-1234")
2. **Link Device:** Log into the healthcare web app and use the device linking feature
3. **Verify Connection:** Once linked, the device data will be saved and appear in your dashboard

### Option 2: Using the Command Line Script
1. **List Users:** Run `python list_users.py` in the backend directory to see available users
2. **Link Device:** Run `python link_esp8266_device.py <user_email> ESP8266-1234`
3. **Example:** `python link_esp8266_device.py john.doe@example.com ESP8266-1234`

## Notes
- **Simplified Code:** Removed excess functions and verbose logging
- **Temperature in Fahrenheit:** Sensor readings are converted and sent in °F
- **Auto Device ID:** Generated using ESP8266 chip ID (format: ESP8266-XXXXXX)
- **Minimal Placeholders:** Heart rate, SpO2, and ECG fields set to 0/empty
- **30-second intervals:** Temperature readings every 30 seconds
- **UTC timestamps:** All timestamps in ISO 8601 UTC format
- **Device linking required:** Must be linked to user account before data is saved