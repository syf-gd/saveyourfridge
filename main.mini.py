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

py = Pysense()

# ################################################################
# ########   functions
# ################################################################
def get_sensors_mp_temp():
    global py
    mp = MPL3115A2(py,mode=ALTITUDE) # Returns height in meters. Mode may also be set to PRESSURE, returning a value in Pascals
    return mp.temperature()

def get_sensors_py_battery():
    global py
    py = Pysense()
    return py.read_battery_voltage()


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

while True:
    sigfox_network.send(bytearray(struct.pack("f", get_sensors_py_battery())+struct.pack("f", get_sensors_mp_temp()))))
    wdt.feed()
    py.setup_sleep(900)
    py.go_to_sleep()

sigfox_network.close()
