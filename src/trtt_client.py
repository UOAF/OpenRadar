import re
import socket
import queue
import threading
from time import sleep

class Buffer:

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.buffer = b''

    def get_handshake(self):
        return self.get_line("\0")
    
    def get_line(self, seperator="\n"):
        while seperator.encode("utf-8") not in self.buffer:
            data = self.sock.recv(1024) #TODO try except
            if not data: # socket closed
                return None
            self.buffer += data
        line,sep,self.buffer = self.buffer.partition(seperator.encode("utf-8"))
        return line.decode()

class TRTTClientThread(threading.Thread):
    def __init__(self, queue: queue.Queue):
        super(TRTTClientThread, self).__init__() # Call the init for threading.Thread
        self.queue = queue
        self.connected = False
        self.server = ("localhost", 42674)
        #self.server = ("bms.uoaf.net", 42674)
        self.num_retries = 5
        self.servername = ""
        self.clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def run(self):
        
        retries = 0
        while retries < self.num_retries:
            try:
                self.connect(self.server)
                break
            except ConnectionRefusedError:
                retries += 1
                print(f"Connection refused, retrying in 10 seconds {retries}/{self.num_retries}")
                sleep(10)
        
    def connect(self, server: tuple):
        """ blocking call to connect to the server and start processing data
        """
        self.server = server
        self.clientsocket.connect(self.server)
        buf = Buffer(self.clientsocket)
        if self.do_handshake(buf):
            self.processing_loop(buf)
        else:
            print("Tacview Handshake failed")
            self.disconnect()
        
    def processing_loop(self, buf: Buffer):
         # Put lines from the socket into the queue while socket is open
         
        while self.connected:
            line = buf.get_line()
            if line is None:
                self.disconnect()
                break
            self.queue.put(line)

        # Indicate that the thread has finished its work
        self.queue.put(None)   
                
    def do_handshake(self, buf: Buffer, password: str = "") -> bool:
        
        handshake = f"XtraLib.Stream.0\nTacview.RealTimeTelemetry.0\nClient OpenRadar\n{password}\0".encode('utf-8')
        self.clientsocket.sendall(handshake)
        # Get handshake from server
        handshake = buf.get_handshake()
        
        if handshake is not None and handshake.startswith("XtraLib.Stream.0\nTacview.RealTimeTelemetry.0\n"):
            self.connected = True
            self.servername = handshake.split("\n")[2]
            return True
        else:
            return False

    def disconnect(self):
        self.connected = False
        self.servername = ""
        self.clientsocket.close()
    
