import ollama
from pydantic import BaseModel, Field
from monitor import collect_data, led_status, control_leds


# Pydantic models for structured output
class LEDControl(BaseModel):
    """LED control configuration."""
    red_led: bool = Field(description="Red LED state (on/off)")
    yellow_led: bool = Field(description="Yellow LED state (on/off)")
    green_led: bool = Field(description="Green LED state (on/off)")


class AssistantResponse(BaseModel):
    """Complete assistant response with message and LED control."""
    message: str = Field(description="Helpful response to the user")
    leds: LEDControl = Field(description="LED control configuration")


# System message that defines the assistant's behavior (sent once at initialization)
SYSTEM_MESSAGE = """You are an IoT assistant controlling an environmental monitoring system with LEDs.

RULES:
- Information queries: keep current LED states unchanged
- LED commands: update LEDs as requested
- Conditional commands (if/when): evaluate condition from sensor data first
- Only ONE LED should be on at a time UNLESS user explicitly says "all"
- Be concise and conversational

Your response will be automatically formatted as JSON with 'message' and 'leds' fields."""


def create_interactive_prompt(temp_dht, hum, temp_bmp, press, 
                             button_state, ledRedSts, ledYlwSts, ledGrnSts, user_input):
    """Create a compact prompt for interactive user commands and queries (optimized version)."""
    return f"""STATUS: DHT22={temp_dht:.1f}°C/{hum:.1f}% BMP280={temp_bmp:.1f}°C/{press:.2f}hPa Button={'PRESSED' if button_state else 'OFF'} LEDs:R={'ON' if ledRedSts else 'OFF'}/Y={'ON' if ledYlwSts else 'OFF'}/G={'ON' if ledGrnSts else 'OFF'}

USER: {user_input}"""


def slm_inference(messages, MODEL):
    """Send chat request to Ollama using chat API with structured output (Pydantic)."""
    response = ollama.chat(
        model=MODEL,
        messages=messages,
        format=AssistantResponse.model_json_schema()  # Constrained decoding with Pydantic schema
    )
    return response


def parse_interactive_response(response_text):
    """Parse the interactive SLM response using Pydantic (guaranteed valid)."""
    try:
        # Parse directly into Pydantic model - guaranteed valid JSON structure
        data = AssistantResponse.model_validate_json(response_text)
        
        # Extract values from Pydantic model
        message = data.message
        red_led = data.leds.red_led
        yellow_led = data.leds.yellow_led
        green_led = data.leds.green_led
        
        return message, (red_led, yellow_led, green_led)
    
    except Exception as e:
        print(f"Error parsing response: {e}")
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
    print(f"Using Model: {MODEL} (Pydantic Optimized)")
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
        
        # Get SLM response using chat API with structured output
        print("Assistant: [Thinking...]")
        response = slm_inference(messages, MODEL)
        
        # Parse response using Pydantic (guaranteed valid)
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
    MODEL = 'llama3.2:3b'  # Same model, Pydantic optimized
    
    # Run in interactive mode
    interactive_mode(MODEL)
