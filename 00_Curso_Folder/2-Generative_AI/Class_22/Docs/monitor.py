import time
import board
import adafruit_dht
import adafruit_bmp280
from gpiozero import LED, Button

DHT22Sensor = adafruit_dht.DHT22(board.D16)
i2c = board.I2C()
bmp280Sensor = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=0x76)
bmp280Sensor.sea_level_pressure = 1013.25

ledRed = LED(13)
ledYlw = LED(19)
ledGrn = LED(26)
button = Button(20)

def collect_data():
    try:
        temperature_dht = DHT22Sensor.temperature
        humidity = DHT22Sensor.humidity
        temperature_bmp = bmp280Sensor.temperature
        pressure = bmp280Sensor.pressure
        button_pressed = button.is_pressed
        return temperature_dht, humidity, temperature_bmp, pressure, button_pressed
    except RuntimeError:
        return None, None, None, None, None

def led_status():
    ledRedSts = ledRed.is_lit
    ledYlwSts = ledYlw.is_lit
    ledGrnSts = ledGrn.is_lit 
    return ledRedSts, ledYlwSts, ledGrnSts


def control_leds(red, yellow, green):
    ledRed.on() if red else ledRed.off()
    ledYlw.on() if yellow else ledYlw.off()
    ledGrn.on() if green else ledGrn.off()


if __name__ == "__main__":
    while True:
        ledRedSts, ledYlwSts, ledGrnSts  = led_status()
        temp_dht, hum, temp_bmp, press, button_state  = collect_data()

        #control_leds(True, True, True)
         
        if all(v is not None for v in [temp_dht, hum, temp_bmp, press]):
            print(f"\nMonitor Data")
            print(f"DHT22 Temp: {temp_dht:.1f}°C, Humidity: {hum:.1f}%")
            print(f"BMP280 Temp: {temp_bmp:.1f}°C, Pressure: {press:.2f}hPa")
            print(f"Button {'pressed' if button_state else 'not pressed'}")
            print(f"Red LED {'is on' if ledRedSts else 'is off'}")
            print(f"Yellow LED {'is on' if ledYlwSts else 'is off'}")
            print(f"Green LED {'is on' if ledGrnSts else 'is off'}")
            

        time.sleep(2)