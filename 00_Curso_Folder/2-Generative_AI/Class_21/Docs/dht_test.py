import time
import board
import adafruit_dht
dhtDevice = adafruit_dht.DHT22(board.D16)

while True:
    try:
        # Print the values to the serial port
        temperature_c = dhtDevice.temperature
        temperature_f = temperature_c * (9 / 5) + 32
        humidity = dhtDevice.humidity
        print(
            "Temp: {:.1f} F / {:.1f} C    Humidity: {}% ".format(
                temperature_f, temperature_c, humidity
            )
        )
        time.sleep(5.0)
    except RuntimeError as error:
        # Errors happen fairly often, DHT's are hard to read, 
        # just keep going
        print(error.args[0])
        time.sleep(2.0)
        continue
    except Exception as error:
        dhtDevice.exit()
        raise error
