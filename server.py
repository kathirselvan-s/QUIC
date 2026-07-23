import asyncio
import os
import sys
import signal
from pathlib import Path
from aioquic.asyncio import serve
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived, ConnectionTerminated

from config import *
from protocol import Protocol, MessageType
from utils import ensure_directory, safe_filename, format_size

class FileTransferServer:
    def __init__(self):
        self.received_dir = RECEIVED_DIR
        self.current_files = {}  # Handle multiple files simultaneously
        self.total_bytes_received = 0
        self.total_files_received = 0
        ensure_directory(self.received_dir)
        
    def get_client_info(self, connection):
        """Get client information"""
        try:
            if hasattr(connection, 'remote_address'):
                return connection.remote_address
            return "unknown"
        except:
            return "unknown"
        
    async def handle_stream(self, stream_id, data, connection):
        """Handle incoming stream data"""
        msg_type, payload = Protocol.decode_message(data)
        client_info = self.get_client_info(connection)
        
        if msg_type == MessageType.FILE_REQUEST:
            filename = safe_filename(payload['filename'])
            filepath = os.path.join(self.received_dir, filename)
            
            # Send error if file already exists
            if os.path.exists(filepath):
                error_msg = f"File {filename} already exists on server"
                error_data = Protocol.encode_error(error_msg)
                connection.send_stream_data(stream_id, error_data, end_stream=True)
                print(f"❌ [{client_info}] Rejected duplicate: {filename}")
                return
            
            # Create file and prepare to receive data
            try:
                self.current_files[stream_id] = {
                    'file': open(filepath, 'wb'),
                    'filename': filename,
                    'bytes_received': 0,
                    'client': client_info
                }
                print(f"📥 [{client_info}] Receiving: {filename}")
            except Exception as e:
                error_msg = f"Failed to create file: {str(e)}"
                error_data = Protocol.encode_error(error_msg)
                connection.send_stream_data(stream_id, error_data, end_stream=True)
                print(f"❌ [{client_info}] Error creating file: {e}")
            
        elif msg_type == MessageType.FILE_DATA:
            if stream_id in self.current_files:
                file_info = self.current_files[stream_id]
                try:
                    file_info['file'].seek(payload['offset'])
                    file_info['file'].write(payload['data'])
                    file_info['bytes_received'] += len(payload['data'])
                    self.total_bytes_received += len(payload['data'])
                    
                    # Progress update every 100KB
                    if file_info['bytes_received'] % 102400 < len(payload['data']):
                        size_str = format_size(file_info['bytes_received'])
                        print(f"📊 [{file_info['client']}] Received {size_str} of {file_info['filename']}")
                except Exception as e:
                    print(f"❌ Error writing file: {e}")
            else:
                error_data = Protocol.encode_error("No active file transfer")
                connection.send_stream_data(stream_id, error_data, end_stream=True)
        
        elif msg_type == MessageType.FILE_COMPLETE:
            if stream_id in self.current_files:
                file_info = self.current_files[stream_id]
                try:
                    file_info['file'].close()
                    filepath = os.path.join(self.received_dir, file_info['filename'])
                    file_size = os.path.getsize(filepath)
                    self.total_files_received += 1
                    
                    print(f"✅ [{file_info['client']}] Received: {file_info['filename']} ({format_size(file_size)})")
                    print(f"📊 Total: {self.total_files_received} files, {format_size(self.total_bytes_received)}")
                except Exception as e:
                    print(f"❌ Error completing file: {e}")
                finally:
                    del self.current_files[stream_id]
            else:
                print(f"⚠️  Received completion but no active file")
        
        elif msg_type == MessageType.ERROR:
            print(f"❌ [{client_info}] Error: {payload['message']}")
        
        elif msg_type == MessageType.FILE_LIST:
            # Request for file list
            files = os.listdir(self.received_dir)
            response = Protocol.encode_file_list_response(files)
            connection.send_stream_data(stream_id, response, end_stream=True)
    
    async def run(self):
        """Run the QUIC server"""
        configuration = QuicConfiguration(
            is_client=False,
            alpn_protocols=["file-transfer"],
        )
        
        # Load certificate
        try:
            configuration.load_cert_chain(CERT_PATH, KEY_PATH)
        except FileNotFoundError:
            print("❌ ERROR: Certificates not found!")
            print("📋 Please generate certificates using: python generate_certs.py")
            return
        
        async def connection_handler(connection, scope):
            # Handle stream events
            while True:
                event = await connection.wait_event()
                if isinstance(event, StreamDataReceived):
                    await self.handle_stream(event.stream_id, event.data, connection)
                elif isinstance(event, ConnectionTerminated):
                    # Clean up any open files for this connection
                    for stream_id in list(self.current_files.keys()):
                        if stream_id in self.current_files:
                            try:
                                self.current_files[stream_id]['file'].close()
                            except:
                                pass
                            del self.current_files[stream_id]
                    break
        
        try:
            await serve(
                SERVER_HOST,
                SERVER_PORT,
                configuration=configuration,
                create_protocol=connection_handler,
            )
            
            print("╔════════════════════════════════════════════════════════════╗")
            print("║              QUIC FILE TRANSFER SERVER                   ║")
            print("╠════════════════════════════════════════════════════════════╣")
            print(f"║ Server running on:                                      ║")
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
            
            # Handle shutdown gracefully
            loop = asyncio.get_event_loop()
            stop_event = asyncio.Event()
            
            def signal_handler():
                print("\n🛑 Shutting down server...")
                stop_event.set()
            
            for sig in [signal.SIGINT, signal.SIGTERM]:
                loop.add_signal_handler(sig, signal_handler)
            
            await stop_event.wait()
            
        except KeyboardInterrupt:
            print("\n🛑 Server stopped by user")
        except Exception as e:
            print(f"❌ ERROR: Failed to start server: {e}")

if __name__ == "__main__":
    asyncio.run(FileTransferServer().run())