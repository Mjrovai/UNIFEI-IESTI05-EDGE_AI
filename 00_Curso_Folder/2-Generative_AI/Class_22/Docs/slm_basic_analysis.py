import ollama
from monitor import collect_data, led_status

ledRedSts, ledYlwSts, ledGrnSts  = led_status()
temp_dht, hum, temp_bmp, press, button_state  = collect_data()

prompt = f"""
		You are an experienced environmental scientist. 
		Analyze the information received from an IoT system:

		DHT22 Temp: {temp_dht:.1f}°C and Humidity: {hum:.1f}%
		BMP280 Temp: {temp_bmp:.1f}°C and Pressure: {press:.2f}hPa
		Button {"pressed" if button_state else "not pressed"}
		Red LED {"is on" if ledRedSts else "is off"}
		Yellow LED {"is on" if ledYlwSts else "is off"}
		Green LED {"is on" if ledGrnSts else "is off"}

		Where,
		- The button, not pressed, shows a normal operation
		- The button, when pressed, shows an emergency
		- Red LED when is on, indicates a problem/emergency.
		- Yellow LED when is on indicates a warning situation.
		- Green LED when is on, indicates system is OK.

		If the temperature is over 20°C, mean a warning situation

		You should answer only with: "Activate Red LED" or "Activate Yellow LED" or "Activate Green LED"

"""

MODEL = 'llama3.2:3b'
PROMPT = prompt

response = ollama.generate(
	model=MODEL, 
	prompt=PROMPT
	)

print(f"\nSmart IoT Analyser using {MODEL} model\n")

print(f"SYSTEM REAL DATA")
print(f" - DHT22 ==> Temp: {temp_dht:.1f}°C, Humidity: {hum:.1f}%")
print(f" - BMP280 => Temp: {temp_bmp:.1f}°C, Pressure: {press:.2f}hPa")
print(f" - Button {'pressed' if button_state else 'not pressed'}")
print(f" - Red LED {'is on' if ledRedSts else 'is off'}")
print(f" - Yellow LED {'is on' if ledYlwSts else 'is off'}")
print(f" - Green LED {'is on' if ledGrnSts else 'is off'}")

print(f"\n>> {MODEL} Response: {response['response']}")

