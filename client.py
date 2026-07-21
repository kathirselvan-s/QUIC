import asyncio
import os
import sys
from aioquic.asyncio import connect
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived, ConnectionTerminated

from config import *
from protocol import Protocol, MessageType
from utils import get_file_size

class FileTransferClient:
    def __init__(self):
        self.send_dir = SEND_DIR
        
    async def send_file(self, filename):
        """Send a file to the server"""
        filepath = os.path.join(self.send_dir, filename)
        
        if not os.path.exists(filepath):
            print(f"Error: File {filename} not found in {self.send_dir}")
            return False
        
        configuration = QuicConfiguration(
            is_client=True,
            alpn_protocols=["file-transfer"],
        )
        configuration.load_verify_locations(CERT_PATH)
        
        # Connect to server
        async with connect(
            SERVER_HOST, SERVER_PORT,
            configuration=configuration,
        ) as connection:
            print(f"Connected to server at {SERVER_HOST}:{SERVER_PORT}")
            
            # Create a stream
            stream_id = connection.get_next_available_stream_id()
            
            # Send file request
            request_data = Protocol.encode_file_request(filename)
            connection.send_stream_data(stream_id, request_data, end_stream=False)
            
            # Send file data in chunks
            file_size = get_file_size(filepath)
            chunk_size = 8192
            offset = 0
            
            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    data_packet = Protocol.encode_file_data(chunk, offset)
                    connection.send_stream_data(stream_id, data_packet, end_stream=False)
                    offset += len(chunk)
                    print(f"Sent {offset}/{file_size} bytes")
                    
                    # Wait a bit to avoid overwhelming the server
                    await asyncio.sleep(0.01)
            
            # Send completion message
            complete_data = Protocol.encode_file_complete()
            connection.send_stream_data(stream_id, complete_data, end_stream=True)
            
            print(f"File {filename} sent successfully ({file_size} bytes)")
            
            # Wait for any response
            while True:
                event = await connection.wait_event()
                if isinstance(event, StreamDataReceived):
                    msg_type, payload = Protocol.decode_message(event.data)
                    if msg_type == MessageType.ERROR:
                        print(f"Server error: {payload['message']}")
                        return False
                elif isinstance(event, ConnectionTerminated):
                    break
            
            return True
    
    async def list_files(self):
        """List available files in send directory"""
        from utils import list_files
        files = list_files(self.send_dir)
        if files:
            print(f"Files available to send:")
            for f in files:
                size = get_file_size(os.path.join(self.send_dir, f))
                print(f"  - {f} ({size} bytes)")
        else:
            print(f"No files found in {self.send_dir}")

async def main():
    client = FileTransferClient()
    
    if len(sys.argv) < 2:
        print("Usage: python client.py <filename>")
        print("Or: python client.py --list")
        return
    
    if sys.argv[1] == "--list":
        await client.list_files()
    else:
        filename = sys.argv[1]
        await client.send_file(filename)

if __name__ == "__main__":
    asyncio.run(main())