# Real IoT Starter

## ESP32
Open `esp32_guardian.ino` in Arduino IDE, set Wi-Fi and the PC's LAN IP, then flash the board. Replace the analog readers with calibrated temperature/vibration/pressure sensors.

## PC simulator
Start FastAPI, then run:
`python iot/gateway_simulator.py --machine M1 --seconds 20`

To demonstrate a deterioration event:
`python iot/gateway_simulator.py --machine M1 --seconds 20 --risk-mode`

The API response contains the ML risk and the Guardian Maintenance Agent decision.
