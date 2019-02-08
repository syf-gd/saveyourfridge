# ################################################################
# ########   SaveYourFridge
# ################################################################
# LED status indication:
#
# green (>5sec) =   Init ok
# red   (>5sec) =   Init failed
# blue  (<5sec) =   sending data
# green (<5sec) =   sending alarm

# ################################################################
# ########   imports
# ################################################################
import sys
from network import Sigfox
from machine import WDT
import socket
import binascii
import struct
import pycom
from pysense import Pysense
from MPL3115A2 import MPL3115A2,ALTITUDE,PRESSURE
import gc
import time

py = Pysense()

# messen alle 5 minuten, senden alle 15 minuten
measurement_interval=30
transmission_interval=3600
anomaly_detection_difference = 2
low_power_consumption_mode = 0
send_all_data = 1
fast_boot = 1

# ################################################################
# ########   main
# ################################################################
pycom.heartbeat(False)
gc.enable()
py.setup_int_wake_up(True, True)

wdt = WDT(timeout=1200000)  # enable it with a timeout of 1 seconds (1000)*1200 (=20min)
wdt.feed()

sigfox = Sigfox(mode=Sigfox.SIGFOX, rcz=Sigfox.RCZ1)
sigfox_network = socket.socket(socket.AF_SIGFOX, socket.SOCK_RAW)
sigfox_network.setblocking(True)
sigfox_network.setsockopt(socket.SOL_SIGFOX, socket.SO_RX, False)
device_id = binascii.hexlify(sigfox.id())
device_pac = binascii.hexlify(sigfox.pac())

# INIT
# fake green status
# test uplink/downlink - if successful, send green light, else red light
if fast_boot == 0:
    pycom.rgbled(0x007f00)
    time.sleep(5)
    pycom.rgbled(0x000000)

this_interval=0
init_count=0
old_temperature=0
while True:
    this_interval += 1
    already_sent = 0

    # round to floor
    if low_power_consumption_mode == 0:
        print("measuring...")
        pycom.rgbled(0x00007f)
    original_temperature=MPL3115A2(py,mode=ALTITUDE).temperature()
    now_temperature = int(original_temperature*2+80)
    if low_power_consumption_mode == 0:
        pycom.rgbled(0x000000)

    intervals = transmission_interval/(measurement_interval*this_interval)
    if low_power_consumption_mode == 0:
        #print("measurement_interval=%s" % measurement_interval)
        #print("transmission_interval=%s" % transmission_interval)
        #print("intervals=%s" % intervals)
        #print("this_interval=%s" % str(this_interval))
        print("temperature (this) [%s]: %s ((temp-80)/2=%s)" % (device_id, now_temperature, original_temperature))
        print("temperature (old)  [%s]: %s ((temp-80)/2)"  % (device_id, old_temperature))
        print("temperature anomaly[%s]: %s (>=)" % (device_id, anomaly_detection_difference))

    if init_count == 0:
        # first start => send message
            if low_power_consumption_mode == 0:
                print("sending first value after restart... (green:%s,%s)" % (now_temperature, old_temperature))
            pycom.rgbled(0x007f00)
            sigfox_network.send(bytes([now_temperature, old_temperature]))
            pycom.rgbled(0x000000)

    if init_count == 1:
        # only if first measurement completed
        if now_temperature >= (old_temperature + anomaly_detection_difference):
            if low_power_consumption_mode == 0:
                print("sending alarm... (red:%s,%s)" % (now_temperature, old_temperature))
            
            pycom.rgbled(0x7f0000)
            sigfox_network.send(bytes([now_temperature,old_temperature]))
            pycom.rgbled(0x000000)
            this_interval=0
            already_sent=1

    old_temperature=now_temperature

    if already_sent == 0:
        # only end if not already red status
        if (intervals == 1.0) or (send_all_data == 1):
            if low_power_consumption_mode == 0:
                print("sending... (green:%s,%s)" % (now_temperature,old_temperature))
            pycom.rgbled(0x007f00)
            sigfox_network.send(bytes([now_temperature, old_temperature]))
            #pybytes.send_virtual_pin_value(False,15,int(now_temperature))
            this_interval=0
            pycom.rgbled(0x000000)

    wdt.feed()
    if low_power_consumption_mode == 0:
        time.sleep(measurement_interval)
    else:
        py.setup_sleep(measurement_interval)
        py.go_to_sleep()

    init_count = 1

sigfox_network.close()
