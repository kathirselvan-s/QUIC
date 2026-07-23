import asyncio
import os
import sys
import socket
import argparse
from aioquic.asyncio import connect
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived, ConnectionTerminated

from config import *
from protocol import Protocol, MessageType
from utils import get_file_size, safe_filename, format_size, create_progress_bar

class FileTransferClient:
    def __init__(self, server_ip=None, server_port=None):
        self.send_dir = SEND_DIR
        self.server_ip = server_ip or SERVER_HOST
        self.server_port = server_port or SERVER_PORT
        self.connection_attempts = 3
        
    def get_local_ip(self):
        """Get the local IP address for logging"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "unknown"
        
    async def send_file(self, filename):
        """Send a file to the server"""
        filepath = os.path.join(self.send_dir, filename)
        
        if not os.path.exists(filepath):
            print(f"❌ Error: File {filename} not found in {self.send_dir}")
            return False
        
        # Sanitize filename
        filename = safe_filename(filename)
        file_size = get_file_size(filepath)
        
        configuration = QuicConfiguration(
            is_client=True,
            alpn_protocols=["file-transfer"],
        )
        
        # For self-signed certificates, disable verification
        try:
            configuration.load_verify_locations(CERT_PATH)
        except:
            print("⚠️  Certificate not found, using insecure mode")
            configuration.verify_mode = False
        
        # Connect to server
        for attempt in range(self.connection_attempts):
            try:
                print(f"📤 Connecting to {self.server_ip}:{self.server_port} (attempt {attempt+1}/{self.connection_attempts})...")
                async with connect(
                    self.server_ip, self.server_port,
                    configuration=configuration,
                ) as connection:
                    print(f"✅ Connected to server at {self.server_ip}:{self.server_port}")
                    
                    # Create a stream
                    stream_id = connection.get_next_available_stream_id()
                    
                    # Send file request
                    request_data = Protocol.encode_file_request(filename)
                    connection.send_stream_data(stream_id, request_data, end_stream=False)
                    
                    # Send file data in chunks
                    chunk_size = CHUNK_SIZE
                    offset = 0
                    bytes_sent = 0
                    
                    print(f"\n📁 Sending: {filename} ({format_size(file_size)})")
                    print("📊 Progress:")
                    
                    with open(filepath, 'rb') as f:
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            
                            data_packet = Protocol.encode_file_data(chunk, offset)
                            connection.send_stream_data(stream_id, data_packet, end_stream=False)
                            offset += len(chunk)
                            bytes_sent += len(chunk)
                            
                            # Update progress
                            progress = bytes_sent / file_size
                            bar = create_progress_bar(progress)
                            print(f"\r{bar} {bytes_sent}/{file_size} bytes", end='')
                            
                            # Small delay to prevent flooding
                            await asyncio.sleep(0.001)
                    
                    # Send completion message
                    complete_data = Protocol.encode_file_complete()
                    connection.send_stream_data(stream_id, complete_data, end_stream=True)
                    
                    print(f"\n\n✅ File sent successfully! ({format_size(file_size)})")
                    
                    # Wait for any response
                    error_received = False
                    while True:
                        try:
                            event = await asyncio.wait_for(connection.wait_event(), timeout=5.0)
                            if isinstance(event, StreamDataReceived):
                                msg_type, payload = Protocol.decode_message(event.data)
                                if msg_type == MessageType.ERROR:
                                    print(f"❌ Server error: {payload['message']}")
                                    error_received = True
                            elif isinstance(event, ConnectionTerminated):
                                break
                        except asyncio.TimeoutError:
                            break
                    
                    return not error_received
                    
            except ConnectionRefusedError:
                print(f"❌ Connection refused. Is the server running on {self.server_ip}:{self.server_port}?")
                if attempt < self.connection_attempts - 1:
                    await asyncio.sleep(1)
                continue
            except Exception as e:
                print(f"❌ Connection error: {e}")
                if attempt < self.connection_attempts - 1:
                    await asyncio.sleep(1)
                continue
        
        return False
    
    async def list_files(self):
        """List available files in send directory"""
        from utils import list_files
        files = list_files(self.send_dir)
        if files:
            print(f"📁 Files available to send:")
            print("━" * 50)
            for i, f in enumerate(files, 1):
                size = get_file_size(os.path.join(self.send_dir, f))
                print(f"  {i}. 📄 {f} ({format_size(size)})")
        else:
            print(f"❌ No files found in {self.send_dir}")
            print(f"📋 Place files in './{self.send_dir}/' directory")

    async def list_remote_files(self):
        """List files on the server"""
        configuration = QuicConfiguration(
            is_client=True,
            alpn_protocols=["file-transfer"],
        )
        
        try:
            configuration.load_verify_locations(CERT_PATH)
        except:
            configuration.verify_mode = False
        
        try:
            async with connect(
                self.server_ip, self.server_port,
                configuration=configuration,
            ) as connection:
                stream_id = connection.get_next_available_stream_id()
                request = Protocol.encode_file_list()
                connection.send_stream_data(stream_id, request, end_stream=False)
                
                # Wait for response
                while True:
                    event = await connection.wait_event()
                    if isinstance(event, StreamDataReceived):
                        msg_type, payload = Protocol.decode_message(event.data)
                        if msg_type == MessageType.FILE_LIST_RESPONSE:
                            files = payload['files']
                            print(f"📁 Files on server:")
                            print("━" * 50)
                            if files:
                                for i, f in enumerate(files, 1):
                                    print(f"  {i}. 📄 {f}")
                            else:
                                print("  No files on server")
                            return
                    elif isinstance(event, ConnectionTerminated):
                        break
        except Exception as e:
            print(f"❌ Failed to list remote files: {e}")

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='QUIC File Transfer Client',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python client.py --list                    # List local files
  python client.py file.txt                 # Send file to default server
  python client.py file.txt --server 192.168.1.100  # Send to specific server
  python client.py --remote-list            # List files on server
        '''
    )
    parser.add_argument('filename', nargs='?', help='File to send')
    parser.add_argument('--list', action='store_true', help='List local available files')
    parser.add_argument('--remote-list', action='store_true', help='List files on server')
    parser.add_argument('--server', default=SERVER_HOST, help='Server IP address')
    parser.add_argument('--port', type=int, default=SERVER_PORT, help='Server port')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Create client
    client = FileTransferClient(server_ip=args.server, server_port=args.port)
    local_ip = client.get_local_ip()
    
    print("╔════════════════════════════════════════════════════════════╗")
    print("║              QUIC FILE TRANSFER CLIENT                   ║")
    print("╠════════════════════════════════════════════════════════════╣")
    print(f"║ Local IP: {local_ip:<40} ║")
    print(f"║ Server:  {args.server}:{args.port:<33} ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    
    # Execute commands
    if args.list:
        await client.list_files()
    elif args.remote_list:
        await client.list_remote_files()
    elif args.filename:
        await client.send_file(args.filename)
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())