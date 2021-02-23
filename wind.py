from gpiozero import Button
import math
import time, statistics
import wind_direction_byo

wind_speed_sensor = Button(5)
wind_count = 0
store_speeds = []
store_directions = []

radius_cm = 9.0
ADJUSTMENT = 1.18
SECS_IN_AN_HOUR = 3600
CM_IN_A_KM = 100000

def spin():
  global wind_count
  wind_count = wind_count + 1

wind_speed_sensor.when_pressed = spin # bind

def reset_wind():
  global wind_count
  wind_count = 0

def calculate_speed(time_sec):
  global wind_count
  circumference_cm = (2 * math.pi) * radius_cm
  rotations = wind_count / 2.0
  dist_km = (circumference_cm * rotations) / CM_IN_A_KM
  km_per_sec = dist_km / time_sec
  km_per_hour = km_per_sec * SECS_IN_AN_HOUR
  return km_per_hour * ADJUSTMENT