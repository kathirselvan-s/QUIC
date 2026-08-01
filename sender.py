import os
import socket
import traceback

RECEIVER_IP = "192.168.1.36"   # Receiver machine IP
PORT = 5005
FOLDER_TO_SEND = "output"
CHUNK_SIZE = 4096
SOCKET_TIMEOUT = 3
MAX_RETRIES = 5


def wait_for_ack(sock, expected_ack, description):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            ack, _ = sock.recvfrom(1024)

            if ack == expected_ack:
                return True

            print(f"[WARNING] Unexpected ACK while waiting for {description}: {ack}")

        except socket.timeout:
            print(f"[WARNING] Timeout waiting for {description} (attempt {attempt}/{MAX_RETRIES})")

        except ConnectionResetError:
            print(f"[ERROR] Receiver {RECEIVER_IP}:{PORT} is not listening.")
            print("        Start receiver.py on the target machine.")
            print("        Also verify Windows Firewall allows UDP 5005.")
            return False

        except OSError as e:
            print(f"[ERROR] Socket error while waiting for {description}: {e}")
            return False

        except Exception as e:
            print(f"[ERROR] Unexpected error while waiting for {description}: {e}")
            traceback.print_exc()
            return False

    print(f"[ERROR] No ACK received for {description} after {MAX_RETRIES} attempts.")
    return False


def send_folder():
    if not os.path.isdir(FOLDER_TO_SEND):
        print(f"[ERROR] Source folder '{FOLDER_TO_SEND}' does not exist.")
        return

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(SOCKET_TIMEOUT)

        print("[INFO] Sender started.")
        print(f"[INFO] Sending to {RECEIVER_IP}:{PORT}")
        print(f"[INFO] Source folder: {os.path.abspath(FOLDER_TO_SEND)}")

    except OSError as e:
        print(f"[CRITICAL ERROR] Unable to create UDP socket: {e}")
        return

    files_sent = 0

    try:
        for root, _, files in os.walk(FOLDER_TO_SEND):

            for filename in files:
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, FOLDER_TO_SEND)
                rel_path = rel_path.replace("\\\\", "/")

                print(f"\\n[INFO] Preparing file: {rel_path}")

                # Send file header
                header = f"FILE:{rel_path}".encode("utf-8")

                success = False
                for _ in range(MAX_RETRIES):
                    sock.sendto(header, (RECEIVER_IP, PORT))
                    if wait_for_ack(sock, b"ACK", f"header ACK for {rel_path}"):
                        success = True
                        break

                if not success:
                    print(f"[ERROR] Receiver did not acknowledge header for {rel_path}.")
                    return

                # Send file data
                try:
                    with open(full_path, "rb") as f:
                        chunk_index = 0

                        while True:
                            chunk = f.read(CHUNK_SIZE)

                            if not chunk:
                                break

                            chunk_index += 1

                            success = False
                            for _ in range(MAX_RETRIES):
                                sock.sendto(chunk, (RECEIVER_IP, PORT))
                                if wait_for_ack(sock, b"ACK", f"chunk {chunk_index} of {rel_path}"):
                                    success = True
                                    break

                            if not success:
                                print(f"[ERROR] Receiver did not acknowledge chunk {chunk_index} of {rel_path}.")
                                return

                except FileNotFoundError:
                    print(f"[ERROR] File not found: {full_path}")
                    continue

                except PermissionError:
                    print(f"[ERROR] Permission denied reading file: {full_path}")
                    continue

                except OSError as e:
                    print(f"[ERROR] File read error for '{full_path}': {e}")
                    continue

                # Send EOF marker
                success = False
                for _ in range(MAX_RETRIES):
                    sock.sendto(b"EOF_FILE", (RECEIVER_IP, PORT))
                    if wait_for_ack(sock, b"ACK_EOF_FILE", f"EOF ACK for {rel_path}"):
                        success = True
                        break

                if not success:
                    print(f"[ERROR] Receiver did not acknowledge EOF for {rel_path}.")
                    return

                files_sent += 1
                print(f"[SUCCESS] Sent: {rel_path}")

        # Send EOT
        print("\\n[INFO] Finalizing transmission...")

        success = False
        for _ in range(MAX_RETRIES):
            sock.sendto(b"EOT", (RECEIVER_IP, PORT))
            if wait_for_ack(sock, b"ACK_EOT", "EOT ACK"):
                success = True
                break

        if success:
            print(f"[SUCCESS] Transfer completed successfully. Files sent: {files_sent}")
        else:
            print("[ERROR] Receiver did not acknowledge final EOT signal.")

    except KeyboardInterrupt:
        print("\\n[WARNING] Sender interrupted by user.")

    except Exception as e:
        print(f"[CRITICAL ERROR] Unexpected sender failure: {e}")
        traceback.print_exc()

    finally:
        try:
            sock.close()
        except Exception:
            pass

        print("[INFO] Sender socket closed.")


if __name__ == "__main__":
    send_folder()