from gpiozero import LED
from time import sleep

ledRed = LED(13)
ledYlw = LED(19)
ledGrn = LED(26)

ledRed.off()
ledYlw.off()
ledGrn.off()

ledRed.on()
ledYlw.on()
ledGrn.on()

sleep(5)

ledRed.off()
ledYlw.off()
ledGrn.off()
