# ################################################################
# ########   imports
# ################################################################
# ----------------------------------------------------------------
import sys

from network import Sigfox
import socket
import ubinascii

import time
import machine
from machine import RTC
from machine import WDT

import pycom
from pysense import Pysense
#from LIS2HH12 import LIS2HH12
#from SI7006A20 import SI7006A20
#from LTR329ALS01 import LTR329ALS01
#from MPL3115A2 import MPL3115A2,ALTITUDE,PRESSURE

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


wdt = WDT(timeout=1200000)  # enable it with a timeout of 1 seconds (1000)*1200 (=20min)
wdt.feed()

while True:
    rtc = machine.RTC()
    t = rtc.now()
    print("%s-%s-%s %s:%s:%s.%s : %s" % ('{:04d}'.format(t[0]), '{:02d}'.format(t[1]), '{:02d}'.format(t[2]), '{:02d}'.format(t[3]), '{:02d}'.format(t[4]), '{:02d}'.format(t[5]), '{:06d}'.format(t[6]), "Running..."))

    print(s.send(bytes([0x48, 0x65, 0x6C,  0x6C, 0x6F, 0x20, 0x50, 0x79, 0x63, 0x6F, 0x6D, 0x21])))

    wdt.feed()
    py.setup_sleep(900)
    py.go_to_sleep()
