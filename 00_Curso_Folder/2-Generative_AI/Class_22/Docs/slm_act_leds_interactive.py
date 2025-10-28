import ollama
import json
from monitor import collect_data, led_status, control_leds


def create_interactive_prompt(temp_dht, hum, temp_bmp, press, 
    button_state, ledRedSts, ledYlwSts, ledGrnSts, user_input):
	"""Create a prompt for interactive user commands and queries."""
	return f"""
You are an IoT system assistant controlling an environmental monitoring 
system with LED indicators.

CURRENT SYSTEM STATUS:
- DHT22: Temperature {temp_dht:.1f}°C, Humidity {hum:.1f}%
- BMP280: Temperature {temp_bmp:.1f}°C, Pressure {press:.2f}hPa
- Button: {"PRESSED" if button_state else "NOT PRESSED"}
- Red LED: {"ON" if ledRedSts else "OFF"}
- Yellow LED: {"ON" if ledYlwSts else "OFF"}
- Green LED: {"ON" if ledGrnSts else "OFF"}

USER REQUEST: "{user_input}"

INSTRUCTIONS:
You must analyze the user's request and respond with a JSON object 
containing two fields:

1. "message": A helpful text response to the user
2. "leds": LED control object with three boolean fields: 
"red_led", "yellow_led", "green_led"

EXAMPLES:

User: "what's the current temperature?"
Response: {{"message": "The current temperature is {temp_dht:.1f}°C from DHT22 and {temp_bmp:.1f}°C from BMP280.", "leds": {{"red_led": {str(ledRedSts).lower()}, "yellow_led": {str(ledYlwSts).lower()}, "green_led": {str(ledGrnSts).lower()}}}}}

User: "turn on the yellow led"
Response: {{"message": "Yellow LED turned on.", "leds": {{"red_led": false, "yellow_led": true, "green_led": false}}}}

User: "if temperature is above 20°C, turn on yellow led"
Response: {{"message": "Temperature is {temp_dht:.1f}°C, which is {'above' if temp_dht > 20 else 'below or equal to'} 20°C. {'Yellow LED turned on.' if temp_dht > 20 else 'No action taken.'}", "leds": {{"red_led": false, "yellow_led": {str(temp_dht > 20).lower()}, "green_led": {str(temp_dht <= 20).lower()}}}}}

User: "if button is pressed, turn on red led"
Response: {{"message": "Button is {'pressed' if button_state else 'not pressed'}. {'Red LED turned on.' if button_state else 'No action taken.'}", "leds": {{"red_led": {str(button_state).lower()}, "yellow_led": false, "green_led": {str(not button_state).lower()}}}}}

User: "turn on all leds"
Response: {{"message": "All LEDs turned on.", "leds": {{"red_led": true, "yellow_led": true, "green_led": true}}}}

User: "turn off all leds"
Response: {{"message": "All LEDs turned off.", "leds": {{"red_led": false, "yellow_led": false, "green_led": false}}}}

User: "will it rain?"
Response: {{"message": "Based on pressure of {press:.2f}hPa and humidity of {hum:.1f}%, [your analysis here]. LEDs unchanged.", "leds": {{"red_led": {str(ledRedSts).lower()}, "yellow_led": {str(ledYlwSts).lower()}, "green_led": {str(ledGrnSts).lower()}}}}}

User: "if button is pressed, switch (Change, Reverse) the led states"
Response: {{"message": "Button is {'pressed' if button_state else 'not pressed'}. {'LED states switched.' if button_state else 'No action taken.'}", "leds": {{"red_led": {str(not ledRedSts and button_state).lower()}, "yellow_led": {str(not ledYlwSts and button_state).lower()}, "green_led": {str(not ledGrnSts and button_state).lower()}}}}}

RULES:
- Always respond with valid JSON containing both "message" and "leds" fields
- If the user is just asking for information, keep the current LED states
- If the user gives a command, update the LED states accordingly
- If the command has a condition (if/when), evaluate it based on current sensor data
- Be conversational and helpful in your message
- Only ONE LED should be on at a time UNLESS the user explicitly asks for multiple LEDs

Respond with ONLY the JSON, no other text.
"""


def slm_inference(PROMPT, MODEL):
    response = ollama.generate(
    	model=MODEL, 
    	prompt=PROMPT
    	)
    return response


