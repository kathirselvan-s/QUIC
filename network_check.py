#network_check.py , UDP



import platform
import subprocess
import socket
import sys
import traceback

def get_local_ip():
    """Dynamically fetches the local machine's active IP address."""
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        return local_ip
    except Exception as e:
        print(f"[WARNING] Could not determine via external socket lookup: {e}")
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            return local_ip
        except Exception as ex:
            print(f"[ERROR] Failed all IP lookup mechanisms: {ex}")
            traceback.print_exc()
            return "127.0.0.1"
    finally:
        if s:
            s.close()

def ping_target(target_ip):
    """Cross-platform ping check function for Windows and Linux."""
    param = "-n" if platform.system().lower() == "windows" else "-c"
    command = ["ping", param, "1", target_ip]
    
    print(f"[INFO] Pinging target host: {target_ip}...")
    try:
        output = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if output.returncode == 0:
            print(f"[SUCCESS] Target {target_ip} is reachable via ping!")
            return True
        else:
            print(f"[ERROR] Target {target_ip} did not respond to ping. Return code: {output.returncode}")
            return False
    except Exception as e:
        print(f"[CRITICAL ERROR] Failed to execute system ping utility: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    my_ip = get_local_ip()
    print(f"[INFO] Current Machine Local IP Address: {my_ip}")
    
    if len(sys.argv) > 1:
        target = sys.argv[1]
        ping_target(target)
    else:
        print("[INFO] Tip: Pass target IP as an argument to test connectivity (e.g., python network_check.py 192.168.1.50)")