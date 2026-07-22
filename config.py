import os
import socket

# Server configuration - CHANGE THESE FOR CROSS-PLATFORM
SERVER_HOST = "0.0.0.0"  # Listen on all interfaces
SERVER_PORT = 4433

# File paths
CERT_PATH = "certs/cert.pem"
KEY_PATH = "certs/key.pem"
RECEIVED_DIR = "received"
SEND_DIR = "send"

# QUIC configuration
MAX_DATAGRAM_SIZE = 65536
IDLE_TIMEOUT = 60.0
CHUNK_SIZE = 8192  # 8KB chunks

# Create necessary directories
os.makedirs(RECEIVED_DIR, exist_ok=True)
os.makedirs(SEND_DIR, exist_ok=True)
os.makedirs("certs", exist_ok=True)

def get_local_ip():
    """Get the local IP address of the machine"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# Auto-detect local IP
LOCAL_IP = get_local_ip()