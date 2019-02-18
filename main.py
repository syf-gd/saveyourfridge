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
measurement_interval=300            # #[30]=seconds a measurement will be done (300=>5 minutes)
transmission_interval=900           # #[900]=seconds a message will be sent (independently of alarm) (900=>15 minutes)
temperature_compression_factor=2    # #[2]=factor of temperature compression 
temperature_correction_factor=80    # #[80]=temperature correction factor
anomaly_detection_difference=4      # #[2]=differences in degrees(celsius) to send alarm by device
low_power_consumption_mode=1        # 0/[1]=send device to deep sleep mode (attention: system is not connectable anymore)
send_data_every_interval=0          # [0]/1=send every measurement
do_signal_test=0                    # 0/[1]=do signal strength test at boot
protocol_version=1                  # #=1-254 (change, if data format changed)
rssi_dbm_limit=-135                 # #[135]=limit of rssi strength (-135...-122)
disable_low_power_on_usb=1          # 0/[1]=disable low power mode if usb connection is detected
usb_power_voltage_indication=4.2    # #[4.2]=voltage limit to detect usb connection

# protocol versions:
# (1)   initial version
#       AABB; AA=protocaol version, BB=temperature
# (?)
#
# (255) FFFF00; AA=protocol version; 00=signal test message (3 Bytes!)

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
color_white=0x222222

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
    interval = int(nvram_read('interval'))
    interval += 1
    nvram_write('interval', interval)

def console(message):
    if low_power_consumption_mode == 0:
        now = time.localtime()
        print("%s-%02d-%02d %02d:%02d:%02d [%s] %s" % (now[0],now[1],now[2],now[3],now[4],now[5], device_id, message))

def nvram_read(key):
    ret=pycom.nvs_get(key)
    console("NVRAM read '%s'=%s" % (str(key), str(ret)))
    return ret

def nvram_write(key,value):
    console("NVRAM write '%s'=%s" % (str(key), str(value)))
    pycom.nvs_set(key, int(value))

def led_blink(color,duration,loop=1):
    # loop=0 infinite
    if loop > 0:
        for x in range(loop):
            # if duration = 0, permanent on
            console("LED on: %s, %s, %s" % (str(color), str(duration), str(loop)))
            pycom.rgbled(color)
            if duration > 0:
                time.sleep(duration)
                pycom.rgbled(color_black)
    else:
        while True:
            console("LED on: %s, %s, %s" % (str(color), str(duration), str(loop)))
            pycom.rgbled(color)
            time.sleep(duration)
            pycom.rgbled(color_black)
            time.sleep(duration)

def led_signal_error():
    led_blink(color_red, 0.2, 0)

def send_sigfox_message(message):
    try:
        sigfox_network.send(message)
    except:
        led_signal_error

py = Pysense()


# ################################################################
# ########   main
# ################################################################
pycom.heartbeat(False)

gc.enable()

wdt = WDT(timeout=1200000)  # enable it with a timeout of 1 seconds (1000)*1200 (=20min)
wdt.feed()

battery_voltage=py.read_battery_voltage()

sigfox = Sigfox(mode=Sigfox.SIGFOX, rcz=Sigfox.RCZ1)
sigfox_network = socket.socket(socket.AF_SIGFOX, socket.SOCK_RAW)
sigfox_network.setblocking(True)
sigfox_network.setsockopt(socket.SOL_SIGFOX, socket.SO_RX, True) # true=downlink
device_id = binascii.hexlify(sigfox.id())
device_pac = binascii.hexlify(sigfox.pac())
wake_up_reason=py.get_wake_reason()

if disable_low_power_on_usb == 1:
    if battery_voltage > usb_power_voltage_indication:
        low_power_consumption_mode=0        
        console("USB connection detected, disable low power mode (voltage=%s)" % (str(py.read_battery_voltage())))
        wdt.feed()

if low_power_consumption_mode == 0:
    led_duration = 0
else:
    led_duration = 0.2

# WAKE_REASON_POWERON = 0       # Accelerometer activity/inactivity detection
# WAKE_REASON_ACCELEROMETER = 1 # Accelerometer activity/inactivity detection
# WAKE_REASON_PUSH_BUTTON = 2   # Pytrack/Pysense reset buttom
# WAKE_REASON_TIMER = 4         # Normal timeout of the sleep interval
# WAKE_REASON_INT_PIN = 8       # INT pinmy_wake_up_reason=py.get_wake_reason()
console("Wakeup reason: %s (last saved reason: %s)" % (str(wake_up_reason), str(nvram_read('saved_wu_status'))))
# lwus=last wake-up status
nvram_write('saved_wu_status', int(wake_up_reason))


