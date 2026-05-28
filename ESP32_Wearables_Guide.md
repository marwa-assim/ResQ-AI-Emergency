# ResQ AI - ESP32 Wearable Integration Guide

This guide explains how to connect custom ESP32 wearables (using MAX30102 for Heart Rate/SpO2 and MPU6050 for fall detection) directly to the ResQ AI ER system.

## 1. Hardware Required
- **ESP32 Microcontroller** (e.g., ESP32-WROOM-32)
- **MAX30102** Pulse Oximeter & Heart Rate Sensor
- **MPU6050** Accelerometer & Gyroscope (for fall detection)
- Battery Pack (LiPo)

## 2. API Endpoint configuration
The ER system exposes an IoT webhook that the ESP32 should `POST` to. 

**Endpoint**: `http://<SERVER_IP>:5000/api/iot/webhook`  
**Method**: `POST`  
**Headers**: `Content-Type: application/json`

### Payload Format
```json
{
    "device_id": "ESP32_MAC_ADDRESS_HERE",
    "vitals": {
        "hr": 85,
        "spo2": 98
    },
    "alert": "Optional critical alert message (e.g., Fall Detected)",
    "lat": 26.2235,
    "lng": 50.5876
}
```

## 3. Sample Arduino IDE Code (C++)

```cpp
#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Point this to your machine's local IP address or cloud domain
const char* serverName = "http://192.168.1.X:5000/api/iot/webhook"; 
String macAddress = "";

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  
  while(WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  macAddress = WiFi.macAddress();
  Serial.println("Connected! MAC: " + macAddress);
  
  // Initialize Sensors here (MAX30102 & MPU6050)
}

void loop() {
  if(WiFi.status() == WL_CONNECTED){
    HTTPClient http;
    http.begin(serverName);
    http.addHeader("Content-Type", "application/json");
    
    // Read real values from your sensors
    int heartRate = 80; 
    int spo2 = 97;
    bool fallDetected = false;
    
    String jsonPayload = "{\"device_id\":\"" + macAddress + "\",\"vitals\":{\"hr\":" + String(heartRate) + ",\"spo2\":" + String(spo2) + "}}";
    
    if (fallDetected) {
      jsonPayload = "{\"device_id\":\"" + macAddress + "\",\"alert\":\"Fall Detected\",\"vitals\":{\"hr\":" + String(heartRate) + ",\"spo2\":" + String(spo2) + "}}";
    }
    
    int httpResponseCode = http.POST(jsonPayload);
    Serial.print("HTTP Response code: ");
    Serial.println(httpResponseCode);
    
    http.end();
  }
  
  delay(5000); // Send data every 5 seconds
}
```

## 4. Registering the Device
1. Log into the ResQ Admin Dashboard as `superadmin`.
2. Navigate to **Administration > IoT Wearables**.
3. (In Phase 2) Use the "Provision Device" button to register the MAC address and assign it to a Patient CPR.
4. Telemetry and critical drops (e.g. SpO2 < 90) will now trigger instant dashboard alerts and SMS notifications to emergency contacts.
