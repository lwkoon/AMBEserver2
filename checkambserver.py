#!/usr/bin/env python3
import socket
import struct
import subprocess
import time

# AMBEserver protocol constant: expected start byte
DV3K_START_BYTE = 0x61

def build_test_packet():
    """
    Construct a minimal valid AMBE packet.
    According to the C code:
      - Byte 0: start byte (0x61)
      - Bytes 1-2: payload length (big-endian)
      - Byte 3: packet type
      - Followed by payload (here, a single byte)
    We'll set payload_length = 1 and use 0x00 as the packet type.
    The payload is set to 0x33 (an example value).
    """
    payload_length = 1
    packet_type = 0x00  # Adjust if needed
    # Pack header: 2-byte payload length and 1-byte packet type
    header = struct.pack("!HB", payload_length, packet_type)
    # Minimal payload: 1 byte (0x33 as an example)
    payload = struct.pack("!B", 0x33)
    # Construct the full packet
    packet = struct.pack("!B", DV3K_START_BYTE) + header + payload
    return packet

def is_valid_response(packet):
    """
    Validate the response packet:
      - Must be at least 4 bytes.
      - Must start with DV3K_START_BYTE.
      - The total packet length must equal 1 (start byte) + 3 (header) + payload_length.
    """
    if len(packet) < 4:
        print("Response packet too short: %d bytes" % len(packet))
        return False
    if packet[0] != DV3K_START_BYTE:
        print("Invalid start byte in response: expected 0x%02X, got 0x%02X" %
              (DV3K_START_BYTE, packet[0]))
        return False
    payload_length = struct.unpack("!H", packet[1:3])[0]
    expected_length = 1 + 3 + payload_length
    if len(packet) != expected_length:
        print("Response packet length mismatch: expected %d, got %d" %
              (expected_length, len(packet)))
        return False
    return True

def send_test_packet_and_wait():
    """
    Sends a test UDP packet to the ambeserver and waits for a UDP response.
    Returns True if a valid response is received; otherwise, False.
    """
    server_address = ('127.0.0.1', 2460)
    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Bind to any available port so that we can receive the response
    sock.bind(('0.0.0.0', 0))
    sock.settimeout(10)  # Wait up to 10 seconds for a response

    test_packet = build_test_packet()
    try:
        # Send the test packet
        sock.sendto(test_packet, server_address)
        print("Test packet sent to %s:%d" % server_address)
        # Wait for a response
        data, addr = sock.recvfrom(4096)
        print("Received response from %s" % (addr,))
        if is_valid_response(data):
            print("Valid response received. Ambeserver is running correctly.")
            return True
        else:
            print("Invalid response received.")
            return False
    except socket.timeout:
        print("No response received within timeout.")
        return False
    except Exception as e:
        print("Error during test:", e)
        return False
    finally:
        sock.close()

def restart_ambeserver():
    """
    Restart ambeserver by killing the current process and starting a new one.
    """
    try:
        print("Ambeserver did not respond correctly. Restarting ambeserver...")
        subprocess.run(["pkill", "-f", "/opt/AMBEServer/AMBEserver"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(1)
        subprocess.Popen(["/opt/AMBEServer/AMBEserver", "-s", "230400", "-d"])
        print("Ambeserver restarted.")
    except Exception as e:
        print("Error restarting ambeserver:", e)

def log_to_journal(message):
    """
    Log a message to the system journal using the logger command.
    """
    subprocess.run(["logger", message])

def main():
    if send_test_packet_and_wait():
        # Log a message to journalctl if the service is running correctly
        log_to_journal("Ambeserver is running correctly")
    else:
        restart_ambeserver()

if __name__ == '__main__':
    main()
