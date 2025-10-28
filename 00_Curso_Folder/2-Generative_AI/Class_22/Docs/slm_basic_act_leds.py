import ollama
from monitor import collect_data, led_status, control_leds


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

def slm_inference(PROMPT, MODEL):
    response = ollama.generate(
    	model=MODEL, 
    	prompt=PROMPT
    	)
    return response


def parse_llm_response(response_text):
    """Parse the LLM response to extract LED control instructions."""
    response_lower = response_text.lower()
    red_led = 'activate red led' in response_lower
    yellow_led = 'activate yellow led' in response_lower
    green_led = 'activate green led' in response_lower
    return (red_led, yellow_led, green_led)


def output_actuator(response, MODEL):
    print(f"\nSmart IoT Actuator using {MODEL} model\n")
    
    print(f"SYSTEM REAL DATA")
    print(f" - DHT22 ==> Temp: {temp_dht:.1f}°C, Humidity: {hum:.1f}%")
    print(f" - BMP280 => Temp: {temp_bmp:.1f}°C, Pressure: {press:.2f}hPa")
    print(f" - Button {'pressed' if button_state else 'not pressed'}")
    
    print(f"\n>> {MODEL} Response: {response['response']}")
    
    # Control LEDs based on response
    red, yellow, green = parse_llm_response(response['response'])
    control_leds(red, yellow, green)
    
    print(f"\nSYSTEM ACTUATOR STATUS")
    ledRedSts, ledYlwSts, ledGrnSts  = led_status()
    print(f" - Red LED {'is on' if ledRedSts else 'is off'}")
    print(f" - Yellow LED {'is on' if ledYlwSts else 'is off'}")
    print(f" - Green LED {'is on' if ledGrnSts else 'is off'}")


if __name__ == "__main__":

MODEL = 'llama3.2:3b'
PROMPT = prompt

# Get system info
ledRedSts, ledYlwSts, ledGrnSts  = led_status()
temp_dht, hum, temp_bmp, press, button_state  = collect_data()

# Analyse and actuate on LEDs
response = slm_inference(PROMPT, MODEL)
output_actuator(response, MODEL)


