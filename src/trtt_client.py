import socket
import queue
import threading
from time import sleep

from dataclasses import dataclass
from enum import Enum, auto

import pygame

import config
from messages import UI_SETTINGS_PAGE_SERVER_CONNECT, UI_SETTINGS_PAGE_SERVER_DISCONNECT, DATA_THREAD_STATUS, UI_SETTINGS_PAGE_REQUEST_SERVER_STATUS
from messages import RADAR_SERVER_CONNECTED, RADAR_SERVER_DISCONNECTED
@dataclass
class ThreadStatus:
    status_enum: int 
    status_msg: str
    status_color: tuple[int,int,int] | str
    is_connected: bool
    
class ThreadState(ThreadStatus, Enum):
    DISCONNECTED = auto(), "Disconnected", '#dbdbdb', False # White
    CONNECTING = auto(), "Connecting", '#f5f52c', False # Yellow
    CONNECTED = auto(), "Connected", '#2cf562', False # Green
    FAILED = auto(), "Failed", '#f52c4a', False # Red
    TERMINATED = auto(), "Terminated", '#f52c4a', False # Red
    
class Buffer:

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.buffer = b''

    def get_handshake(self):
        return self.get_line("\0")
    
    def get_line(self, seperator="\n"):
        try:
            while seperator.encode("utf-8") not in self.buffer:
                data = self.sock.recv(1024) #TODO try except
                if not data: # socket closed
                    return None
                self.buffer += data
            line,sep,self.buffer = self.buffer.partition(seperator.encode("utf-8"))
            return line.decode()
        except ConnectionAbortedError:
            return None

class TRTTClientThread(threading.Thread):
    def __init__(self, queue: queue.Queue):
        super(TRTTClientThread, self,).__init__(daemon=True) # Call the init for threading.Thread
        self.queue = queue
        self.connected = False
        self.connecting = False
        self.quit = False
        self.status:ThreadState #state and info string
        self.state_info: str = ""
        
        self.set_status(ThreadState.DISCONNECTED, "Not connected")
        
        self.server = None
        server = str(config.app_config.get("server", "address", str)) # type: ignore
        port = int(config.app_config.get("server", "port", int)) # type: ignore
        if server is None:
            self.set_status(ThreadState.FAILED, "No server address set")
        elif port is None:
            self.set_status(ThreadState.FAILED, "No server port set")
        else:
            self.server = (server, port)
            
        autoconnect = config.app_config.get("server", "autoconnect", bool) # type: ignore

        
        self.tacview_password = str(config.app_config.get("server", "password", str)) # type: ignore
            
        self.num_retries = int( config.app_config.get("server", "retries", int) ) # type: ignore
        self.servername = ""
        self.clientsocket = None
        
        if autoconnect and self.server is not None:
            self.connect(server, port)

    def run(self):
        
        retries = 0
        while not self.quit:

            if self.connecting:
                self.set_status(ThreadState.CONNECTING, "Trying connection")
                
                if self.clientsocket is None:
                    print("Uh oh clientsocket")
                elif self.server is None:
                    print("Uh oh server")
                elif (retries < self.num_retries or self.num_retries == 0):
                    try:
                        self.clientsocket.connect(self.server)
                        self.connecting = False
                        self.connected = True
                    except ConnectionRefusedError:
                        retries += 1
                        self.set_status(ThreadState.CONNECTING ,f"Connection refused, retrying in 10 seconds {retries}/{self.num_retries}")
                        sleep(10)
                else:
                    self.set_status(ThreadState.FAILED, "Failed to connect to server")
                    self.connecting = False
                    self.connected = False
                    
            if self.connected and self.clientsocket is not None:
                
                buf = Buffer(self.clientsocket)
                
                if not self.performHandshake(buf, self.tacview_password):
                    self.set_status(ThreadState.FAILED, "Tacview Handshake failed")
                    self.disconnect()
                
                self.set_status(ThreadState.CONNECTED, "")
                pygame.event.post(pygame.event.Event(RADAR_SERVER_CONNECTED))
                self.process_data(buf) # blocking call
                self.set_status(ThreadState.DISCONNECTED, "Disconnected from server")
                pygame.event.post(pygame.event.Event(RADAR_SERVER_DISCONNECTED))


            sleep(1)
                
    def stop(self):
        self.quit = True
        self.disconnect()            
    
    def connect(self, server: str, port: int) -> bool:
        
        if self.connected:
            return False
        self.clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
                self.set_status(ThreadState.DISCONNECTED, "Disconnected from server")
                break
            self.queue.put(line)

        # Indicate that the thread has finished its work
        self.queue.put(None)   
                
    def performHandshake(self, buf: Buffer, password: str = "") -> bool:
        
        if self.clientsocket is None:
            return False
        
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
        if self.clientsocket is not None:
            self.clientsocket.close()
            self.clientsocket = None
        
    def set_status(self, status: ThreadState, info: str):
        self.status = status
        self.state_info = info
        event_data = {'status': self.status, 'info': self.state_info}
        pygame.event.post(pygame.event.Event(DATA_THREAD_STATUS, event_data))
        
    def process_events(self, event: pygame.event.Event) -> bool:
        
        consumed = False
        
        if event.type == UI_SETTINGS_PAGE_SERVER_CONNECT:
            ip, port = event.server, event.port
            self.connect(ip, port)
            consumed = True
                
        elif event.type == UI_SETTINGS_PAGE_SERVER_DISCONNECT:
            self.disconnect()
            consumed = True

        elif event.type == UI_SETTINGS_PAGE_REQUEST_SERVER_STATUS:
            event_data = {'status': self.status, 'info': self.state_info}
            pygame.event.post(pygame.event.Event(DATA_THREAD_STATUS, event_data))
            
        return consumed
