# QUIC File Transfer

A secure, high-performance file transfer application using the QUIC protocol. Works across Windows, Linux, and macOS.

## ✨ Features

- ✅ **Cross-platform** — Windows, Linux, macOS
- 🔒 **Secure** — Built-in TLS 1.3 encryption via self-signed certificates
- 🚀 **Fast** — QUIC protocol over UDP
- 📊 **Progress bars** — Real-time transfer progress
- 🔍 **Connectivity check** — Verifies server is reachable before every transfer
- 📁 **Multiple files** — Watch a folder and auto-send all files
- 🛡️ **Error handling** — Robust error recovery
- 🖥️ **Auto IP detection** — Automatically detects your local network IP
- 🔄 **Retry mechanism** — Automatic connection retries (3 attempts)

---

## 📋 Requirements

- Python 3.10+
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

### 3. Generate SSL certificates (run on the SERVER machine)

```powershell
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe generate_certs.py
```

> Certificates are saved to `certs/cert.pem` and `certs/key.pem`.  
> They are valid for **365 days** and include all local LAN IPs + `localhost` + `127.0.0.1`.

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
║   - All interfaces: 0.0.0.0:4433                        ║
║   - Local IP: 192.168.1.37:4433                         ║
╚════════════════════════════════════════════════════════════╝

📁 Files will be saved in: ./received/
🔄 Press Ctrl+C to stop the server
```

Note the **Local IP** shown — you will need it on the client machine.

### Stop the server:

```
Ctrl + C
```

---

## 🔍 Step 1 — Check Two-Device Connectivity (Do This First!)

Before sending any file, always verify that both devices can reach each other over QUIC.  
Run this command **on the client machine**, replacing the IP with the server's Local IP:

```powershell
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py --ping --server 192.168.1.37
```

### ✅ Success output (server is up and reachable):

```
╔════════════════════════════════════════════════════════════╗
║          QUIC FILE TRANSFER - AUTO SENDER                ║
╠════════════════════════════════════════════════════════════╣
║ Local IP: 192.168.1.50                                   ║
║ Server:  192.168.1.37:4433                               ║
╚════════════════════════════════════════════════════════════╝

🔍 Checking connection to 192.168.1.37:4433 ...
✅ Server is reachable at 192.168.1.37:4433
```

### ❌ Failure output (server is down or unreachable):

```
🔍 Checking connection to 192.168.1.37:4433 ...
❌ Connection refused — is the server running on 192.168.1.37:4433?
```

or

```
🔍 Checking connection to 192.168.1.37:4433 ...
❌ Connection timed out — server unreachable at 192.168.1.37:4433
```

### What to do if the ping fails:

| Symptom | Fix |
|---|---|
| "Connection refused" | Start the server on the other machine first |
| "Connection timed out" | Check both machines are on the same Wi-Fi/LAN; check Windows Firewall allows UDP port 4433 |
| Still failing | Run `netstat -ano \| findstr ":4433"` on the server to confirm it's listening |

---

## 📤 Step 2 — Send a File

Once the ping succeeds, send a file. The client automatically re-checks connectivity before every transfer.

### Send a single file (most common use case):

```powershell
# Positional argument (simplest form)
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py myfile.txt --server 192.168.1.37

# Absolute path
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py C:\Users\You\Documents\report.pdf --server 192.168.1.37

# Using --file flag
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py --file send\photo.jpg --server 192.168.1.37
```

> Replace `192.168.1.37` with the **Local IP** shown in the server's startup banner.

### Expected output on successful transfer:

```
🔍 Checking connection to 192.168.1.37:4433 ...
✅ Server is reachable at 192.168.1.37:4433

