#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <OneWire.h> ///
#include <DallasTemperature.h> ///
#include <ArduinoJson.h>///
#include <time.h>

// WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Server configuration
const char* serverURL = "http://10.30.29.183:5001/device";

// DS18B20 configuration
#define ONE_WIRE_BUS 2  // GPIO2 (D4 on NodeMCU)

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// Device configuration
String deviceId = "ESP8266-1234" ;

// Timing
unsigned long lastReading = 0;
const unsigned long readingInterval = 30000; // 30 seconds

void setup() {
  Serial.begin(115200);
  Serial.println("Healthcare Temperature Monitor Starting...");
  
  sensors.begin();
  
  // Connect to WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected!");
  
  // Initialize time
  configTime(0, 0, "pool.ntp.org");
  while (time(nullptr) < 8 * 3600 * 2) {
    delay(500);
  }
  
  // Print device info
  Serial.println("\n=== DEVICE INFO ===");
  Serial.println("Device ID: " + deviceId);
  Serial.println("Link this device in your healthcare app");
  Serial.println("===================\n");
}

void loop() {
  if (millis() - lastReading >= readingInterval) {
    readAndSendTemperature();
    lastReading = millis();
  }
  delay(600000);
}

void readAndSendTemperature() {
  sensors.requestTemperatures();
  float tempC = sensors.getTempCByIndex(0);
  
  if (tempC == DEVICE_DISCONNECTED_C) {
    Serial.println("Sensor error!");
    return;
  }
  
  // Convert to Fahrenheit
  float tempF = (tempC * 9.0 / 5.0) + 32.0;
  
  Serial.print("Temperature: ");
  Serial.print(tempF, 1);
  Serial.println("°F");
  
  // Create JSON payload
  DynamicJsonDocument doc(512);
  doc["device_id"] = deviceId;
  
  // Add timestamp
  time_t now = time(nullptr);
  struct tm* timeinfo = gmtime(&now);
  char timestamp[32];
  strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", timeinfo);
  doc["timestamp"] = timestamp;
  
  // Add temperature data in Fahrenheit
  JsonObject data = doc.createNestedObject("data");
  data["temperature_f"] = round(tempF * 10) / 10.0;
  data["heart_rate_bpm"] = 0;
  data["spo2_percent"] = 0;
  data.createNestedArray("ecg_mV");
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  // Send to server
  if (WiFi.status() == WL_CONNECTED) {
    WiFiClient client;
    HTTPClient http;
    
    http.begin(client, serverURL);
    http.addHeader("Content-Type", "application/json");
    
    int responseCode = http.POST(jsonString);
    
    if (responseCode == 200) {
      Serial.println("✓ Data sent successfully");
    } else {
      Serial.println("✗ Send failed: " + String(responseCode));
    }
    
    http.end();
  }
}