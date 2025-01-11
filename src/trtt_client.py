import socket
import queue
import threading
from time import sleep
from dataclasses import dataclass
from enum import Enum, auto

import datetime

from tomlkit import date

@dataclass
class ThreadStatus:
    status_enum: int
    status_msg: str
    status_color: tuple[int, int, int] | str
    is_connected: bool

class ThreadState(ThreadStatus, Enum):
    DISCONNECTED = auto(), "Disconnected", '#dbdbdb', False  # White
    CONNECTING = auto(), "Connecting", '#f5f52c', False     # Yellow
    CONNECTED = auto(), "Connected", '#2cf562', True       # Green
    FAILED = auto(), "Failed", '#f52c4a', False            # Red
    TERMINATED = auto(), "Terminated", '#f52c4a', False    # Red

class Buffer:
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.buffer = b''

    def get_handshake(self):
        return self.get_line("\0")

    def get_line(self, separator="\n"):
        try:
            while separator.encode("utf-8") not in self.buffer:
                data = self.sock.recv(1024)
                if not data:  # socket closed
                    return None
                self.buffer += data
            line, sep, self.buffer = self.buffer.partition(separator.encode("utf-8"))
            return line.decode()
        except (ConnectionAbortedError, ConnectionResetError, OSError):
            return None

class TRTTClientThread(threading.Thread):
    def __init__(self, queue: queue.Queue):
        super().__init__(daemon=True)
        self.queue = queue
        self.connected = False
        self.connecting = False
        self.quit = False
        self.status = ThreadState.DISCONNECTED
        self.state_info = ""

        self.server = None
        self.clientsocket = None
        self.tacview_password = ""
        self.max_retries = 3
        self.retries = 0
        
        self.connection_time = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)

        self.lock = threading.Lock()

    def run(self):
        retry_delay = 5  # Initial retry delay in seconds
        while not self.quit:
            with self.lock:
                if self.connecting:
                    self._set_status(ThreadState.CONNECTING, "Trying connection")
                    if self.clientsocket and self.server and (self.retries < self.max_retries or self.max_retries == 0):
                        try:
                            self.clientsocket.settimeout(10)
                            self.clientsocket.connect(self.server)
                            self.clientsocket.settimeout(None)
                            self.connecting = False
                            self.connected = True
                            self.retries = 0 # Reset retries on successful connection
                            self.connection_time = datetime.datetime.now()
                        except (ConnectionRefusedError, socket.timeout):
                            self.retries += 1
                            self._set_status(ThreadState.CONNECTING, f"Retry {self.retries}/{self.max_retries}")
                            sleep(retry_delay)
                        continue
                    else:
                        self._set_status(ThreadState.FAILED, f"Failed to connect after {self.retries} retries")
                        self.retries = 0 # Reset retries on failed connection
                        self.connecting = False
                        self.connected = False

            # Process data outside the lock
            if self.connected and self.clientsocket:
                buf = Buffer(self.clientsocket)
                if not self._perform_handshake(buf, self.tacview_password):
                    self._set_status(ThreadState.FAILED, "Handshake failed")
                    self.disconnect()
                    
                with self.lock:
                    self._set_status(ThreadState.CONNECTED, "Connected")
                    
                self._process_data(buf)
                
                with self.lock:
                    self._set_status(ThreadState.DISCONNECTED, "")

            sleep(1)

    def stop(self):
        self.quit = True
        self.disconnect()

    def connect(self, server: str, port: int, password: str = "", retries: int = 3):
        # Disconnect outside the lock to avoid deadlock
        self.disconnect()
        with self.lock:
            if self.connected or self.connecting:
                return False
            # Reset connection state
            self.connected = False
            self.connecting = False
            # Create a new socket
            self.clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server = (server, port)
            self.tacview_password = password
            self.max_retries = retries
            self.connecting = True
            return True

    def disconnect(self):
        if self.clientsocket:
            try:
                self.clientsocket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.clientsocket.close()
            self.clientsocket = None
        with self.lock:
            self.connected = False
            self.connecting = False

    def get_status(self):
        return self.status, self.state_info

    def _process_data(self, buf: Buffer):
        while self.connected and not self.quit:
            line = buf.get_line()
            print(line)
            if line is None:
                with self.lock:
                    self.connected = False
                self.disconnect()
                self._set_status(ThreadState.DISCONNECTED, "Disconnected")
                break
            self.queue.put(line)
            print ("Put data in queue")
            
            hours, remainder = divmod((datetime.datetime.now() - self.connection_time).total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            self._set_status(ThreadState.CONNECTED, f"Connected for {int(hours)}h {int(minutes)}m {int(seconds)}s")
        self.queue.put(None)

    def _perform_handshake(self, buf: Buffer, password: str = "") -> bool:
        if not self.clientsocket:
            return False

        try:
            handshake = f"XtraLib.Stream.0\nTacview.RealTimeTelemetry.0\nClient OpenRadar\n{password}\0".encode('utf-8')
            self.clientsocket.sendall(handshake)
            response = buf.get_handshake()
            if response and response.startswith("XtraLib.Stream.0\nTacview.RealTimeTelemetry.0\n"):
                return True
        except socket.error:
            pass
        return False

    def _set_status(self, status: ThreadState, info: str):
        self.status = status
        self.state_info = info
