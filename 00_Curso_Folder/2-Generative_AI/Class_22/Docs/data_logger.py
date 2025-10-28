import csv
import os
from datetime import datetime, timedelta
import threading
import time
from pathlib import Path


class DataLogger:
    """
    Manages data logging for the IoT system.
    Logs sensor readings, LED states, and command history to CSV files.
    """
    
    def __init__(self, data_dir="iot_data"):
        """Initialize the data logger."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # File paths
        self.sensor_log_file = self.data_dir / "sensor_readings.csv"
        self.command_log_file = self.data_dir / "command_history.csv"
        
        # Initialize CSV files if they don't exist
        self._initialize_csv_files()
        
        # Background logging control
        self.logging_active = False
        self.logging_thread = None
        self.log_interval = 60  # seconds (1 minute)
        
    def _initialize_csv_files(self):
        """Create CSV files with headers if they don't exist."""
        # Sensor readings file
        if not self.sensor_log_file.exists():
            with open(self.sensor_log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'temp_dht', 'humidity', 'temp_bmp', 
                    'pressure', 'button_pressed', 'red_led', 'yellow_led', 'green_led'
                ])
        
        # Command history file
        if not self.command_log_file.exists():
            with open(self.command_log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'user_command', 'slm_response', 
                    'red_led', 'yellow_led', 'green_led'
                ])
    
    def log_sensor_reading(self, temp_dht, humidity, temp_bmp, pressure, 
                          button_pressed, red_led, yellow_led, green_led):
        """Log a single sensor reading."""
        timestamp = datetime.now().isoformat()
        
        with open(self.sensor_log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp, temp_dht, humidity, temp_bmp, pressure,
                button_pressed, red_led, yellow_led, green_led
            ])
    
    def log_command(self, user_command, slm_response, red_led, yellow_led, green_led):
        """Log a user command and system response."""
        timestamp = datetime.now().isoformat()
        
        with open(self.command_log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp, user_command, slm_response,
                red_led, yellow_led, green_led
            ])
    
    def start_background_logging(self, collect_data_func, led_status_func):
        """
        Start background logging thread.
        
        Args:
            collect_data_func: Function to collect sensor data
            led_status_func: Function to get LED status
        """
        if self.logging_active:
            print("Background logging already active.")
            return
        
        self.logging_active = True
        self.logging_thread = threading.Thread(
            target=self._background_logging_loop,
            args=(collect_data_func, led_status_func),
            daemon=True
        )
        self.logging_thread.start()
        print(f"Background logging started (interval: {self.log_interval}s)")
    
    def stop_background_logging(self):
        """Stop background logging thread."""
        if self.logging_active:
            self.logging_active = False
            print("Background logging stopped.")
    
    def _background_logging_loop(self, collect_data_func, led_status_func):
        """Background thread loop for continuous logging."""
        while self.logging_active:
            try:
                # Collect current data
                temp_dht, hum, temp_bmp, press, button_state = collect_data_func()
                red_led, yellow_led, green_led = led_status_func()
                
                # Log if data is valid
                if all(v is not None for v in [temp_dht, hum, temp_bmp, press]):
                    self.log_sensor_reading(
                        temp_dht, hum, temp_bmp, press,
                        button_state, red_led, yellow_led, green_led
                    )
                
            except Exception as e:
                print(f"Error in background logging: {e}")
            
            # Wait for next interval
            time.sleep(self.log_interval)
    
    def get_sensor_readings(self, start_time=None, end_time=None, limit=None):
        """
        Retrieve sensor readings from log file.
        
        Args:
            start_time: Filter readings after this time (datetime)
            end_time: Filter readings before this time (datetime)
            limit: Maximum number of readings to return (most recent first)
        
        Returns:
            List of dictionaries containing sensor readings
        """
        readings = []
        
        with open(self.sensor_log_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                timestamp = datetime.fromisoformat(row['timestamp'])
                
                # Apply time filters
                if start_time and timestamp < start_time:
                    continue
                if end_time and timestamp > end_time:
                    continue
                
                readings.append({
                    'timestamp': timestamp,
                    'temp_dht': float(row['temp_dht']),
                    'humidity': float(row['humidity']),
                    'temp_bmp': float(row['temp_bmp']),
                    'pressure': float(row['pressure']),
                    'button_pressed': row['button_pressed'] == 'True',
                    'red_led': row['red_led'] == 'True',
                    'yellow_led': row['yellow_led'] == 'True',
                    'green_led': row['green_led'] == 'True'
                })
        
        # Apply limit (most recent first)
        if limit:
            readings = readings[-limit:]
        
        return readings
    
    def get_command_history(self, start_time=None, end_time=None, limit=None):
        """
        Retrieve command history from log file.
        
        Args:
            start_time: Filter commands after this time (datetime)
            end_time: Filter commands before this time (datetime)
            limit: Maximum number of commands to return (most recent first)
        
        Returns:
            List of dictionaries containing command history
        """
        commands = []
        
        with open(self.command_log_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                timestamp = datetime.fromisoformat(row['timestamp'])
                
                # Apply time filters
                if start_time and timestamp < start_time:
                    continue
                if end_time and timestamp > end_time:
                    continue
                
                commands.append({
                    'timestamp': timestamp,
                    'user_command': row['user_command'],
                    'slm_response': row['slm_response'],
                    'red_led': row['red_led'] == 'True',
                    'yellow_led': row['yellow_led'] == 'True',
                    'green_led': row['green_led'] == 'True'
                })
        
        # Apply limit (most recent first)
        if limit:
            commands = commands[-limit:]
        
        return commands
    
    def get_statistics(self, hours=24):
        """
        Calculate statistics for the specified time period.
        
        Args:
            hours: Number of hours to analyze (from now backwards)
        
        Returns:
            Dictionary containing statistical analysis
        """
        start_time = datetime.now() - timedelta(hours=hours)
        readings = self.get_sensor_readings(start_time=start_time)
        
        if not readings:
            return None
        
        # Calculate statistics
        temps_dht = [r['temp_dht'] for r in readings]
        temps_bmp = [r['temp_bmp'] for r in readings]
        humidities = [r['humidity'] for r in readings]
        pressures = [r['pressure'] for r in readings]
        
        # LED state changes
        led_changes = {
            'red': sum(1 for i in range(1, len(readings)) 
                      if readings[i]['red_led'] != readings[i-1]['red_led']),
            'yellow': sum(1 for i in range(1, len(readings)) 
                         if readings[i]['yellow_led'] != readings[i-1]['yellow_led']),
            'green': sum(1 for i in range(1, len(readings)) 
                        if readings[i]['green_led'] != readings[i-1]['green_led'])
        }
        
        # Button presses
        button_presses = sum(1 for i in range(1, len(readings))
                           if readings[i]['button_pressed'] and not readings[i-1]['button_pressed'])
        
        return {
            'period_hours': hours,
            'total_readings': len(readings),
            'temperature_dht': {
                'min': min(temps_dht),
                'max': max(temps_dht),
                'avg': sum(temps_dht) / len(temps_dht),
                'current': temps_dht[-1]
            },
            'temperature_bmp': {
                'min': min(temps_bmp),
                'max': max(temps_bmp),
                'avg': sum(temps_bmp) / len(temps_bmp),
                'current': temps_bmp[-1]
            },
            'humidity': {
                'min': min(humidities),
                'max': max(humidities),
                'avg': sum(humidities) / len(humidities),
                'current': humidities[-1]
            },
            'pressure': {
                'min': min(pressures),
                'max': max(pressures),
                'avg': sum(pressures) / len(pressures),
                'current': pressures[-1]
            },
            'led_changes': led_changes,
            'button_presses': button_presses
        }
    
    def get_trend(self, parameter, hours=24):
        """
        Determine trend (increasing, decreasing, stable) for a parameter.
        
        Args:
            parameter: 'temp_dht', 'temp_bmp', 'humidity', or 'pressure'
            hours: Number of hours to analyze
        
        Returns:
            Dictionary with trend information
        """
        start_time = datetime.now() - timedelta(hours=hours)
        readings = self.get_sensor_readings(start_time=start_time)
        
        if len(readings) < 2:
            return {'trend': 'insufficient_data', 'change': 0}
        
        values = [r[parameter] for r in readings]
        
        # Calculate simple linear trend
        n = len(values)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        # Calculate slope
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # Total change
        change = values[-1] - values[0]
        
        # Determine trend
        if abs(slope) < 0.01:
            trend = 'stable'
        elif slope > 0:
            trend = 'increasing'
        else:
            trend = 'decreasing'
        
        return {
            'trend': trend,
            'change': change,
            'start_value': values[0],
            'end_value': values[-1],
            'slope': slope
        }
