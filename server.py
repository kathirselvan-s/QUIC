import asyncio
import os
import signal
import struct
import sys

# Fix Unicode output on Windows terminals (cp1252 → UTF-8)
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from aioquic.asyncio import serve
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived, ConnectionTerminated

from config import SERVER_HOST, SERVER_PORT, CERT_PATH, KEY_PATH, RECEIVED_DIR, LOCAL_IP, ALPN_PROTOCOL
from protocol import Protocol, MessageType, HEADER_FORMAT
from utils import ensure_directory, safe_filename, format_size

ensure_directory(RECEIVED_DIR)


class FileTransferServerProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_transfers = {}

    def quic_event_received(self, event):
        if isinstance(event, ConnectionTerminated):
            for reader in self._stream_readers.values():
                reader.feed_eof()
            if hasattr(self, "close"):
                self.close()
        elif isinstance(event, StreamDataReceived):
            reader = self._stream_readers.get(event.stream_id, None)
            if reader is None:
                reader, writer = self._create_stream(event.stream_id)
                asyncio.ensure_future(self.handle_stream(event.stream_id, reader, writer))
            reader.feed_data(event.data)
            if event.end_stream:
                reader.feed_eof()

    async def handle_stream(self, stream_id, reader, writer):
        buffer = bytearray()
        while True:
            try:
                chunk = await asyncio.wait_for(reader.read(65535), timeout=1.0)
            except asyncio.TimeoutError:
                break
            if not chunk:
                break
            print(f"[DEBUG] stream {stream_id} read {len(chunk)} bytes")
            if chunk:
                print(f"[DEBUG] sample: {chunk[:16].hex()}")
            buffer.extend(chunk)

            while True:
                if len(buffer) < 6:
                    break
                version, msg_type, payload_size = struct.unpack(
                    HEADER_FORMAT,
                    bytes(buffer[:6]),
                )
                total_length = 6 + payload_size
                if len(buffer) < total_length:
                    break
                message_data = bytes(buffer[:total_length])
                del buffer[:total_length]

                try:
                    msg_type = MessageType(msg_type)
                except ValueError:
                    print(f"Unknown message type: {msg_type}")
                    continue

                if msg_type == MessageType.FILE_REQUEST:
                    try:
                        _, payload = Protocol.decode(message_data)
                    except Exception as exc:
                        print(f"Decode Error: {exc}")
                        continue

                    filename = safe_filename(payload["filename"])
                    filepath = os.path.join(RECEIVED_DIR, filename)
                    filesize = payload.get("filesize", 0)

                    if os.path.exists(filepath):
                        print(f"[ERROR] File already exists: {filename}")
                        packet = Protocol.error("File already exists.")
                        writer.write(packet)
                        await writer.drain()
                        continue

                    file_handle = open(filepath, "wb")
                    self.active_transfers[stream_id] = {
                        "filename": filename,
                        "filepath": filepath,
                        "filesize": filesize,
                        "received": 0,
                        "file": file_handle,
                    }
                    print(f"\nIncoming file: {filename} ({format_size(filesize)})")
                    continue

                if msg_type == MessageType.FILE_DATA:
                    transfer = self.active_transfers.get(stream_id)
                    if not transfer:
                        continue

                    offset, chunk = Protocol.decode_chunk(message_data)
                    transfer["file"].seek(offset)
                    transfer["file"].write(chunk)
                    transfer["file"].flush()
                    os.fsync(transfer["file"].fileno())
                    transfer["received"] += len(chunk)
                    progress = (transfer["received"] / transfer["filesize"] * 100) if transfer["filesize"] else 100.0
                    print(f"\rReceiving {transfer['filename']} {progress:6.2f}% ", end="", flush=True)
                    continue

                if msg_type == MessageType.FILE_COMPLETE:
                    transfer = self.active_transfers.pop(stream_id, None)
                    if transfer:
                        transfer["file"].flush()
                        transfer["file"].close()
                        print(f"\nCompleted: {transfer['filename']}")
                    continue

                if msg_type == MessageType.ERROR:
                    try:
                        _, payload = Protocol.decode(message_data)
                    except Exception as exc:
                        print(f"Decode Error: {exc}")
                        continue
                    print(f"Error from client: {payload.get('message', '')}")
                    continue

                if msg_type == MessageType.FILE_LIST:
                    files = os.listdir(RECEIVED_DIR)
                    response = Protocol.file_list_response(files)
                    writer.write(response)
                    await writer.drain()
                    continue

        if stream_id in self.active_transfers:
            transfer = self.active_transfers.pop(stream_id)
            transfer["file"].flush()
            transfer["file"].close()


async def run_server():
    configuration = QuicConfiguration(is_client=False, alpn_protocols=[ALPN_PROTOCOL])
    try:
        configuration.load_cert_chain(CERT_PATH, KEY_PATH)
    except FileNotFoundError:
        print("❌ ERROR: Certificates not found!")
        print("📋 Please generate certificates using: python generate_certs.py")
        return

    print("╔════════════════════════════════════════════════════════════╗")
    print("║              QUIC FILE TRANSFER SERVER                   ║")
    print("╠════════════════════════════════════════════════════════════╣")
    print("║ Server running on:                                      ║")
    print(f"║   - All interfaces: {SERVER_HOST}:{SERVER_PORT}              ║")
    print(f"║   - Local IP: {LOCAL_IP}:{SERVER_PORT}                    ║")
    print("║                                                         ║")
    print("║ Important: Use the LOCAL IP on other machines!         ║")
    print("║                                                         ║")
    print("║ To connect from another machine, use:                  ║")
    print(f"║   python client.py <filename> --server {LOCAL_IP}        ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print("\n📁 Files will be saved in: ./received/")
    print("🔄 Press Ctrl+C to stop the server\n")

    server = await serve(SERVER_HOST, SERVER_PORT, configuration=configuration, create_protocol=FileTransferServerProtocol)
    try:
        await asyncio.Event().wait()
    finally:
        if hasattr(server, "close"):
            server.close()


if __name__ == "__main__":
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as exc:
        import traceback
        print(f"❌ ERROR: Failed to start server: {exc}")
        traceback.print_exc()
