# ################################################################
# ########   SaveYourFridge
# ################################################################
# LED status indication:
#
# white (0-20sec.)  =   Init
# white (5x)        =   Init ok
# red   (~x)        =   Init failed
# blue  (<5sec)     =   measurement
# green (<5sec)     =   sending data (ok)
# red   (<5sec)     =   sending alarm (nok)

# ################################################################
# ########   Variables
# ################################################################
measurement_interval=10             # #=seconds a measurement will be done (300=>5 minutes)
transmission_interval=100           # #=seconds a message will be sent (independently of alarm) (3600=>15 minutes)
anomaly_detection_difference = 2     # #=differences in degrees(celsius) to send alarm by device
low_power_consumption_mode = 1       # 1=send device to deep sleep mode (attention: system is not connectable anymore)
send_all_data = 0                    # 1=send every measurement
fast_boot = 0                        # no operational feedback at boot - ATTENTION: "0" is the only way to re-deploy code to the board without flashing the firmware!
signal_test = 1                      # 1=do signal strength test at boot
protocol_version=1                   # #=1-254 (change, if data format changed)
rssi_dbm_limit=-135                  # limit of rssi strength (-135...-122)
disable_low_power_on_usb=1           # disable low power mode if usb connection is detected


# protocol versions:
# (1)   initial version
#       AABB; AA=protocaol version, BB=temperature
# (?)
#
# (255) AA00; AA=protocol version; 00=dummy message

# ################################################################
# ################################################################
# ########   +++++ NO CHANGES BELOW THIS LINE +++++
# ################################################################
# ################################################################
color_blue=0x00007f
color_orange=0xea3602
color_red=0x7f0000
color_green=0x007f00
color_black=0x000000
color_white=0x444444

# ################################################################
# ########   imports
# ################################################################
import os
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


def countInterval():
    interval = pycom.nvs_get('interval')
    interval += 1
    pycom.nvs_set('interval', interval)

py = Pysense()

# ################################################################
# ########   main
# ################################################################
pycom.heartbeat(False)

gc.enable()

wdt = WDT(timeout=1200000)  # enable it with a timeout of 1 seconds (1000)*1200 (=20min)
wdt.feed()

battery_voltage=py.read_battery_voltage()

if disable_low_power_on_usb == 1:
    if battery_voltage > 4.2:
        low_power_consumption_mode=0
        print("USB connection detected, disable low power mode (voltage=%s)" % (str(py.read_battery_voltage())))
        wdt.feed()

sigfox = Sigfox(mode=Sigfox.SIGFOX, rcz=Sigfox.RCZ1)
sigfox_network = socket.socket(socket.AF_SIGFOX, socket.SOCK_RAW)
sigfox_network.setblocking(True)
sigfox_network.setsockopt(socket.SOL_SIGFOX, socket.SO_RX, True) # true=downlink
device_id = binascii.hexlify(sigfox.id())
device_pac = binascii.hexlify(sigfox.pac())
if low_power_consumption_mode == 0:
    print("DEVICE ID : %s" % (device_id))
    print("DEVICE PAC: %s" % (device_pac))
wdt.feed()

# ################################################################
# ########   pre-check
# ################################################################

low_power_mode_indicator=color_white
low_power_mode_indicator_ok=color_white
low_power_mode_indicator_fail=color_red

for x in range(4):
    # indicate power mode (blue=high power, orange=low power)
    time.sleep(0.1)
    pycom.rgbled(color_black)
    time.sleep(0.1)
    pycom.rgbled(low_power_mode_indicator)

