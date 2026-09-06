// AI Industrial Guardian - ESP32 telemetry starter
// Sensors can be replaced with real industrial transmitters/ADC modules.
// Sends JSON to FastAPI: POST /api/v1/telemetry/{machine_id}
#include <WiFi.h>
#include <HTTPClient.h>

const char* WIFI_SSID = "YOUR_WIFI";
const char* WIFI_PASSWORD = "YOUR_PASSWORD";
const char* API_URL = "http://192.168.1.100:8000/api/v1/telemetry/M1";

float readTemperature(){ return 25.0 + (analogRead(34) / 4095.0) * 90.0; }
float readVibration(){ return (analogRead(35) / 4095.0) * 2.0; }
float readPressure(){ return 20.0 + (analogRead(32) / 4095.0) * 40.0; }

void setup(){
  Serial.begin(115200); WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while(WiFi.status()!=WL_CONNECTED){ delay(500); Serial.print('.'); }
  Serial.println("\nGuardian IoT connected");
}
void loop(){
  if(WiFi.status()==WL_CONNECTED){
    HTTPClient http; http.begin(API_URL); http.addHeader("Content-Type","application/json");
    String body = String("{\"temp\":") + String(readTemperature(),1) +
      String(",\"vibration\":") + String(readVibration(),2) +
      String(",\"pressure\":") + String(readPressure(),1) + String("}");
    int code=http.POST(body); Serial.printf("Telemetry HTTP %d: %s\n",code,body.c_str()); http.end();
  }
  delay(5000);
}
