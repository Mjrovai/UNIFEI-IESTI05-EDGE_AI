import ollama
import json
from datetime import datetime, timedelta
from monitor import collect_data, led_status, control_leds
from data_logger import DataLogger


# Initialize data logger
logger = DataLogger()


def create_analysis_prompt(user_input, statistics, trends, recent_readings, command_history):
    """Create a prompt for analyzing historical data."""
    return f"""
You are an IoT system assistant with access to historical sensor data and analysis.

USER REQUEST: "{user_input}"

CURRENT STATISTICS (Last 24 hours):
- Total readings: {statistics['total_readings'] if statistics else 0}
- Temperature DHT22: Min={statistics['temperature_dht']['min']:.1f}°C, Max={statistics['temperature_dht']['max']:.1f}°C, Avg={statistics['temperature_dht']['avg']:.1f}°C
- Temperature BMP280: Min={statistics['temperature_bmp']['min']:.1f}°C, Max={statistics['temperature_bmp']['max']:.1f}°C, Avg={statistics['temperature_bmp']['avg']:.1f}°C
- Humidity: Min={statistics['humidity']['min']:.1f}%, Max={statistics['humidity']['max']:.1f}%, Avg={statistics['humidity']['avg']:.1f}%
- Pressure: Min={statistics['pressure']['min']:.1f}hPa, Max={statistics['pressure']['max']:.1f}hPa, Avg={statistics['pressure']['avg']:.1f}hPa
- LED changes: Red={statistics['led_changes']['red']}, Yellow={statistics['led_changes']['yellow']}, Green={statistics['led_changes']['green']}
- Button presses: {statistics['button_presses']}

TRENDS (Last 24 hours):
- Temperature DHT22: {trends['temp_dht']['trend']} (change: {trends['temp_dht']['change']:.2f}°C)
- Temperature BMP280: {trends['temp_bmp']['trend']} (change: {trends['temp_bmp']['change']:.2f}°C)
- Humidity: {trends['humidity']['trend']} (change: {trends['humidity']['change']:.2f}%)
- Pressure: {trends['pressure']['trend']} (change: {trends['pressure']['change']:.2f}hPa)

RECENT READINGS (Last 5):
{format_recent_readings(recent_readings)}

RECENT COMMANDS (Last 3):
{format_command_history(command_history)}

INSTRUCTIONS:
Analyze the user's request and provide a helpful, detailed response about the historical data.
Use the statistics, trends, and recent readings to answer their question.
Be specific with numbers and include relevant insights.

Respond with ONLY a JSON object:
{{
  "message": "Your detailed analysis and response to the user"
}}

Respond with ONLY the JSON, no other text.
"""


def format_recent_readings(readings):
    """Format recent readings for the prompt."""
    if not readings:
        return "No recent readings available."
    
    formatted = []
    for r in readings:
        formatted.append(
            f"- {r['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}: "
            f"Temp={r['temp_dht']:.1f}°C, Hum={r['humidity']:.1f}%, "
            f"Press={r['pressure']:.1f}hPa, Button={'Pressed' if r['button_pressed'] else 'Not pressed'}"
        )
    return "\n".join(formatted)


def format_command_history(commands):
    """Format command history for the prompt."""
    if not commands:
        return "No recent commands."
    
    formatted = []
    for c in commands:
        formatted.append(
            f"- {c['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}: "
            f"'{c['user_command']}' → Response: {c['slm_response'][:60]}..."
        )
    return "\n".join(formatted)


