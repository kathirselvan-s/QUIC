
import os
import socket
import traceback

RECEIVER_IP = "192.168.1.50"  # Replace with target OS IP address
PORT = 5005
FOLDER_TO_SEND = "output"
CHUNK_SIZE = 4096

def send_folder():
    if not os.path.exists(FOLDER_TO_SEND):
        print(f"[ERROR] Source folder '{FOLDER_TO_SEND}' does not exist locally.")
        return

    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2.0)  # 2-second timeout for visibility
        print(f"[INFO] Socket initialized. Target: {RECEIVER_IP}:{PORT}")
    except Exception as e:
        print(f"[ERROR] Failed to create socket: {e}")
        traceback.print_exc()
        return

    try:
        print(f"[INFO] Starting scan of folder '{FOLDER_TO_SEND}'...")
        for root, dirs, files in os.walk(FOLDER_TO_SEND):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, FOLDER_TO_SEND)
                rel_path_normalized = rel_path.replace("\\", "/")

                # 1. Send File Header Indicator
                header = f"FILE:{rel_path_normalized}".encode('utf-8')
                header_success = False
                while not header_success:
                    try:
                        sock.sendto(header, (RECEIVER_IP, PORT))
                        ack, _ = sock.recvfrom(1024)
                        if ack == b"ACK":
                            header_success = True
                        elif ack == b"ERR":
                            print(f"[ERROR] Receiver reported error handling file header: {rel_path_normalized}")
                            return
                    except socket.timeout:
                        print(f"[WARNING] Timeout waiting for header ACK on '{rel_path_normalized}', retrying...")
                    except Exception as e:
                        print(f"[ERROR] Network error sending header for '{rel_path_normalized}': {e}")
                        traceback.print_exc()
                        return

                # 2. Send File Contents in Chunks
                try:
                    with open(full_path, "rb") as f:
                        print(f"[INFO] Streaming: {rel_path_normalized}")
                        while True:
                            chunk = f.read(CHUNK_SIZE)
                            if not chunk:
                                break
                            
                            chunk_sent = False
                            while not chunk_sent:
                                try:
                                    sock.sendto(chunk, (RECEIVER_IP, PORT))
                                    ack, _ = sock.recvfrom(1024)
                                    if ack == b"ACK":
                                        chunk_sent = True
                                except socket.timeout:
                                    print(f"[WARNING] Timeout on chunk for '{rel_path_normalized}', resending...")
                                except Exception as e:
                                    print(f"[ERROR] Network error during chunk transmission: {e}")
                                    traceback.print_exc()
                                    return
                except Exception as e:
                    print(f"[ERROR] Failed reading local file '{full_path}': {e}")
                    traceback.print_exc()
                    return

                # 3. Send End Of File Signal
                eof_file_success = False
                while not eof_file_success:
                    try:
                        sock.sendto(b"EOF_FILE", (RECEIVER_IP, PORT))
                        ack, _ = sock.recvfrom(1024)
                        if ack == b"ACK_EOF_FILE":
                            eof_file_success = True
                    except socket.timeout:
                        sock.sendto(b"EOF_FILE", (RECEIVER_IP, PORT))
                    except Exception as e:
                        print(f"[ERROR] Network exception sending EOF_FILE: {e}")
                        return

        # 4. Send End Of Transmission Signal for the whole folder
        print("[INFO] All files sent. Finalizing transmission signal...")
        eot_success = False
        while not eot_success:
            try:
                sock.sendto(b"EOT", (RECEIVER_IP, PORT))
                ack, _ = sock.recvfrom(1024)
                if ack == b"ACK_EOT":
                    print("[SUCCESS] Folder and all nested files transferred and confirmed successfully!")
                    eot_success = True
            except socket.timeout:
                sock.sendto(b"EOT", (RECEIVER_IP, PORT))
            except Exception as e:
                print(f"[ERROR] Network exception finalizing transfer (EOT): {e}")
                break

    except KeyboardInterrupt:
        print("\n[WARNING] Sender manually interrupted by user (Ctrl+C).")
    except Exception as e:
        print(f"[CRITICAL ERROR] An unexpected exception occurred in sender loop: {e}")
        traceback.print_exc()
    finally:
        if sock:
            try:
                sock.close()
            except:
                pass
        print("[INFO] Sender socket closed.")

if __name__ == "__main__":
    send_folder()