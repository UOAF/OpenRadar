import socket
import queue
import threading

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

    def run(self):
        clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientsocket.connect(("localhost", 42674))
        # clientsocket.connect(("bms.uoaf.net", 42674))

        # Send handshake to host
        handshake = "XtraLib.Stream.0\nTacview.RealTimeTelemetry.0\nClient OpenRadar\n\0".encode('utf-8')
        clientsocket.sendall(handshake)

        buf = Buffer(clientsocket)

        # Get handshake from server # TODO parse server name out of handshake and do something with it
        handshake = buf.get_handshake()
        print(handshake)

        # Put lines from the socket into the queue while socket is open
        while True:
            line = buf.get_line()
            if line is None:
                break
            self.queue.put(line)

        # Indicate that the thread has finished its work
        self.queue.put(None)
