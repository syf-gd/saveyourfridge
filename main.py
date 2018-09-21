# ################################################################
# ########   imports
# ################################################################
# ----------------------------------------------------------------
import sys
from network import Sigfox

import machine
import time
from machine import RTC

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

def do_garbage_collection():
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
    logging("Sent bytes=" + str(sigfox_network.send(raw)))
    logging("Data sent to Sigfox.")

def sigfox_terminate():
    global sigfox_network
    sigfox_network.close()

def logging(msg):
    rtc = machine.RTC()
    t = rtc.now()
    logstring ="%s-%s-%s %s:%s:%s.%s : %s" % ('{:04d}'.format(t[0]), '{:02d}'.format(t[1]), '{:02d}'.format(t[2]), '{:02d}'.format(t[3]), '{:02d}'.format(t[4]), '{:02d}'.format(t[5]), '{:06d}'.format(t[6]), msg)
    print(logstring)

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
#def thread_get_sensordata(arg):
#    while True:
#        set_led(0x7f0000)
#        get_sensors_py_battery()
#        set_led(0x7f0000)
#        time.sleep(30)

def thread_send_sigfox(arg):
    global py

    # initial wait time to be sure sensor data were collected
    sigfox_init()
    time.sleep(30)
    while True:
        sigfox_send("f",get_sensors_mp_temp())
        # waiting 15min to send new data (=900)
        time.sleep(60)
    sigfox_terminate()

# ################################################################
# ########   main
# ################################################################
pycom.heartbeat(False)
set_led(0x000000)

#_thread.start_new_thread(thread_get_sensordata, ("",))
_thread.start_new_thread(thread_send_sigfox, ("",))
logging("Please wait...Sigfox loop running...")
