

import os
import socket
import traceback

LISTEN_IP = "0.0.0.0"
PORT = 5005
OUTPUT_DIR = "output"

def run_server():
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((LISTEN_IP, PORT))
        print(f"[INFO] Server successfully bound and listening on port {PORT}")
        print(f"[INFO] Target output directory resolved to: absolute path -> '{os.path.abspath(OUTPUT_DIR)}'")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    except Exception as e:
        print(f"[CRITICAL ERROR] Server failed during socket initialization or directory setup: {e}")
        traceback.print_exc()
        return

    current_file_handle = None
    files_received_count = 0

    try:
        while True:
            try:
                data, addr = sock.recvfrom(65535)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[WARNING] Low-level socket read exception occurred: {e}")
                continue

            # Check for end of transmission signal
            if data == b"EOT":
                print(f"[SUCCESS] Transmission complete signal (EOT) received from client {addr}.")
                try:
                    sock.sendto(b"ACK_EOT", addr)
                except Exception as e:
                    print(f"[ERROR] Failed dispatching ACK_EOT response: {e}")
                break

            # Handle incoming file header indicator
            if data.startswith(b"FILE:"):
                if current_file_handle:
                    current_file_handle.close()
                
                try:
                    rel_path = data[5:].decode('utf-8')
                    target_path = os.path.join(OUTPUT_DIR, rel_path)
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    
                    current_file_handle = open(target_path, "wb")
                    files_received_count += 1
                    print(f"[INFO] Processing file #{files_received_count}: '{rel_path}'")
                    sock.sendto(b"ACK", addr)
                except Exception as e:
                    print(f"[ERROR] Failed creating file pointer on disk: {e}")
                    traceback.print_exc()
                    sock.sendto(b"ERR", addr)
                continue

            # Handle individual file EOF boundary
            if data == b"EOF_FILE":
                if current_file_handle:
                    current_file_handle.close()
                    current_file_handle = None
                try:
                    sock.sendto(b"ACK_EOF_FILE", addr)
                except Exception as e:
                    print(f"[ERROR] Failed sending ACK_EOF_FILE response: {e}")
                continue

            # Handle file data chunks
            if current_file_handle:
                try:
                    current_file_handle.write(data)
                    sock.sendto(b"ACK", addr)
                except Exception as e:
                    print(f"[ERROR] Disk write failure while saving packet chunk: {e}")
                    traceback.print_exc()

    except KeyboardInterrupt:
        print("\n[WARNING] Server manually stopped by operator (Ctrl+C).")
    except Exception as e:
        print(f"[CRITICAL ERROR] Unhandled exception in main server listener loop: {e}")
        traceback.print_exc()
    finally:
        if current_file_handle:
            try:
                current_file_handle.close()
            except:
                pass
        if sock:
            try:
                sock.close()
            except:
                pass
        print(f"[INFO] Server listener shutdown complete. Total files successfully processed: {files_received_count}")

if __name__ == "__main__":
    run_server()