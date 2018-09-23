# ################################################################
# ########   imports
# ################################################################
# ----------------------------------------------------------------
import sys
from network import Sigfox

import machine
import time
from machine import RTC
from machine import WDT
# sdcard
from machine import SD
import os

import socket
import binascii
import struct

import pycom
from pysense import Pysense
from LIS2HH12 import LIS2HH12
from SI7006A20 import SI7006A20
from LTR329ALS01 import LTR329ALS01
from MPL3115A2 import MPL3115A2,ALTITUDE,PRESSURE

import _thread
import gc

py = Pysense()

# ################################################################
# ########   functions
# ################################################################

def init_sd_card(format_bool):
    sd = SD()
    print("Formatting SD card ...")
    os.mount(sd,"/sd")
    if format_bool == True:
        os.mkfs("/sd")
    print("SD card formatted...")

def log_sd_card(message):
    try:
        sd = SD()
        f = open("/sd/syf.log", "a")
        f.write(message+"\n")
        f.close()
    except Exception as e:
        print("Error while accessing sd card...")
        print("*************************************")
        print(str(e))
        print("*************************************")

def do_garbage_collection():
        free = gc.mem_free()
        if free < 30000:
            gc.collect()
            logging("GC - memory allocated = %s" % gc.mem_alloc())
            logging("GC - free memory = %s" % gc.mem_free())

def sigfox_init():
    global sigfox_network

    # !!!!!!!!!!!!!!!!! CHECK REGION !!!!!!!!!!!!!!!!!
    sigfox = Sigfox(mode=Sigfox.SIGFOX, rcz=Sigfox.RCZ1)
    # !!!!!!!!!!!!!!!!! CHECK REGION !!!!!!!!!!!!!!!!!

    logging("Sigfox device id: %s" % str(binascii.hexlify(sigfox.id())))
    logging("Sigfox PAC      : %s" % str(binascii.hexlify(sigfox.pac())))
    # create a Sigfox socket
    sigfox_network = socket.socket(socket.AF_SIGFOX, socket.SOCK_RAW)
    # make the socket blocking
    sigfox_network.setblocking(True)
    # configure it as uplink only
    sigfox_network.setsockopt(socket.SOL_SIGFOX, socket.SO_RX, False)

def sigfox_send(format,data):
    global sigfox_network
    raw = bytearray(struct.pack(str(format), data))
    logging("Sending data to Sigfox network: %s" % raw)
#    logging("Sent bytes=" + str(sigfox_network.send(raw)))
    logging("Data sent to Sigfox.")

def sigfox_terminate():
    global sigfox_network
    sigfox_network.close()

def logging(msg):
    rtc = machine.RTC()
    t = rtc.now()
    logstring ="%s-%s-%s %s:%s:%s.%s : %s" % ('{:04d}'.format(t[0]), '{:02d}'.format(t[1]), '{:02d}'.format(t[2]), '{:02d}'.format(t[3]), '{:02d}'.format(t[4]), '{:02d}'.format(t[5]), '{:06d}'.format(t[6]), msg)
    print(logstring)
    log_sd_card(logstring)

def get_sensors_mp_temp():
    global py
    mp = MPL3115A2(py,mode=ALTITUDE) # Returns height in meters. Mode may also be set to PRESSURE, returning a value in Pascals
    return mp.temperature()

def get_sensors_mp_altitude():
    global py
    mp = MPL3115A2(py,mode=ALTITUDE) # Returns height in meters. Mode may also be set to PRESSURE, returning a value in Pascals
    return mp.altitude()

def get_sensors_mp_pressure():
    global py
    mpp = MPL3115A2(py,mode=PRESSURE)
    return mpp.pressure()

def get_sensors_si_temp():
    global py
    si = SI7006A20(py)
    return si.temperature()

def get_sensors_si_humidity():
    global py
    si = SI7006A20(py)
    return si.humidity()

def get_sensors_si_dew_point():
    global py
    si = SI7006A20(py)
    return si.dew_point()

def get_sensors_si_humid_ambient():
    global py
    si_ambient=24.4
    si = SI7006A20(py)
    return si.humid_ambient(si_ambient)

def get_sensors_lt_light():
    global py
    lt = LTR329ALS01(py)
    return lt.light()

def get_sensors_li_acceleration():
    global py
    li = LIS2HH12(py)
    return li.acceleration()

def get_sensors_li_roll():
    global py
    li = LIS2HH12(py)
    return li.roll()

def get_sensors_li_pitch():
    global py
    li = LIS2HH12(py)
    return li.pitch()

def get_sensors_py_battery():
    global py
    py = Pysense()
    return py.read_battery_voltage()

def set_led(color):
    pycom.rgbled(color)


# ################################################################
# ########   threads
# ################################################################
def thread_send_sigfox(arg):
    global py
    while True:
#        do_garbage_collection()

        this_sensor_battery=get_sensors_py_battery()
        this_sensor_temp=get_sensors_mp_temp()
        logging("Sensor 'battery' data = " + str(this_sensor_battery))
        logging("Sensor 'temp' data    = " + str(this_sensor_temp))
        raw = bytearray(struct.pack("f", this_sensor_battery)+struct.pack("f", this_sensor_temp))
        logging("Sent bytes            = " + str(sigfox_network.send(raw)))

        set_led(0x330000)
        time.sleep(1)
        logging("Data sent to Sigfox.")
        set_led(0x000000)

        # watchdog thread feed
        wdt.feed()
        # waiting 15min to send new data (=900)
#        machine.idle()
        time.sleep(900)
    sigfox_terminate()

def thread_heartbeat(arg):
    global py
    while True:
        set_led(0x000033)
        time.sleep(0.3)
        set_led(0x000000)
        machine.idle()
        time.sleep(60)

# ################################################################
# ########   main
# ################################################################
# init
pycom.heartbeat(False)
set_led(0x000000)
gc.enable()
# init watchdog thread
init_sd_card(False)

# start main
logging("")
logging("")
logging("#################################################")
logging("##### SaveYourFridge v0.1 2018-09-24        #####")
logging("#################################################")
logging("")
logging(os.uname())
logging("Initializing watch dog thread (1200 seconds/20mins)...")
wdt = WDT(timeout=1200000)  # enable it with a timeout of 1 seconds (1000)*1200 (=20min)
wdt.feed()

# init treads
sigfox_init()
_thread.start_new_thread(thread_send_sigfox, ("",))
_thread.start_new_thread(thread_heartbeat, ("",))
