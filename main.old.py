# ################################################################
# ########   vars
# ################################################################
WAITTIME_SLEEP=900
WAITTIME_DEEPSLEEP=1200000

# ################################################################
# ########   imports
# ################################################################
# ----------------------------------------------------------------
import sys

from network import Sigfox
import socket
import ubinascii
import struct

import time
import machine
from machine import RTC
from machine import WDT

import pycom
from pysense import Pysense
#from LIS2HH12 import LIS2HH12
#from SI7006A20 import SI7006A20
#from LTR329ALS01 import LTR329ALS01
from MPL3115A2 import MPL3115A2,ALTITUDE,PRESSURE

py = Pysense()

# ################################################################
# ########   main
# ################################################################
# init
pycom.heartbeat(True)
# init watchdog thread
py.setup_int_wake_up(True, True)

sigfox = Sigfox(mode=Sigfox.SIGFOX, rcz=Sigfox.RCZ1)
# create a Sigfox socket
s = socket.socket(socket.AF_SIGFOX, socket.SOCK_RAW)
print("ID ", ubinascii.hexlify(sigfox.id()))
print("PAC ", ubinascii.hexlify(sigfox.pac()))
# make the socket blocking
s.setblocking(True)
# configure it as uplink only
s.setsockopt(socket.SOL_SIGFOX, socket.SO_RX, False)


wdt = WDT(timeout=WAITTIME_DEEPSLEEP)  # enable it with a timeout of 1 seconds (1000)*1200 (=20min)
wdt.feed()

while True:
    rtc = machine.RTC()
    t = rtc.now()
#    print("%s-%s-%s %s:%s:%s.%s : %s" % ('{:04d}'.format(t[0]), '{:02d}'.format(t[1]), '{:02d}'.format(t[2]), '{:02d}'.format(t[3]), '{:02d}'.format(t[4]), '{:02d}'.format(t[5]), '{:06d}'.format(t[6]), "Running..."))

    _battery=py.read_battery_voltage()
    _temperature=MPL3115A2(py,mode=ALTITUDE).temperature()
#    print("%s , %s" % (_battery,_temperature))
    print(s.send(bytearray(struct.pack("f", _battery)+struct.pack("f", _temperature))))

    wdt.feed()
    py.setup_sleep(WAITTIME_SLEEP)
    py.go_to_sleep()
