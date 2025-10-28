import ollama
import json
from monitor import collect_data, led_status, control_leds


def create_prompt(temp_dht, hum, temp_bmp, press, button_state, ledRedSts, ledYlwSts, ledGrnSts, TEMP_THRESHOLD):
	"""Create a prompt for the LLM with current sensor data."""
	return f"""
You are controlling an IoT LED system. Analyze the sensor data and decide which ONE LED to activate.

SENSOR DATA:
- DHT22 Temperature: {temp_dht:.1f}°C
- BMP280 Temperature: {temp_bmp:.1f}°C
- Humidity: {hum:.1f}%
- Pressure: {press:.2f}hPa
- Button: {"PRESSED" if button_state else "NOT PRESSED"}

TEMPERATURE THRESHOLD: {TEMP_THRESHOLD}°C

DECISION RULES (apply in this priority order):
1. IF button is PRESSED → Activate Red LED (EMERGENCY - highest priority)
2. IF button is NOT PRESSED AND (DHT22 temp > {TEMP_THRESHOLD}°C OR BMP280 temp > {TEMP_THRESHOLD}°C) → Activate Yellow LED (WARNING)
3. IF button is NOT PRESSED AND (DHT22 temp ≤ {TEMP_THRESHOLD}°C AND BMP280 temp ≤ {TEMP_THRESHOLD}°C) → Activate Green LED (NORMAL)

CURRENT ANALYSIS:
- Button status: {"PRESSED" if button_state else "NOT PRESSED"}
- DHT22 temp ({temp_dht:.1f}°C) is {"OVER" if temp_dht > TEMP_THRESHOLD else "AT OR BELOW"} threshold ({TEMP_THRESHOLD}°C)
- BMP280 temp ({temp_bmp:.1f}°C) is {"OVER" if temp_bmp > TEMP_THRESHOLD else "AT OR BELOW"} threshold ({TEMP_THRESHOLD}°C)

Based on these rules, respond with ONLY a JSON object (no other text):
{{"red_led": true, "yellow_led": false, "green_led": false}}

Only ONE LED should be true, the other two must be false.
"""

def slm_inference(PROMPT, MODEL):
    response = ollama.generate(
    	model=MODEL, 
    	prompt=PROMPT
    	)
    return response


def parse_llm_response(response_text):
    """Parse the LLM JSON response to extract LED control instructions."""
    try:
        # Clean the response - remove any markdown code blocks if present
        response_text = response_text.strip()
        if response_text.startswith('```'):
            # Extract JSON from markdown code block
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text
        
        # Parse JSON
        data = json.loads(response_text)
        red_led = data.get('red_led', False)
        yellow_led = data.get('yellow_led', False)
        green_led = data.get('green_led', False)
        return (red_led, yellow_led, green_led)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Response was: {response_text}")
        # Fallback to safe state (all LEDs off)
        return (False, False, False)


def output_actuator(response, MODEL, temp_dht, hum, temp_bmp, press, button_state):
    print(f"\nSmart IoT Actuator using {MODEL} model\n")
    
    print(f"SYSTEM REAL DATA")
    print(f" - DHT22 ==> Temp: {temp_dht:.1f}°C, Humidity: {hum:.1f}%")
    print(f" - BMP280 => Temp: {temp_bmp:.1f}°C, Pressure: {press:.2f}hPa")
    print(f" - Button {'pressed' if button_state else 'not pressed'}")
    
    print(f"\n>> {MODEL} Response: {response['response']}")
    
    # Parse LLM response and use it directly (no validation)
    red, yellow, green = parse_llm_response(response['response'])
    print(f">> SLM decision: Red={red}, Yellow={yellow}, Green={green}")
    
    # Control LEDs based on SLM decision
    control_leds(red, yellow, green)
    
    print(f"\nSYSTEM ACTUATOR STATUS")
    ledRedSts, ledYlwSts, ledGrnSts  = led_status()
    print(f" - Red LED {'is on' if ledRedSts else 'is off'}")
    print(f" - Yellow LED {'is on' if ledYlwSts else 'is off'}")
    print(f" - Green LED {'is on' if ledGrnSts else 'is off'}")


def slm_analyse_act(MODEL, TEMP_THRESHOLD):
    """Main function to get sensor data, run SLM inference, and actuate LEDs."""
    # Get system info
    ledRedSts, ledYlwSts, ledGrnSts  = led_status()
    temp_dht, hum, temp_bmp, press, button_state  = collect_data()
    
    # Create prompt with current sensor data
    PROMPT = create_prompt(temp_dht, 
                           hum, 
                           temp_bmp, 
                           press, 
                           button_state, 
                           ledRedSts, 
                           ledYlwSts, 
                           ledGrnSts,
                           TEMP_THRESHOLD)
    
    # Analyse and actuate on LEDs
    response = slm_inference(PROMPT, MODEL)
    output_actuator(response, MODEL, temp_dht, hum, temp_bmp, press, button_state)


if __name__ == "__main__":

	MODEL = 'llama3.2:3b'
	TEMP_THRESHOLD = 25.0

	# Run the SLM analysis and actuation
	slm_analyse_act(MODEL, TEMP_THRESHOLD)