console("DEVICE ID : %s" % (device_id))
console("DEVICE PAC: %s" % (device_pac))
wdt.feed()

# ################################################################
# ########   pre-check: signal strength
# ################################################################

if do_signal_test == 1 and wake_up_reason != 4:
    # do signal test only if booted up and option is set
    led_blink(color_white, led_duration, 3)

    # test uplink/downlink - if successful, send green light, else red light
    signal_strength=-500        # default value
    console("send strength test message")
    try:
        error_position="send"
        sigfox_network.send(bytes([255,255,0]))

        error_position="send2"
        console("waiting for feedback message")

        error_position="recv"
        sigfox_network.recv(32)

        error_position="rssi"
        signal_strength=sigfox.rssi()
        console("Signal Strength received:" + str(signal_strength))
        wdt.feed()

    except:
        # every error will stop strength test
        signal_strength=-500
        console("error while waiting for signal strength test (position=%s)" % (error_position))

    console("received signal stregth: %s" % (str(signal_strength)))
    if signal_strength < rssi_dbm_limit:
        console("ERROR: signal stregth below limit: %s < %s" % (str(signal_strength),str(rssi_dbm_limit)))
        led_signal_error()
    else:
        console("signal stregth okay : %s >= %s" % (str(signal_strength),str(rssi_dbm_limit)))
        nvram_write('signaltest_done', 1)
    wdt.feed()
    led_blink(color_black,led_duration)


# ################################################################
# ########   measurement loop
# ################################################################
# sigfox: change to uplink messages only
sigfox_network.setsockopt(socket.SOL_SIGFOX, socket.SO_RX, False) # false=only uplink
if wake_up_reason != 4:
    # reset vars if re-powered by USB/battery (not by deep sleep)
    nvram_write('interval', 0)        # waiting time interval countdown
    nvram_write('last_temp', 0)       # save of last temperature (to detect anomaly)
    nvram_write('first_run', 1)       # save of first run status (1=first run;0=second+ run)

while True:
    # interval logic: every time the counter iszero (0), a message is sent
    # counter will be counted up from zero to "interval_max"
    # counter is resetted if it reaches interval_max (equal or beyond)
    # benefit: after a restart, the initial message is sent
    interval_max = transmission_interval/measurement_interval
    if nvram_read('interval') > interval_max:
        nvram_write('interval', 0)
    if send_data_every_interval == 1:
            # if data should be sent every time, the var 'interval' have to be reset
        nvram_write('interval', 0)
        
    # round to floor
    led_blink(color_blue, led_duration)
    console("measuring temperature...")
    original_temperature=MPL3115A2(py,mode=ALTITUDE).temperature()
    now_temperature = int(original_temperature*temperature_compression_factor+temperature_correction_factor)
    led_blink(color_black, led_duration)

    console("interval countdown  : %s < %s" % (str(nvram_read('interval')),str(interval_max)))
    console("temperature (now)   : %s ((temp-%s)/%s=%s)" % (now_temperature, temperature_correction_factor, temperature_compression_factor, original_temperature))
    console("temperature (last)  : %s ((temp-%s)/%s)"  % (nvram_read('last_temp'), temperature_correction_factor, temperature_compression_factor))
    console("temperature anomaly : %s (>=)" % (anomaly_detection_difference))
    wdt.feed()

    if nvram_read('first_run') != 1:
        if now_temperature >= (nvram_read('last_temp') + anomaly_detection_difference):
            # sending alarm if anomaly detected
            console("===> sending alarm... (red:%s;v:%s)" % (now_temperature, protocol_version))
            led_blink(color_red, led_duration)
            send_sigfox_message(bytes([protocol_version,now_temperature]))
            led_blink(color_black, led_duration)
            nvram_write('interval',999) # set interval to limit, so next loop the cycle is starting over
            wdt.feed()

    # sending first run and normal if counter reaches limit
    if nvram_read('interval') == 0:
            console("===> sending... (green:%s;v:%s)" % (now_temperature,protocol_version))
            led_blink(color_green, led_duration)
            send_sigfox_message(bytes([protocol_version,now_temperature]))
            wdt.feed()
            led_blink(color_black, led_duration)

    countInterval()

    nvram_write('last_temp', now_temperature )
    nvram_write('first_run', 0)

    wdt.feed()
    if low_power_consumption_mode == 0:
        console("going to sleep (%s seconds)" %(measurement_interval))
        sigfox_network.close()
        time.sleep(measurement_interval)
    else:
        console("going to deep sleep (%s seconds)" %(measurement_interval))
        sigfox_network.close()
        py.setup_sleep(measurement_interval)
        py.go_to_sleep()