def parse_interactive_response(response_text):
    """Parse the interactive SLM JSON response."""
    try:
        # Clean the response
        response_text = response_text.strip()
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text
            response_text = response_text.replace('```json', '').replace('```', '').strip()
        
        # Parse JSON
        data = json.loads(response_text)
        
        # Extract message
        message = data.get('message', 'No response provided.')
        
        # Extract LED states
        leds = data.get('leds', {})
        red_led = leds.get('red_led', False)
        yellow_led = leds.get('yellow_led', False)
        green_led = leds.get('green_led', False)
        
        return message, (red_led, yellow_led, green_led)
    
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Response was: {response_text}")
        return "Error: Could not parse SLM response.", (False, False, False)


def display_system_status(temp_dht, hum, temp_bmp, press, button_state, ledRedSts, ledYlwSts, ledGrnSts):
    """Display comprehensive system status."""
    print("\n" + "="*60)
    print("SYSTEM STATUS")
    print("="*60)
    print(f"DHT22 Sensor:  Temp = {temp_dht:.1f}°C, Humidity = {hum:.1f}%")
    print(f"BMP280 Sensor: Temp = {temp_bmp:.1f}°C, Pressure = {press:.2f}hPa")
    print(f"Button:        {'PRESSED' if button_state else 'NOT PRESSED'}")
    print(f"\nLED Status:")
    print(f"  Red LED:    {'●' if ledRedSts else '○'} {'ON' if ledRedSts else 'OFF'}")
    print(f"  Yellow LED: {'●' if ledYlwSts else '○'} {'ON' if ledYlwSts else 'OFF'}")
    print(f"  Green LED:  {'●' if ledGrnSts else '○'} {'ON' if ledGrnSts else 'OFF'}")
    print("="*60)


def interactive_mode(MODEL):
    """Run the system in interactive mode accepting user commands."""
    print("\n" + "="*60)
    print("IoT Environmental Monitoring System - Interactive Mode")
    print(f"Using Model: {MODEL}")
    print("="*60)
    print("\nCommands you can try:")
    print("  - What's the current temperature?")
    print("  - What are the actual conditions?")
    print("  - Turn on the yellow LED")
    print("  - If temperature is above 20°C, turn on yellow LED")
    print("  - If button is pressed, turn on red LED")
    print("  - Turn on all LEDs")
    print("  - Turn off all LEDs")
    print("  - Will it rain based on current conditions?")
    print("  - Type 'status' to see system status")
    print("  - Type 'exit' or 'quit' to stop")
    print("="*60 + "\n")
    
    while True:
        # Get user input
        user_input = input("You: ").strip()
        
        if not user_input:
            continue
            
        if user_input.lower() in ['exit', 'quit', 'q']:
            print("\nExiting interactive mode. Goodbye!")
            break
        
        # Get current system status
        ledRedSts, ledYlwSts, ledGrnSts = led_status()
        temp_dht, hum, temp_bmp, press, button_state = collect_data()
        
        # Handle status command
        if user_input.lower() == 'status':
            display_system_status(temp_dht, hum, temp_bmp, press, button_state, 
                                ledRedSts, ledYlwSts, ledGrnSts)
            continue
        
        # Check if sensor data is valid
        if any(v is None for v in [temp_dht, hum, temp_bmp, press]):
            print("Assistant: Error - Unable to read sensor data. Please try again.")
            continue
        
        # Create prompt with user input
        PROMPT = create_interactive_prompt(temp_dht, hum, temp_bmp, press, button_state,
                                          ledRedSts, ledYlwSts, ledGrnSts, user_input)
        
        # Get SLM response
        print("Assistant: [Thinking...]")
        response = slm_inference(PROMPT, MODEL)
        
        # Parse response
        message, (red, yellow, green) = parse_interactive_response(response['response'])
        
        # Display assistant's message
        print(f"Assistant: {message}")
        
        # Control LEDs based on response
        control_leds(red, yellow, green)
        
        # Display updated system status
        ledRedSts, ledYlwSts, ledGrnSts = led_status()
        print(f"\nLED Update: Red={'ON' if ledRedSts else 'OFF'}, "
              f"Yellow={'ON' if ledYlwSts else 'OFF'}, "
              f"Green={'ON' if ledGrnSts else 'OFF'}\n")


if __name__ == "__main__":
    MODEL = 'llama3.2:3b'  # Use 3b model for better instruction following
    
    # Run in interactive mode
    interactive_mode(MODEL)
