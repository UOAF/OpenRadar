import socket
import queue
import threading
from time import sleep
from dataclasses import dataclass
from enum import Enum, auto

import datetime

from tomlkit import date
from logging_config import get_logger


@dataclass
class ThreadStatus:
    status_enum: int
    status_msg: str
    status_color: tuple[int, int, int] | str
    is_connected: bool


class ThreadState(ThreadStatus, Enum):
    DISCONNECTED = auto(), "Disconnected", '#dbdbdb', False  # White
    CONNECTING = auto(), "Connecting", '#f5f52c', False  # Yellow
    CONNECTED = auto(), "Connected", '#2cf562', True  # Green
    FAILED = auto(), "Failed", '#f52c4a', False  # Red
    TERMINATED = auto(), "Terminated", '#f52c4a', False  # Red


class Buffer:

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.buffer = b''
        self.logger = get_logger(f"{__name__}.Buffer")
        self.logger.debug("Buffer initialized for socket communication")

    def get_handshake(self):
        self.logger.debug("Getting handshake from buffer")
        result = self.get_line("\0")
        if result:
            self.logger.debug(f"Handshake received: {result[:50]}..." if len(result) >
                              50 else f"Handshake received: {result}")
        else:
            self.logger.warning("No handshake received or connection closed")
        return result

    def get_line(self, separator="\n"):
        try:
            bytes_received = 0
            while separator.encode("utf-8") not in self.buffer:
                data = self.sock.recv(1024)
                if not data:  # socket closed
                    self.logger.warning("Socket closed while reading data")
                    return None
                self.buffer += data
                bytes_received += len(data)

            line, sep, self.buffer = self.buffer.partition(separator.encode("utf-8"))
            decoded_line = line.decode()

            if separator == "\n":  # Regular data line
                self.logger.debug(f"Received data line ({len(decoded_line)} chars): {decoded_line[:100]}..."
                                  if len(decoded_line) > 100 else f"Received data line: {decoded_line}")

            return decoded_line
        except (ConnectionAbortedError, ConnectionResetError, OSError) as e:
            self.logger.error(f"Network error while reading data: {e}")
            return None
        except UnicodeDecodeError as e:
            self.logger.error(f"Unicode decode error: {e}")
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

        # Initialize logger
        self.logger = get_logger(f"{__name__}.TRTTClientThread")
        self.logger.info("TRTT Client thread initialized")

        # Statistics for logging
        self.total_messages_received = 0
        self.total_bytes_received = 0
        self.connection_attempts = 0

    def run(self):
        self.logger.info("TRTT Client thread started")
        retry_delay = 5  # Initial retry delay in seconds

        while not self.quit:
            with self.lock:
                if self.connecting:
                    self.connection_attempts += 1
                    self.logger.info(f"Connection attempt #{self.connection_attempts} to {self.server}")
                    self._set_status(ThreadState.CONNECTING, "Trying connection")

                    if self.clientsocket and self.server and (self.retries < self.max_retries or self.max_retries == 0):
                        try:
                            self.logger.debug(f"Setting socket timeout to 10 seconds for connection")
                            self.clientsocket.settimeout(10)
                            self.logger.debug(f"Attempting to connect to {self.server[0]}:{self.server[1]}")
                            self.clientsocket.connect(self.server)
                            self.clientsocket.settimeout(None)

                            self.connecting = False
                            self.connected = True
                            self.retries = 0  # Reset retries on successful connection
                            self.connection_time = datetime.datetime.now()

                            self.logger.info(f"Successfully connected to {self.server[0]}:{self.server[1]}")

                        except (ConnectionRefusedError, socket.timeout, OSError) as e:
                            self.retries += 1
                            self.logger.warning(
                                f"Connection attempt failed (attempt {self.retries}/{self.max_retries}): {e}")
                            self._set_status(ThreadState.CONNECTING, f"Retry {self.retries}/{self.max_retries}")
                            self.logger.debug(f"Sleeping for {retry_delay} seconds before retry")
                            sleep(retry_delay)
                        continue
                    else:
                        self.logger.error(f"Failed to connect after {self.retries} retries. Giving up.")
                        self._set_status(ThreadState.FAILED, f"Failed to connect after {self.retries} retries")
                        self.retries = 0  # Reset retries on failed connection
                        self.connecting = False
                        self.connected = False

            # Process data outside the lock
            if self.connected and self.clientsocket:
                self.logger.debug("Creating buffer for data processing")
                buf = Buffer(self.clientsocket)
                if not self._perform_handshake(buf, self.tacview_password):
                    self.logger.error("Handshake failed - disconnecting")
                    self._set_status(ThreadState.FAILED, "Handshake failed")
                    self.disconnect()
                else:
                    self.logger.info("Handshake completed successfully")

                with self.lock:
                    self._set_status(ThreadState.CONNECTED, "Connected")

                self.logger.info("Starting data processing loop")
                self._process_data(buf)
                self.logger.info("Data processing loop ended")

                with self.lock:
                    self._set_status(ThreadState.DISCONNECTED, "")

            sleep(1)

        self.logger.info("TRTT Client thread stopping")
        # Log final statistics
        self.logger.info(
            f"Session statistics - Messages: {self.total_messages_received}, Bytes: {self.total_bytes_received}, Attempts: {self.connection_attempts}"
        )

    def stop(self):
        self.logger.info("Stop requested for TRTT Client thread")
        self.quit = True
        self.disconnect()

    def connect(self, server: str, port: int, password: str = "", retries: int = 3):
        # Disconnect outside the lock to avoid deadlock
        self.logger.info(f"Connection request to {server}:{port} (retries: {retries})")
        self.disconnect()

        if password == "":
            password = "0"
            self.logger.debug("Using default password '0'")
        else:
            self.logger.debug("Using provided password")

        with self.lock:
            if self.connected or self.connecting:
                self.logger.warning("Already connected or connecting - ignoring connection request")
                return False

            # Reset connection state
            self.connected = False
            self.connecting = False

            try:
                # Create a new socket
                self.logger.debug("Creating new socket")
                self.clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server = (server, port)
                self.tacview_password = password
                self.max_retries = retries
                self.connecting = True

                self.logger.info(f"Socket created, ready to connect to {server}:{port}")
                return True

            except Exception as e:
                self.logger.error(f"Failed to create socket: {e}")
                return False

    def disconnect(self):
        self.logger.debug("Disconnect requested")

        if self.clientsocket:
            try:
                self.logger.debug("Shutting down socket")
                self.clientsocket.shutdown(socket.SHUT_RDWR)
            except OSError as e:
                self.logger.debug(f"Socket shutdown error (expected): {e}")
                pass

        try:
            if self.clientsocket:
                self.logger.debug("Closing socket")
                self.clientsocket.close()  # type: ignore
        except AttributeError:
            self.logger.debug("Socket was already None")
            pass

        self.clientsocket = None

        with self.lock:
            was_connected = self.connected
            self.connected = False
            self.connecting = False

        if was_connected:
            self.logger.info("Disconnected from server")
        else:
            self.logger.debug("Disconnect completed (was not connected)")

    def get_status(self):
        return self.status, self.state_info

    def _process_data(self, buf: Buffer):
        self.logger.debug("Starting data processing loop")
        message_count = 0
        last_stats_log = datetime.datetime.now()
        stats_interval = 30  # Log stats every 30 seconds

        while self.connected and not self.quit:
            line = buf.get_line()
            if line is None:
                self.logger.warning("Received None from buffer - connection likely closed")
                with self.lock:
                    self.connected = False
                self.disconnect()
                self._set_status(ThreadState.DISCONNECTED, "Disconnected")
                break

            # Update statistics
            self.total_messages_received += 1
            self.total_bytes_received += len(line.encode('utf-8'))
            message_count += 1

            # Queue the message for processing
            self.queue.put(line)

            # Log periodic statistics
            now = datetime.datetime.now()
            if (now - last_stats_log).total_seconds() >= stats_interval:
                self.logger.debug(
                    f"Data stats: {message_count} messages in last {stats_interval}s, total: {self.total_messages_received}"
                )
                last_stats_log = now
                message_count = 0

            # Update connection time display
            hours, remainder = divmod((datetime.datetime.now() - self.connection_time).total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            self._set_status(ThreadState.CONNECTED, f"Connected for {int(hours)}h {int(minutes)}m {int(seconds)}s")

        self.logger.debug(f"Data processing loop ended. Total messages processed: {self.total_messages_received}")
        self.queue.put(None)

    def _perform_handshake(self, buf: Buffer, password: str = "") -> bool:
        if not self.clientsocket:
            self.logger.error("Cannot perform handshake - no socket available")
            return False

        try:
            handshake_msg = f"XtraLib.Stream.0\nTacview.RealTimeTelemetry.0\nOpenRadar\n{password}\0"
            handshake = handshake_msg.encode('utf-8')

            self.logger.debug(f"Sending handshake ({len(handshake)} bytes)")
            self.logger.debug(f"Handshake content: {handshake_msg.replace(password, '[PASSWORD]')}")

            self.clientsocket.sendall(handshake)
            self.logger.debug("Handshake sent, waiting for response")

            response = buf.get_handshake()
            if response:
                self.logger.debug(f"Handshake response received: {response[:100]}..." if len(response) >
                                  100 else f"Handshake response: {response}")

                if response.startswith("XtraLib.Stream.0\nTacview.RealTimeTelemetry.0\n"):
                    self.logger.info("Handshake successful - protocol accepted")
                    return True
                else:
                    self.logger.error(f"Handshake failed - unexpected response: {response}")
                    return False
            else:
                self.logger.error("Handshake failed - no response received")
                return False

        except socket.error as e:
            self.logger.error(f"Socket error during handshake: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during handshake: {e}")
            return False

    def _set_status(self, status: ThreadState, info: str):
        old_status = self.status
        self.status = status
        self.state_info = info

        # Log status changes
        if old_status != status:
            self.logger.info(f"Status changed: {old_status.name} -> {status.name} ({info})")
        else:
            self.logger.debug(f"Status update: {status.name} ({info})")
