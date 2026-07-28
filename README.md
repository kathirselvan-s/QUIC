# QUIC File Transfer

A secure, high-performance file transfer application using the QUIC protocol. Works across Windows, Linux, and macOS.

## ✨ Features

- ✅ **Cross-platform** — Windows, Linux, macOS
- 🔒 **Secure** — Built-in TLS 1.3 encryption via self-signed certificates
- 🚀 **Fast** — QUIC protocol over UDP
- 📊 **Progress bars** — Real-time transfer progress
- 📁 **Multiple files** — Handle simultaneous transfers
- 🛡️ **Error handling** — Robust error recovery
- 🖥️ **Auto IP detection** — Automatically detects your local network IP
- 🔄 **Retry mechanism** — Automatic connection retries (3 attempts)

---

## 📋 Requirements

- Python 3.7+
- pip (Python package manager)
- A virtual environment (`.venv`) — see setup below

---

## ⚙️ Initial Setup (Run Once)

### 1. Create and activate the virtual environment

```powershell
# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate (Windows CMD)
.venv\Scripts\activate.bat
```

### 2. Install dependencies

```powershell
# From offline packages (no internet needed)
python -m pip install --no-index --find-links=offline_packages -r requirements.txt

# OR from the internet
pip install -r requirements.txt
```

### 3. Generate SSL certificates

```powershell
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe generate_certs.py
```

> Certificates are saved to `certs/cert.pem` and `certs/key.pem`.  
> They are valid for **365 days** and include your local LAN IP + `localhost` + `127.0.0.1`.

### 4. Place files to send

Copy any files you want to transfer into the `send/` directory:

```
send/
  myfile.txt
  photo.jpg
  document.pdf
```

---

## 🚀 Running the Server

### Recommended — use the helper script (handles port conflicts automatically):

```powershell
.\start_server.ps1
```

### Manual start:

```powershell
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe server.py
```

> The server listens on **port 4433 (UDP)** on all interfaces (`0.0.0.0`).  
> Received files are saved to the `received/` directory.

**Expected output:**

```
╔════════════════════════════════════════════════════════════╗
║              QUIC FILE TRANSFER SERVER                   ║
╠════════════════════════════════════════════════════════════╣
║ Server running on:                                      ║
║   - All interfaces: 0.0.0.0:4433              ║
║   - Local IP: 192.168.1.51:4433                    ║
║                                                         ║
║ Important: Use the LOCAL IP on other machines!         ║
║                                                         ║
║ To connect from another machine, use:                  ║
║   python client.py <filename> --server 192.168.1.51        ║
╚════════════════════════════════════════════════════════════╝

📁 Files will be saved in: ./received/
🔄 Press Ctrl+C to stop the server
```

### Stop the server:

```
Ctrl + C
```

---

## 📤 Running the Client

### Send a file to the server (same machine):

```powershell
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py <filename> --server 127.0.0.1
```

**Example:**

```powershell
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py myfile.txt --server 127.0.0.1
```

### Send a file to a remote server (different machine on LAN):

```powershell
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py <filename> --server 192.168.1.51
```

> Replace `192.168.1.51` with the **Local IP** shown in the server's startup banner.

### Use a custom port:

```powershell
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py <filename> --server 192.168.1.51 --port 4433
```

### List files available to send (in `send/` folder):

```powershell
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py --list
```

### List files already received on the server:

```powershell
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py --remote-list --server 127.0.0.1
```

**Expected output on successful transfer:**

```
📤 Connecting to 127.0.0.1:4433 (attempt 1/3)...
✅ Connected to server at 127.0.0.1:4433

📁 Sending: myfile.txt (1.01 KB)
📊 Progress:
[████████████████████████████████████████] 100.00% 1032/1032 bytes

✅ File sent successfully! (1.01 KB)
```

### Stop the client:

The client exits automatically after the transfer completes or all retry attempts fail.  
To force-stop mid-transfer:

```
Ctrl + C
```

---

## ❗ Common Errors & How to Fix Them

### 1. `WinError 10048` — Port already in use

```
OSError: [WinError 10048] Only one usage of each socket address is normally permitted
```

**Cause:** A previous server process is still holding port 4433.

**Fix:**

```powershell
# Find the PID using port 4433
netstat -ano | findstr ":4433 "

# Kill it (replace 12345 with the actual PID)
taskkill /F /PID 12345

# Wait 2 seconds, then restart
Start-Sleep -Seconds 2
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe server.py
```

Or simply use the helper script which does this automatically:

