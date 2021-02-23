#!/usr/bin/python3
import plantower
import time, statistics
from tb_device_mqtt import TBDeviceMqttClient, TBPublishInfo
import bme280
import smbus2
import wind
import wind_direction_byo
import rainfall
from renogy_driver import RenogyRover
import configparser

# USB DEVICES
USB_DEVICE_1 = "/dev/ttyUSB_PMS7003" # particulates
USB_DEVICE_2 = "/dev/ttyUSB_CONTROLLER" # solar controller

def main():

  # Particulate Matter
  PLANTOWER = plantower.Plantower(port=USB_DEVICE_1)
  print("Making sure it's correctly setup for active mode. Please wait")
  #make sure it's in the correct mode if it's been used for passive beforehand
  #Not needed if freshly plugged in
  PLANTOWER.mode_change(plantower.PMS_ACTIVE_MODE) #change back into active mode
  PLANTOWER.set_to_wakeup() #ensure fan is spinning

  # Renology Wanderer 10A Charge Controller
  rover = RenogyRover(USB_DEVICE_2, 1)

  # BME 280 Temp, Humidity, Pressure
  port = 1
  address = 0x77 # Adafruit BME280 address. Other BME280s may be different
  bus = smbus2.SMBus(port)
  bme280.load_calibration_params(bus,address)
  
  # delay 30 seconds to warmup devices
  print('30 second warmup....')
  time.sleep(30)
  print('30 second warmup done....')

  telemetry = {
    "pm_10": 'not set',
    "pm_2_5": 'not set',
    "pm_1_0": 'not set',
    "ambient_humidity": 'not set',
    "ambient_pressure": 'not set',
    "ambient_temperature": 'not set',
    "wind_speed": 'not set',
    "wind_gust": 'not set',
    "wind_direction": 'not set',
    "rainfall": 'not set',
    "battery_percentage": 'not set',
    "battery_type": 'not set',
    "battery_capacity": 'not set',
    "battery_voltage": 'not set',
    "battery_temperature": 'not set',
    "controller_model": 'not set',
    "controller_charging_status": 'not set',
    "controller_temperature": 'not set',
    "load_voltage": 'not set',
    "load_current": 'not set',
    "load_power": 'not set',
    "solar_voltage": 'not set',
    "solar_current": 'not set',
    "solar_power": 'not set',
    "power_generation_today": 'not set',
    "charging_amp_hours_today": 'not set',
    "discharging_amp_hours_today": 'not set'
  }

  #MQTT ~~~~
  config = configparser.ConfigParser()
  config.read("config.ini")
  THINGSBOARD_HOST = config.get("thingsboard", "host")
  ACCESS_TOKEN = config.get("thingsboard", "token")

  #SSL Cert locations
  CA_CERTS = ''
  CERT_FILE = ''
  KEY_FILE = ''

  # Set access token
  client = TBDeviceMqttClient(THINGSBOARD_HOST, ACCESS_TOKEN)

  # Connect to ThingsBoard
  client.connect()

  # Data capture and upload interval in seconds. Less interval will eventually hang the DHT22.
  INTERVAL=1
  AVG_INTERVAL=60
  next_reading = time.time()
  # Lists for averages
  pm_1_0_list = []
  pm_2_5_list = []
  pm_10_list = []

  try:
    while True:
      # Every second do this...
      try:
        pm = PLANTOWER.read()
      except Exception as e:
        print("PMS7003: exception: " + str(e)) 
      # print(pm)
      pm_1_0_list.append(pm.pm10_std)
      pm_2_5_list.append(pm.pm25_std)
      pm_10_list.append(pm.pm100_std)
      # wind
      wind.store_speeds.append(wind.calculate_speed(INTERVAL))
      wind_d = wind_direction_byo.get_value()
      if wind_d is not None:
        wind.store_directions.append(wind_d)
      wind.reset_wind()
      # Every 60 seconds do this...
      if len(pm_1_0_list) == AVG_INTERVAL and len(pm_2_5_list) == AVG_INTERVAL and len(pm_10_list) == AVG_INTERVAL:
        # average wind
        wind_average = wind_direction_byo.get_average(wind.store_directions)
        wind_gust = max(wind.store_speeds)
        wind_speed = statistics.mean(wind.store_speeds)
        telemetry["wind_speed"] = str(wind_speed * 0.621371) # convert to mph
        telemetry["wind_gust"] = str(wind_gust * 0.621371) # convert to mph
        telemetry["wind_direction"] = str(wind_average)
        # at end of interval average value and add to telemetry
        pm_1_0_avg = statistics.mean(pm_1_0_list)
        pm_2_5_avg = statistics.mean(pm_2_5_list)
        pm_10_avg = statistics.mean(pm_10_list)
        telemetry["pm_1_0"] = str(pm_1_0_avg)
        telemetry["pm_2_5"] = str(pm_2_5_avg)
        telemetry["pm_10"] = str(pm_10_avg)
        # rain
        rain = rainfall.get_value()
        telemetry["rainfall"] = str(rain)
        rainfall.reset_rainfall()
        # BME280
        bme280_data = bme280.sample(bus,address)
        humidity  = bme280_data.humidity
        pressure  = bme280_data.pressure
        temperature = (bme280_data.temperature * 1.8) + 32 # convert to Farenheit
        # print(pressure, humidity, ambient_temperature)
        telemetry["ambient_pressure"] = str(pressure)
        telemetry["ambient_humidity"] = str(humidity)
        telemetry["ambient_temperature"] = str(temperature)
        # Controller Battery telemetry
        telemetry["battery_percentage"] = rover.battery_percentage()
        telemetry["battery_type"] = rover.battery_type()
        telemetry["battery_capacity"] = rover.battery_capacity()
        telemetry["battery_voltage"] = rover.battery_voltage()
        telemetry["battery_temperature"] = rover.battery_temperature()
        # Controller telemetry
        telemetry["controller_model"] = rover.model()
        telemetry["controller_temperature"] = rover.controller_temperature()
        telemetry["controller_charging_status"] = rover.charging_status_label()
        # Load Telemetry
        telemetry["load_voltage"] = rover.load_voltage()
        telemetry["load_current"] = rover.load_current()
        telemetry["load_power"] = rover.load_power()
        # Solar Telemetry
        telemetry["solar_voltage"] = rover.solar_voltage()
        telemetry["solar_current"] = rover.solar_current()
        telemetry["solar_power"] = rover.solar_power()
        # Controller Stats Telemetry
        telemetry["power_generation_today"] = rover.power_generation_today()
        telemetry["charging_amp_hours_today"] = rover.charging_amp_hours_today()
        telemetry["discharging_amp_hours_today"] = rover.discharging_amp_hours_today()
        # Sending telemetry and checking the delivery status (QoS = 1 by default)
        result = client.send_telemetry(telemetry)
        result.get()
        print("Telemetry update sent: " + str(result.rc() == TBPublishInfo.TB_ERR_SUCCESS))
        print("Telemetry: " + str(telemetry))
        # reset list
        pm_1_0_list.clear()
        pm_2_5_list.clear()
        pm_10_list.clear()
        wind.store_speeds.clear()
        wind.store_directions.clear()

      next_reading += INTERVAL
      sleep_time = next_reading-time.time()
      if sleep_time > 0:
        time.sleep(sleep_time)
  except KeyboardInterrupt:
    pass

  client.disconnect()

if __name__ == '__main__':
  main()
