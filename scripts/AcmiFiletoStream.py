"""Standalone python script to read a .ACMI file and host a single client Tacview Real Time Telemetry stream"""

import socket
import time
import argparse
import sys
from zipfile import ZipFile
import os

# Default ACMI file to stream if none specified
DEFAULT_ACMI_FILE = os.path.join("Data", "2024-09-16_19-09-36_converted.zip.acmi")


def read_acmi_file(filename):
    """Read ACMI file data into a list of lines."""
    acmidata = list()

    if filename.endswith(".zip.acmi"):
        with ZipFile(filename) as zfile:
            if "acmi.txt" in zfile.namelist():
                with zfile.open("acmi.txt") as file:
                    acmidata = [line.decode('utf-8') for line in file.readlines()]
            else:
                print(f"Error: No acmi.txt found in {filename}")
                return None

    elif filename.endswith(".acmi") or filename.endswith(".txt"):
        with open(filename, 'r', encoding='utf-8') as file:
            acmidata = file.readlines()
    else:
        print(f"Error: Unsupported file format: {filename}")
        return None

    return acmidata


def create_server_socket(host="localhost", port=42674):
    """Create and configure the server socket."""
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.bind((host, port))
    serversocket.listen(5)
    # Set timeout to make accept() interruptible
    serversocket.settimeout(1.0)
    print(f"Server listening on {host}:{port}")
    return serversocket


def perform_handshake(clientsocket):
    """Perform the Tacview handshake with the client."""
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
        if len(bytes_recv) < chunk:
            break

    # Check if the client handshake is valid
    print(f"Client handshake: {recieved}")
    if len(recieved) == 0:
        print("Bad Handshake")
        return False

    return True


def find_first_timestamp(acmidata):
    """Find the first timestamp in the ACMI data."""
    for line in acmidata:
        if line.startswith("#"):
            return float(line[1:])
    return 0


def stream_acmi_data(clientsocket, acmidata, timemultiplier, start_time=0):
    """Stream ACMI data to the connected client."""
    buffer = ""
    lastbuffer = ""
    lastbuffer_time = 0

    # Find the first timestamp in the file to use as baseline
    first_timestamp = find_first_timestamp(acmidata)
    target_start_time = first_timestamp + start_time
    seeking = start_time > 0
    first_frame_after_seek = True

    if seeking:
        print(f"File starts at {first_timestamp:.2f}s, seeking to {target_start_time:.2f}s (offset +{start_time:.2f}s)")

    for line in acmidata:
        buffer += line
        if line.startswith("#"):
            cur_time = float(line[1:])

            # Check if we've reached our target start time
            if seeking and cur_time >= target_start_time:
                seeking = False
                first_frame_after_seek = True
                print(f"Started streaming from time {cur_time:.2f}s")

            # Always send the data (needed for delta encoding)
            clientsocket.sendall(lastbuffer.encode('utf-8'))

            # Only sleep if we're not seeking and not the first frame after seek
            if lastbuffer_time > 0 and not first_frame_after_seek and not seeking:
                time.sleep((cur_time - lastbuffer_time) / timemultiplier)

            lastbuffer = buffer
            lastbuffer_time = cur_time
            buffer = ""
            first_frame_after_seek = False


def run_server(filename, timemultiplier=32, host="localhost", port=42674, start_time=0):
    """Main server loop that accepts connections and streams ACMI data."""
    acmidata = read_acmi_file(filename)
    if acmidata is None:
        return False

    serversocket = create_server_socket(host, port)

    try:
        while True:
            try:
                # accept connections from outside
                (clientsocket, address) = serversocket.accept()
                print(f"Client connected from {address}")

                if not perform_handshake(clientsocket):
                    clientsocket.close()
                    continue

                print("Streaming ACMI data...")
                stream_acmi_data(clientsocket, acmidata, timemultiplier, start_time)
                print("Stream complete")

                clientsocket.close()
            except socket.timeout:
                # Timeout allows Ctrl+C to be processed, continue waiting
                continue
            except (ConnectionResetError, ConnectionAbortedError):
                print("Connection reset by client")
            except KeyboardInterrupt:
                print("\nShutting down server...")
                break
    finally:
        serversocket.close()

    return True


def main():
    """Main entry point with command line argument parsing."""
    parser = argparse.ArgumentParser(description='Stream ACMI file data via Tacview Real Time Telemetry')
    parser.add_argument(
        'filename',
        nargs='?',  # Make filename optional
        default=DEFAULT_ACMI_FILE,
        help=f'Path to the ACMI file (.acmi, .txt, or .zip.acmi) (default: {DEFAULT_ACMI_FILE})')
    parser.add_argument('--timemultiplier',
                        '-t',
                        type=float,
                        default=32,
                        help='Time multiplier for playback speed (default: 32)')
    parser.add_argument('--start-time',
                        '-s',
                        type=float,
                        default=0,
                        help='Start time offset in seconds from the beginning of the file (default: 0)')
    parser.add_argument('--host', default='localhost', help='Host to bind to (default: localhost)')
    parser.add_argument('--port', '-p', type=int, default=42674, help='Port to bind to (default: 42674)')

    args = parser.parse_args()

    try:
        success = run_server(args.filename, args.timemultiplier, args.host, args.port, args.start_time)
        if not success:
            sys.exit(1)
    except FileNotFoundError:
        print(f"Error: File not found: {args.filename}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nServer interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
