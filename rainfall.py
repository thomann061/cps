from gpiozero import Button
import time

rain_sensor = Button(13, pull_up=True)
count = 0
BUCKET_SIZE = 0.2794 # in mm
BUCKET_SIZE_INCHES = BUCKET_SIZE / 25.4

def bucket_tipped():
  global count
  print("Tipped")
  count += 1

def reset_rainfall():
  global count
  count = 0

rain_sensor.when_pressed = bucket_tipped

def get_value():
  return count * BUCKET_SIZE_INCHES
