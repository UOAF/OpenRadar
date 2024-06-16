"""Standalone python script to read a .ACMI file and host a single client Tacview Real Time Telemetry stream"""

import socket
import time
from zipfile import ZipFile

filename = "Data\\2024-06-03_19-09-42_converted.zip.acmi"
timemultiplier = 32.0

# Read file as text into into acmidata
acmidata = list()

if filename.endswith(".zip.acmi"):
    with ZipFile(filename) as zfile:
        if "acmi.txt" in zfile.namelist():
            with zfile.open("acmi.txt") as file:
                acmidata = [line.decode('utf-8') for line in file.readlines()]
        else:
            quit()

elif filename.endswith(".acmi") or filename.endswith(".txt"):
    with open(filename, 'r', encoding='utf-8') as file:
        acmidata = file.readlines()
else:
    quit()

# create an INET, STREAMing socket
serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# bind the socket to a public host, and a well-known port
serversocket.bind(("localhost", 42674))
# become a server socket
serversocket.listen(5)   

while True:
        
    try:
        # accept connections from outside
        (clientsocket, address) = serversocket.accept()

        handshake = "XtraLib.Stream.0\nTacview.RealTimeTelemetry.0\nHost streamtest\n\0".encode('utf-8')

        clientsocket.sendall(handshake)

        # Wait for client to send handshake
        time.sleep(0.1)

        # Read the client handshake
        recieved = bytes()
        while True:
            chunk = 1024
            bytes_recv = clientsocket.recv(chunk)
            recieved += bytes_recv
            if len(bytes_recv) < chunk: break

        # Exit if the client handshake fails
        print(recieved)
        if len(recieved) == 0:
            clientsocket.close()
            print("Bad Handshake")
            quit()

        # send acmi data over socket
        buffer = ""
        lastbuffer = ""
        lastbuffer_time = 0
        for line in acmidata:
            buffer += line
            if line.startswith("#"):
                cur_time = float(line[1:])
                if lastbuffer_time > 0: time.sleep((cur_time-lastbuffer_time)/timemultiplier)
                clientsocket.sendall(lastbuffer.encode('utf-8'))
                lastbuffer = buffer
                lastbuffer_time = cur_time
                buffer = ""

        clientsocket.close()
    except ConnectionResetError:
        print("ConnectionResetError")        