if signal_test == 1 and pycom.nvs_get('signaltest_done') is None:
    # test uplink/downlink - if successful, send green light, else red light
    signal_strength=-500        # default value
    if low_power_consumption_mode == 0:
        print("send strength test message")
    try:
        error_position="send"
        sigfox_network.send(bytes([255,255,0]))

        error_position="send2"
        if low_power_consumption_mode == 0:
            print("waiting for feedback message")

        error_position="recv"
        sigfox_network.recv(32)

        error_position="rssi"
        signal_strength=sigfox.rssi()
        wdt.feed()

    except:
        # every error will stop strength test
        signal_strength=-500
        if low_power_consumption_mode == 0:
            print("error while waiting for signal strength test (position=%s)" % (error_position))

    if low_power_consumption_mode == 0:
        print("received signal stregth: %s" % (str(signal_strength)))
    if signal_strength < rssi_dbm_limit:
        if low_power_consumption_mode == 0:
            print("ERROR: signal stregth below limit: %s < %s" % (str(signal_strength),str(rssi_dbm_limit)))
        while True:
            pycom.rgbled(low_power_mode_indicator_fail)
            time.sleep(0.1)
            pycom.rgbled(color_black)
            time.sleep(0.1)
    else:
        if low_power_consumption_mode == 0:
            print("signal stregth okay : %s >= %s" % (str(signal_strength),str(rssi_dbm_limit)))
            pycom.nvs_set('signaltest_done', 1)
            print("NVRAM set: signaltest_done = 1")
        for x in range(4):
            pycom.rgbled(low_power_mode_indicator_ok)
            time.sleep(0.1)
            pycom.rgbled(color_black)
            time.sleep(0.1)
    wdt.feed()
    pycom.rgbled(color_black)


# ################################################################
# ########   measurement loop
# ################################################################
# sigfox: change to uplink messages only
sigfox_network.setsockopt(socket.SOL_SIGFOX, socket.SO_RX, False) # false=only uplink
#this_interval=0
#init_count=0
#old_temperature=0
pycom.nvs_set('interval', 0)
pycom.nvs_set('init_count', 0)
pycom.nvs_set('last_temp', 0)
while True:
    #this_interval += 1
    countInterval()
    already_sent = 0

    # round to floor
    if low_power_consumption_mode == 0:
        print("measuring...")
        pycom.rgbled(color_blue)
    original_temperature=MPL3115A2(py,mode=ALTITUDE).temperature()
    now_temperature = int(original_temperature*2+80)
    if low_power_consumption_mode == 0:
        pycom.rgbled(0x000000)

    intervals = transmission_interval/(measurement_interval*pycom.nvs_get('interval'))
    if low_power_consumption_mode == 0:
        print("temperature (this)  [%s]: %s ((temp-80)/2=%s)" % (device_id, now_temperature, original_temperature))
        print("temperature (old)   [%s]: %s ((temp-80)/2)"  % (device_id, pycom.nvs_get('last_temp')))
        print("temperature anomaly [%s]: %s (>=)" % (device_id, anomaly_detection_difference))
    wdt.feed()
    if pycom.nvs_get('init_count') == 0:
        # first start => send message
            if low_power_consumption_mode == 0:
                print("sending first value after restart... (green:%s; v:%s)" % (now_temperature, protocol_version))
            if low_power_consumption_mode == 0:
                pycom.rgbled(color_green)
            sigfox_network.send(bytes([protocol_version,now_temperature]))
            wdt.feed()
            if low_power_consumption_mode == 0:
                pycom.rgbled(color_black)

    if pycom.nvs_get('init_count') == 1:
        # only if first measurement completed
        if now_temperature >= (pycom.nvs_get('last_temp') + anomaly_detection_difference):
            if low_power_consumption_mode == 0:
                print("sending alarm... (red:%s;v:%s)" % (now_temperature, protocol_version))

            pycom.rgbled(color_red)
            sigfox_network.send(bytes([protocol_version,now_temperature]))
            pycom.rgbled(color_black)
            pycom.nvs_set('interval', 0)
            #this_interval=0
            already_sent=1
            wdt.feed()

    pycom.nvs_set('last_temp', now_temperature )
#    old_temperature=now_temperature

    if already_sent == 0:
        # only end if not already red status
        if (intervals == 1.0) or (send_all_data == 1):
            if low_power_consumption_mode == 0:
                print("sending... (green:%s;v:%s)" % (now_temperature,protocol_version))
            pycom.rgbled(0x007f00)
            sigfox_network.send(bytes([protocol_version,now_temperature]))
            #pybytes.send_virtual_pin_value(False,15,int(now_temperature))
            #this_interval=0
            pycom.nvs_set('interval', 0)
            pycom.rgbled(color_black)

    wdt.feed()
    if low_power_consumption_mode == 0:
        time.sleep(measurement_interval)
    else:
        py.setup_sleep(measurement_interval)
        py.go_to_sleep()

    #init_count = 1
    pycom.nvs_set('init_count', 1)

sigfox_network.close()
