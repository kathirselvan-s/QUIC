import os
import socket
import traceback

LISTEN_IP = "0.0.0.0"
PORT = 5005
OUTPUT_DIR = "received_output"
SOCKET_TIMEOUT = 3


def run_server():
    sock = None
    current_file_handle = None
    files_received = 0

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((LISTEN_IP, PORT))
        sock.settimeout(SOCKET_TIMEOUT)

        os.makedirs(OUTPUT_DIR, exist_ok=True)

        print(f"[INFO] Receiver listening on {LISTEN_IP}:{PORT}")
        print(f"[INFO] Saving files to: {os.path.abspath(OUTPUT_DIR)}")
        print("[INFO] Waiting for incoming files...\\n")

    except OSError as e:
        print(f"[CRITICAL ERROR] Failed to start receiver: {e}")
        print("        Check if port 5005 is already in use.")
        return

    try:
        while True:
            try:
                data, addr = sock.recvfrom(65535)

            except socket.timeout:
                continue

            except OSError as e:
                print(f"[WARNING] Socket receive error: {e}")
                continue

            except Exception as e:
                print(f"[WARNING] Unexpected receive error: {e}")
                traceback.print_exc()
                continue

            # End of transmission
            if data == b"EOT":
                print(f"\\n[SUCCESS] Transfer completed from {addr}")
                sock.sendto(b"ACK_EOT", addr)
                break

            # File header
            if data.startswith(b"FILE:"):
                try:
                    if current_file_handle:
                        current_file_handle.close()

                    rel_path = data[5:].decode("utf-8")
                    target_path = os.path.join(OUTPUT_DIR, rel_path)

                    os.makedirs(os.path.dirname(target_path), exist_ok=True)

                    current_file_handle = open(target_path, "wb")

                    files_received += 1

                    print(f"[INFO] Receiving file #{files_received}: {rel_path}")

                    sock.sendto(b"ACK", addr)

                except UnicodeDecodeError:
                    print("[ERROR] Invalid UTF-8 filename received.")
                    sock.sendto(b"ERR", addr)

                except PermissionError:
                    print(f"[ERROR] Permission denied creating file: {target_path}")
                    sock.sendto(b"ERR", addr)

                except OSError as e:
                    print(f"[ERROR] Failed to create output file: {e}")
                    traceback.print_exc()
                    sock.sendto(b"ERR", addr)

                continue

            # End of file
            if data == b"EOF_FILE":
                try:
                    if current_file_handle:
                        current_file_handle.close()
                        current_file_handle = None

                    sock.sendto(b"ACK_EOF_FILE", addr)
                    print("[INFO] File completed.")

                except Exception as e:
                    print(f"[ERROR] Failed to finalize current file: {e}")

                continue

            # File data
            if current_file_handle:
                try:
                    current_file_handle.write(data)
                    sock.sendto(b"ACK", addr)

                except OSError as e:
                    print(f"[ERROR] Disk write failure: {e}")
                    traceback.print_exc()

                    try:
                        current_file_handle.close()
                    except Exception:
                        pass

                    current_file_handle = None

    except KeyboardInterrupt:
        print("\\n[WARNING] Receiver stopped by user.")

    except Exception as e:
        print(f"[CRITICAL ERROR] Receiver crashed: {e}")
        traceback.print_exc()

    finally:
        if current_file_handle:
            try:
                current_file_handle.close()
            except Exception:
                pass

        if sock:
            try:
                sock.close()
            except Exception:
                pass

        print(f"\\n[INFO] Receiver shutdown complete. Files received: {files_received}")


if __name__ == "__main__":
    run_server()