```powershell
.\start_server.ps1
```

---

### 2. `UnicodeEncodeError` — Emoji/box-drawing characters crash

```
UnicodeEncodeError: 'charmap' codec can't encode characters in position 0-61
```

**Cause:** Windows terminal defaults to `cp1252` encoding and can't render emoji or box-drawing characters.

**Fix:** Always run with `PYTHONUTF8=1`:

```powershell
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe server.py
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py <filename> --server 127.0.0.1
```

> To set this permanently for the session:
> ```powershell
> $env:PYTHONUTF8 = '1'
> ```

---

### 3. TLS certificate mismatch — hostname doesn't match

```
Error: 298, reason: hostname '127.0.0.1' doesn't match ...
```

**Cause:** The SSL certificate was generated without including `127.0.0.1` in its Subject Alternative Names (SAN).

**Fix:** Regenerate the certificates:

```powershell
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe generate_certs.py
```

Then restart the server.

---

### 4. `FileNotFoundError` — Certificates not found

```
❌ ERROR: Certificates not found!
📋 Please generate certificates using: python generate_certs.py
```

**Cause:** The `certs/cert.pem` or `certs/key.pem` files are missing.

**Fix:**

```powershell
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe generate_certs.py
```

---

### 5. `ConnectionRefusedError` — Server not running

```
❌ Connection refused. Is the server running on 127.0.0.1:4433?
```

**Cause:** The client is trying to connect before the server is started, or the server crashed.

**Fix:**
1. Start the server first in a separate terminal window
2. Confirm the server is running: `netstat -ano | findstr ":4433 "`
3. Then run the client

---

### 6. `❌ Server error: File already exists.`

```
❌ Server error: File already exists.
```

**Cause:** A file with the same name already exists in the `received/` folder on the server.

**Fix:** Delete the existing file from `received/` or rename your file before sending:

```powershell
Remove-Item "received\myfile.txt"
```

---

### 7. `ImportError` — Typo or wrong module name

```
ImportError: cannot import name 'XxxConfiguration' from 'aioquic.quic.configuration'
```

**Cause:** A typo in an import statement in `server.py` or `client.py`.

**Fix:** Open `server.py` and verify line 15 reads exactly:

```python
from aioquic.quic.configuration import QuicConfiguration
```

---

## 📁 Project Structure

```
QUIC/
├── server.py            # QUIC server — receives files
├── client.py            # QUIC client — sends files
├── config.py            # Server/client configuration (host, port, paths)
├── protocol.py          # Message framing and protocol definitions
├── utils.py             # Helper utilities (formatting, file ops)
├── generate_certs.py    # Generates self-signed TLS certificates
├── setup_network.py     # Network setup utilities
├── start_server.ps1     # PowerShell helper to start server safely
├── requirements.txt     # Python dependencies
├── certs/
│   ├── cert.pem         # TLS certificate (auto-generated)
│   └── key.pem          # TLS private key (auto-generated)
├── send/                # Place files here to send via client
└── received/            # Server saves received files here
```

---

## 🔧 Configuration

Edit `config.py` to change defaults:

| Setting | Default | Description |
|---|---|---|
| `SERVER_HOST` | `0.0.0.0` | Server listens on all network interfaces |
| `SERVER_PORT` | `4433` | UDP port for QUIC connections |
| `CHUNK_SIZE` | `65536` (64 KB) | Size of each file chunk sent |
| `IDLE_TIMEOUT` | `60.0` seconds | Connection idle timeout |
| `MAX_RETRIES` | `3` | Client reconnection attempts |
| `SEND_DIR` | `./send` | Directory client reads files from |
| `RECEIVED_DIR` | `./received` | Directory server saves files to |

---

## 🔁 Quick Reference

| Action | Command |
|---|---|
| Start server (safe) | `.\start_server.ps1` |
| Start server (manual) | `$env:PYTHONUTF8='1'; .venv\Scripts\python.exe server.py` |
| Stop server | `Ctrl+C` |
| Send file (local) | `$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py <file> --server 127.0.0.1` |
| Send file (remote) | `$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py <file> --server <LAN-IP>` |
| List local files | `$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py --list` |
| List server files | `$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py --remote-list --server 127.0.0.1` |
| Regenerate certs | `$env:PYTHONUTF8='1'; .venv\Scripts\python.exe generate_certs.py` |
| Kill port 4433 | `taskkill /F /PID $($(netstat -ano \| findstr ":4433 ") -split "\s+" \| Select -Last 1)` |