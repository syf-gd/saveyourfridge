from network import Sigfox
import socket
import ubinascii

# init Sigfox for RCZ1 (Europe)
sigfox = Sigfox(mode=Sigfox.SIGFOX, rcz=Sigfox.RCZ1)

# create a Sigfox socket
s = socket.socket(socket.AF_SIGFOX, socket.SOCK_RAW)

print("ID ", ubinascii.hexlify(sigfox.id()))
print("PAC ", ubinascii.hexlify(sigfox.pac()))
 # make the socket blocking
s.setblocking(True)

# configure it as uplink only
s.setsockopt(socket.SOL_SIGFOX, socket.SO_RX, False)

# send some bytes
print(s.send(bytes([0x48, 0x65, 0x6C,  0x6C, 0x6F, 0x20, 0x50, 0x79, 0x63, 0x6F, 0x6D, 0x21])))