def create_interactive_prompt(temp_dht, hum, temp_bmp, press, button_state, 
                              ledRedSts, ledYlwSts, ledGrnSts, user_input):
	"""Create a prompt for interactive user commands and queries."""
	return f"""
You are an IoT system assistant controlling an environmental monitoring system with LED indicators.

CURRENT SYSTEM STATUS:
- DHT22: Temperature {temp_dht:.1f}°C, Humidity {hum:.1f}%
- BMP280: Temperature {temp_bmp:.1f}°C, Pressure {press:.1f}hPa
- Button: {"PRESSED" if button_state else "NOT PRESSED"}
- Red LED: {"ON" if ledRedSts else "OFF"}
- Yellow LED: {"ON" if ledYlwSts else "OFF"}
- Green LED: {"ON" if ledGrnSts else "OFF"}

USER REQUEST: "{user_input}"

INSTRUCTIONS:
Respond with a JSON object containing two fields:

1. "message": A helpful text response to the user
2. "leds": LED control object with three boolean fields: "red_led", "yellow_led", "green_led"

EXAMPLES:

User: "what's the current temperature?"
Response: {{"message": "The current temperature is {temp_dht:.1f}°C from DHT22 and {temp_bmp:.1f}°C from BMP280.", "leds": {{"red_led": {str(ledRedSts).lower()}, "yellow_led": {str(ledYlwSts).lower()}, "green_led": {str(ledGrnSts).lower()}}}}}

User: "turn on the yellow led"
Response: {{"message": "Yellow LED turned on.", "leds": {{"red_led": false, "yellow_led": true, "green_led": false}}}}

User: "turn on all leds"
Response: {{"message": "All LEDs turned on.", "leds": {{"red_led": true, "yellow_led": true, "green_led": true}}}}

RULES:
- Always respond with valid JSON containing both "message" and "leds" fields
- If asking for information only, keep current LED states
- If giving a command, update LED states accordingly
- Be conversational and helpful

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
        response_text = response_text.strip()
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text
            response_text = response_text.replace('```json', '').replace('```', '').strip()
        
        data = json.loads(response_text)
        message = data.get('message', 'No response provided.')
        
        leds = data.get('leds', {})
        if leds:
            red_led = leds.get('red_led', False)
            yellow_led = leds.get('yellow_led', False)
            green_led = leds.get('green_led', False)
            return message, (red_led, yellow_led, green_led)
        else:
            return message, None
    
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing JSON response: {e}")
        return "Error: Could not parse SLM response.", None


def is_analysis_query(user_input):
    """Determine if the query is about historical data analysis."""
    analysis_keywords = [
        'trend', 'average', 'history', 'past', 'last hour', 'last day',
        'statistics', 'stat', 'how many', 'when was', 'show me',
        'yesterday', 'ago', 'previous', 'recent', 'log', 'data'
    ]
    return any(keyword in user_input.lower() for keyword in analysis_keywords)


def display_system_status(temp_dht, hum, temp_bmp, press, button_state, ledRedSts, ledYlwSts, ledGrnSts):
    """Display comprehensive system status."""
    print("\n" + "="*60)
    print("SYSTEM STATUS")
    print("="*60)
    print(f"DHT22 Sensor:  Temp = {temp_dht:.1f}°C, Humidity = {hum:.1f}%")
    print(f"BMP280 Sensor: Temp = {temp_bmp:.1f}°C, Pressure = {press:.1f}hPa")
    print(f"Button:        {'PRESSED' if button_state else 'NOT PRESSED'}")
    print(f"\nLED Status:")
    print(f"  Red LED:    {'●' if ledRedSts else '○'} {'ON' if ledRedSts else 'OFF'}")
    print(f"  Yellow LED: {'●' if ledYlwSts else '○'} {'ON' if ledYlwSts else 'OFF'}")
    print(f"  Green LED:  {'●' if ledGrnSts else '○'} {'ON' if ledGrnSts else 'OFF'}")
    print("="*60)


def interactive_mode(MODEL):
    """Run the system in interactive mode with data logging and analysis."""
    print("\n" + "="*60)
    print("IoT Environmental Monitoring - Enhanced with Data Logging")
    print(f"Using Model: {MODEL}")
    print("="*60)
    print("\nFeatures:")
    print("  • Real-time sensor monitoring and LED control")
    print("  • Automatic background data logging (every minute)")
    print("  • Historical data analysis and trend reporting")
    print("  • Natural language queries")
    print("\nCommands you can try:")
    print("  Real-time Control:")
    print("    - What's the current temperature?")
    print("    - Turn on the yellow LED")
    print("    - If temperature is above 20°C, turn on yellow LED")
    print("\n  Data Analysis:")
    print("    - Show me temperature trends for the last 24 hours")
    print("    - What was the average humidity today?")
    print("    - How many times was the button pressed?")
    print("    - Show me recent sensor readings")
    print("\n  System Commands:")
    print("    - status: Show current system status")
    print("    - stats: Show 24-hour statistics")
    print("    - exit/quit: Stop the system")
    print("="*60 + "\n")
    
    # Start background logging
    logger.start_background_logging(collect_data, led_status)
    
    try:
        while True:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['exit', 'quit', 'q']:
                logger.stop_background_logging()
                print("\nStopping background logging...")
                print("Exiting. Goodbye!")
                break
            
            ledRedSts, ledYlwSts, ledGrnSts = led_status()
            temp_dht, hum, temp_bmp, press, button_state = collect_data()
            
            if user_input.lower() == 'status':
                display_system_status(temp_dht, hum, temp_bmp, press, button_state, 
                                    ledRedSts, ledYlwSts, ledGrnSts)
                continue
            
            if user_input.lower() in ['stats', 'statistics']:
                print("\nCalculating statistics for last 24 hours...")
                stats = logger.get_statistics(hours=24)
                if stats:
                    print(f"\nStatistics (Last 24 hours):")
                    print(f"  Total readings: {stats['total_readings']}")
                    print(f"  Temperature DHT22: {stats['temperature_dht']['min']:.1f}°C - {stats['temperature_dht']['max']:.1f}°C (avg: {stats['temperature_dht']['avg']:.1f}°C)")
                    print(f"  Humidity: {stats['humidity']['min']:.1f}% - {stats['humidity']['max']:.1f}% (avg: {stats['humidity']['avg']:.1f}%)")
                    print(f"  Pressure: {stats['pressure']['min']:.1f}hPa - {stats['pressure']['max']:.1f}hPa (avg: {stats['pressure']['avg']:.1f}hPa)")
                    print(f"  LED changes: Red={stats['led_changes']['red']}, Yellow={stats['led_changes']['yellow']}, Green={stats['led_changes']['green']}")
                    print(f"  Button presses: {stats['button_presses']}")
                else:
                    print("No data available yet.")
                print()
                continue
            
            if any(v is None for v in [temp_dht, hum, temp_bmp, press]):
                print("Assistant: Error - Unable to read sensor data.\n")
                continue
            
            if is_analysis_query(user_input):
                print("Assistant: [Analyzing historical data...]")
                
                try:
                    stats = logger.get_statistics(hours=24)
                    if not stats:
                        print("Assistant: No historical data available yet. Please try again after data has been logged.\n")
                        continue
                    
                    trends = {
                        'temp_dht': logger.get_trend('temp_dht', hours=24),
                        'temp_bmp': logger.get_trend('temp_bmp', hours=24),
                        'humidity': logger.get_trend('humidity', hours=24),
                        'pressure': logger.get_trend('pressure', hours=24)
                    }
                    
                    recent_readings = logger.get_sensor_readings(limit=5)
                    command_history = logger.get_command_history(limit=3)
                    
                    PROMPT = create_analysis_prompt(user_input, stats, trends, recent_readings, command_history)
                    response = slm_inference(PROMPT, MODEL)
                    message, led_command = parse_interactive_response(response['response'])
                    
                    print(f"Assistant: {message}\n")
                    
                except Exception as e:
                    print(f"Assistant: Error during analysis: {e}\n")
                
            else:
                print("Assistant: [Thinking...]")
                
                PROMPT = create_interactive_prompt(temp_dht, hum, temp_bmp, press, button_state,
                                                  ledRedSts, ledYlwSts, ledGrnSts, user_input)
                
                response = slm_inference(PROMPT, MODEL)
                message, led_command = parse_interactive_response(response['response'])
                
                print(f"Assistant: {message}")
                
                if led_command:
                    red, yellow, green = led_command
                    control_leds(red, yellow, green)
                    logger.log_command(user_input, message, red, yellow, green)
                    
                    ledRedSts, ledYlwSts, ledGrnSts = led_status()
                    print(f"\nLED Update: Red={'ON' if ledRedSts else 'OFF'}, "
                          f"Yellow={'ON' if ledYlwSts else 'OFF'}, "
                          f"Green={'ON' if ledGrnSts else 'OFF'}\n")
                else:
                    print()
    
    except KeyboardInterrupt:
        logger.stop_background_logging()
        print("\n\nStopping background logging...")
        print("Exiting. Goodbye!")


if __name__ == "__main__":
    MODEL = 'llama3.2:3b'
    interactive_mode(MODEL)