📤 Connecting to 192.168.1.37:4433 (attempt 1/3)...
📤 Sending Sign.jpg (142.58 KB)
📤 Sign.jpg: [████████████████████████████████████████] 100.00% 146000/146000 bytes
✅ Sent: Sign.jpg (142.58 KB)
```

### Send to the same machine (loopback test):

```powershell
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py myfile.txt --server 127.0.0.1
```

---

## 📁 Other Client Commands

### Watch a folder and auto-send all new files:

```powershell
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py --watch ./send --server 192.168.1.37
```

### Send all files in a folder once:

```powershell
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py --send-all ./send --server 192.168.1.37
```

### List files available to send (in `send/` folder):

```powershell
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py --list ./send
```

### List files already received on the server:

```powershell
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py --remote-list --server 192.168.1.37
```

### Show your local network interfaces and IPs:

```powershell
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py --show-ips
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

**Cause:** Windows terminal defaults to `cp1252` encoding.

**Fix:** Always run with `PYTHONUTF8=1`:

```powershell
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe server.py
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py myfile.txt --server 127.0.0.1
```

> To set permanently for the session:
> ```powershell
> $env:PYTHONUTF8 = '1'
> ```

---

### 3. Ping fails — "Connection timed out"

```
❌ Connection timed out — server unreachable at 192.168.1.37:4433
```

**Cause:** Network or firewall blocking UDP port 4433.

**Fix on Windows (allow QUIC through firewall):**

```powershell
# Run as Administrator
New-NetFirewallRule -DisplayName "QUIC File Transfer" -Direction Inbound `
  -Protocol UDP -LocalPort 4433 -Action Allow
```

Also verify both machines are on the same network:
```powershell
# On client — ping the server's IP (basic network test)
ping 192.168.1.37
```

---

### 4. `FileNotFoundError` — Certificates not found

```
❌ ERROR: Certificates not found!
📋 Please generate certificates using: python generate_certs.py
```

**Fix:**

```powershell
$env:PYTHONUTF8='1'; .venv\Scripts\python.exe generate_certs.py
```

---

### 5. `ConnectionRefusedError` — Server not running

```
❌ Connection refused. Is the server running on 192.168.1.37:4433?
```

**Fix:**
1. Start the server first: `.\start_server.ps1`
2. Confirm it's listening: `netstat -ano | findstr ":4433 "`
3. Then run the ping test, then the client

---

### 6. `❌ Server error: File already exists.`

**Cause:** A file with the same name already exists in `received/` on the server.

**Fix:**
```powershell
Remove-Item "received\myfile.txt"
```

---

## 📁 Project Structure

```
QUIC/
├── server.py            # QUIC server — receives files
├── client.py            # QUIC client — sends files (with connectivity check)
├── config.py            # Server/client configuration (host, port, paths)
├── protocol.py          # Message framing and protocol definitions
├── utils.py             # Helper utilities (formatting, file ops)
├── generate_certs.py    # Generates self-signed TLS certificates
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
| **Check connectivity** | `$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py --ping --server <LAN-IP>` |
| Send single file | `$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py <file> --server <LAN-IP>` |
| Watch folder & auto-send | `$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py --watch ./send --server <LAN-IP>` |
| List local files | `$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py --list ./send` |
| List server files | `$env:PYTHONUTF8='1'; .venv\Scripts\python.exe client.py --remote-list --server <LAN-IP>` |
| Regenerate certs | `$env:PYTHONUTF8='1'; .venv\Scripts\python.exe generate_certs.py` |
| Kill port 4433 | `netstat -ano \| findstr ":4433 "` then `taskkill /F /PID <PID>` |

---

## 🔄 Two-Device Transfer — Full Workflow

```
MACHINE A (Server — IP: 192.168.1.37)          MACHINE B (Client — IP: 192.168.1.50)
─────────────────────────────────────────────   ─────────────────────────────────────────────
1. Run: .\start_server.ps1
   → Note the "Local IP" shown (192.168.1.37)

                                                2. Run ping test:
                                                   python client.py --ping --server 192.168.1.37
                                                   → "✅ Server is reachable"

                                                3. Send file:
                                                   python client.py photo.jpg --server 192.168.1.37
                                                   → Connectivity re-checked automatically
                                                   → "✅ Sent: photo.jpg"

4. Check received/:
   ls received/
   → photo.jpg ✓
```