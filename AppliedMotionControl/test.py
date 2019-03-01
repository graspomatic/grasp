import socket
from struct import pack

UDP_IP = "10.10.10.11"
UDP_PORT = 7775

print("UDP target IP:", UDP_IP)
print("UDP target port:", UDP_PORT)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", 60649))

message = "RV"
c = pack("BB", 0, 7) + bytes(message, "utf-8") + pack("B", 13)

if not sock.sendto(c, (UDP_IP, UDP_PORT)):
      raise Exception("Unable to send UDP command to motor")

data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes

print(addr)
print(data)
print(data[2:len(data)-1])

message = "AC25"
c = pack("BB", 0, 7) + bytes(message, "utf-8") + pack("B", 13)
sock.sendto(c, (UDP_IP, UDP_PORT))

message = "DE25"
c = pack("BB", 0, 7) + bytes(message, "utf-8") + pack("B", 13)
sock.sendto(c, (UDP_IP, UDP_PORT))

message = "VE5"
c = pack("BB", 0, 7) + bytes(message, "utf-8") + pack("B", 13)
sock.sendto(c, (UDP_IP, UDP_PORT))

message = "FL20000"
c = pack("BB", 0, 7) + bytes(message, "utf-8") + pack("B", 13)
sock.sendto(c, (UDP_IP, UDP_PORT))

data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes

print(addr)
print(data)
print(data[2:len(data)-1])

sock.shutdown(1)
sock.close()
