import os
import socket
from pathlib import Path

# ============================================================
# Network Configuration
# ============================================================

# Server listens on all interfaces
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 4433

# ============================================================
# Certificate Paths
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

CERT_DIR = BASE_DIR / "certs"
CERT_PATH = str(CERT_DIR / "cert.pem")
KEY_PATH = str(CERT_DIR / "key.pem")

# ============================================================
# File Transfer Directories
# ============================================================

SEND_DIR = str(BASE_DIR / "send")
RECEIVED_DIR = str(BASE_DIR / "received")

# Create required directories automatically
os.makedirs(CERT_DIR, exist_ok=True)
os.makedirs(SEND_DIR, exist_ok=True)
os.makedirs(RECEIVED_DIR, exist_ok=True)

# ============================================================
# QUIC Settings
# ============================================================

ALPN_PROTOCOL = "file-transfer"

CHUNK_SIZE = 64 * 1024          # 64 KB

MAX_DATAGRAM_SIZE = 65536

IDLE_TIMEOUT = 60.0

# ============================================================
# Retry Settings
# ============================================================

MAX_RETRIES = 3

RETRY_DELAY = 1

# ============================================================
# Progress Update
# ============================================================

PROGRESS_UPDATE_INTERVAL = 0.25

# ============================================================
# Buffer Sizes
# ============================================================

READ_BUFFER = 1024 * 1024

WRITE_BUFFER = 1024 * 1024

# ============================================================
# Utility Functions
# ============================================================

def get_local_ip():
    """
    Returns the LAN IP of this machine.
    """

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Doesn't actually contact Google.
        sock.connect(("8.8.8.8", 80))

        ip = sock.getsockname()[0]

        sock.close()

        return ip

    except Exception:
        return "127.0.0.1"


LOCAL_IP = get_local_ip()