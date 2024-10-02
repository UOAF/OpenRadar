import socket
import queue
import threading
from time import sleep

import config

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
        super(TRTTClientThread, self,).__init__(daemon=True) # Call the init for threading.Thread
        self.queue = queue
        self.connected = False
        self.connecting = True
        self.quit = False

        server = config.app_config.get("server", "address", str) # type: ignore
        port = config.app_config.get("server", "port", int) # type: ignore
        self.server = (server, port)
        self.num_retries = int( config.app_config.get("server", "retries", int) ) # type: ignore
        self.servername = ""
        self.clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


    def run(self):
        
        retries = 0
        while not self.quit:

            if self.connecting:
            
                if (retries < self.num_retries or self.num_retries == 0):
                    try:
                        self.clientsocket.connect(self.server)
                        self.connecting = False
                        self.connected = True
                    except ConnectionRefusedError:
                        retries += 1
                        print(f"Connection refused, retrying in 10 seconds {retries}/{self.num_retries}")
                        sleep(10)
                else:
                    print("Failed to connect to server")
                    self.connecting = False
                    self.connected = False
                    
            if self.connected:
                
                buf = Buffer(self.clientsocket)
                
                if not self.performHandshake(buf):
                    print("Tacview Handshake failed")
                    self.disconnect()
                
                self.process_data(buf) # blocking call
                print("Disconnected from server")

            sleep(1)
                
    def stop(self):
        self.quit = True
        self.disconnect()            
    
    def connect(self, server: str, port: int) -> bool:
        
        if self.connected:
            return False
        config.app_config.set("server", "address", server)
        config.app_config.set("server", "port", port)
        self.server = (server, port)
        self.connecting = True
        return True
        
    def process_data(self, buf: Buffer):
        # Put lines from the socket into the queue while socket is open
        while self.connected and not self.quit:
            line = buf.get_line()
            if line is None:
                self.disconnect()
                break
            self.queue.put(line)

        # Indicate that the thread has finished its work
        self.queue.put(None)   
                
    def performHandshake(self, buf: Buffer, password: str = "") -> bool:
        
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
        self.connecting = False
        self.servername = ""
        self.clientsocket.close()
    
