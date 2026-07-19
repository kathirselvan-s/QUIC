import os

# Server configuration
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 4433

# File paths
CERT_PATH = "certs/cert.pem"
KEY_PATH = "certs/key.pem"
RECEIVED_DIR = "received"
SEND_DIR = "send"

# QUIC configuration
MAX_DATAGRAM_SIZE = 65536
IDLE_TIMEOUT = 60.0

# Create necessary directories
os.makedirs(RECEIVED_DIR, exist_ok=True)
os.makedirs(SEND_DIR, exist_ok=True)
os.makedirs("certs", exist_ok=True)