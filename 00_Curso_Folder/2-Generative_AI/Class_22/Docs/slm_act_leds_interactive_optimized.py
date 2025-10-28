import ollama
import json
from monitor import collect_data, led_status, control_leds


# System message that defines the assistant's behavior (sent once at initialization)
SYSTEM_MESSAGE = """You are an IoT assistant controlling an environmental monitoring system with LEDs.

Respond with JSON only:
{"message": "your helpful response", "leds": {"red_led": bool, "yellow_led": bool, "green_led": bool}}

RULES:
- Information queries: keep current LED states unchanged
- LED commands: update LEDs as requested
- Conditional commands (if/when): evaluate condition from sensor data first
- Only ONE LED should be on at a time UNLESS user explicitly says "all"
- Be concise and conversational

Always respond with valid JSON containing both "message" and "leds" fields."""


def create_interactive_prompt(temp_dht, hum, temp_bmp, press, 
                             button_state, ledRedSts, ledYlwSts, ledGrnSts, user_input):
    """Create a compact prompt for interactive user commands and queries (optimized version)."""
    return f"""STATUS: DHT22={temp_dht:.1f}°C/{hum:.1f}% BMP280={temp_bmp:.1f}°C/{press:.2f}hPa Button={'PRESSED' if button_state else 'OFF'} LEDs:R={'ON' if ledRedSts else 'OFF'}/Y={'ON' if ledYlwSts else 'OFF'}/G={'ON' if ledGrnSts else 'OFF'}

USER: {user_input}"""


def slm_inference(messages, MODEL):
    """Send chat request to Ollama using chat API (optimized version)."""
    response = ollama.chat(
        model=MODEL,
        messages=messages
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


def preload_model(MODEL):
    """Pre-load the model into memory to avoid loading delays."""
    print(f"Pre-loading model {MODEL}...")
    try:
        ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": "hi"}]
        )
        print(f"Model {MODEL} loaded successfully!\n")
    except Exception as e:
        print(f"Warning: Could not pre-load model: {e}")
        print("Model will load on first use.\n")


def interactive_mode(MODEL):
    """Run the system in interactive mode accepting user commands."""
    print("\n" + "="*60)
    print("IoT Environmental Monitoring System - Interactive Mode")
    print(f"Using Model: {MODEL} (Optimized)")
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
    
    # Pre-load model
    preload_model(MODEL)
    
    # Initialize conversation with system message (sent only once)
    messages = [
        {
            "role": "system",
            "content": SYSTEM_MESSAGE
        }
    ]
    
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
        
        # Handle status command locally (no need for LLM)
        if user_input.lower() == 'status':
            display_system_status(temp_dht, hum, temp_bmp, press, button_state, 
                                ledRedSts, ledYlwSts, ledGrnSts)
            continue
        
        # Check if sensor data is valid
        if any(v is None for v in [temp_dht, hum, temp_bmp, press]):
            print("Assistant: Error - Unable to read sensor data. Please try again.")
            continue
        
        # Create compact user message with current status
        user_message_content = create_interactive_prompt(
            temp_dht, hum, temp_bmp, press, button_state,
            ledRedSts, ledYlwSts, ledGrnSts, user_input
        )
        
        messages.append({
            "role": "user",
            "content": user_message_content
        })
        
        # Get SLM response using chat API
        print("Assistant: [Thinking...]")
        response = slm_inference(messages, MODEL)
        
        # Parse response
        assistant_content = response['message']['content']
        message, (red, yellow, green) = parse_interactive_response(assistant_content)
        
        # Add assistant's response to conversation history
        messages.append({
            "role": "assistant",
            "content": assistant_content
        })
        
        # Display assistant's message
        print(f"Assistant: {message}")
        
        # Control LEDs based on response
        control_leds(red, yellow, green)
        
        # Display updated system status
        ledRedSts, ledYlwSts, ledGrnSts = led_status()
        print(f"\nLED Update: Red={'ON' if ledRedSts else 'OFF'}, "
              f"Yellow={'ON' if ledYlwSts else 'OFF'}, "
              f"Green={'ON' if ledGrnSts else 'OFF'}\n")
        
        # Keep conversation history manageable (last 8 messages = 4 exchanges)
        # Keep system message + recent conversation
        if len(messages) > 9:  # system message + 8 user/assistant messages
            messages = [messages[0]] + messages[-8:]


if __name__ == "__main__":
    MODEL = 'llama3.2:3b'  # Same model, optimized usage
    
    # Run in interactive mode
    interactive_mode(MODEL)
