from gpiozero import LED
from time import sleep
led = LED(13)
while True:
    led.on()
    sleep(1)
    led.off()
    sleep(1)
