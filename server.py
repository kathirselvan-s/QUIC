import asyncio
import os
import sys
from pathlib import Path
from aioquic.asyncio import serve
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived, ConnectionTerminated

from config import *
from protocol import Protocol, MessageType
from utils import ensure_directory

class FileTransferServer:
    def __init__(self):
        self.received_dir = RECEIVED_DIR
        ensure_directory(self.received_dir)
        
    async def handle_stream(self, stream_id, data, connection):
        """Handle incoming stream data"""
        msg_type, payload = Protocol.decode_message(data)
        
        if msg_type == MessageType.FILE_REQUEST:
            filename = payload['filename']
            filepath = os.path.join(self.received_dir, filename)
            
            # Send error if file already exists
            if os.path.exists(filepath):
                error_msg = f"File {filename} already exists"
                error_data = Protocol.encode_error(error_msg)
                connection.send_stream_data(stream_id, error_data, end_stream=True)
                return
            
            # Create file and prepare to receive data
            self.current_file = open(filepath, 'wb')
            self.current_filename = filename
            print(f"Receiving file: {filename}")
            
        elif msg_type == MessageType.FILE_DATA:
            if hasattr(self, 'current_file'):
                self.current_file.seek(payload['offset'])
                self.current_file.write(payload['data'])
                print(f"Received {len(payload['data'])} bytes at offset {payload['offset']}")
        
        elif msg_type == MessageType.FILE_COMPLETE:
            if hasattr(self, 'current_file'):
                self.current_file.close()
                filepath = os.path.join(self.received_dir, self.current_filename)
                file_size = os.path.getsize(filepath)
                print(f"File {self.current_filename} received successfully ({file_size} bytes)")
                delattr(self, 'current_file')
                delattr(self, 'current_filename')
        
        elif msg_type == MessageType.ERROR:
            print(f"Error from client: {payload['message']}")
    
    async def run(self):
        """Run the QUIC server"""
        configuration = QuicConfiguration(
            is_client=False,
            alpn_protocols=["file-transfer"],
        )
        configuration.load_cert_chain(CERT_PATH, KEY_PATH)
        
        async def connection_handler(connection, scope):
            # Handle stream events
            while True:
                event = await connection.wait_event()
                if isinstance(event, StreamDataReceived):
                    await self.handle_stream(event.stream_id, event.data, connection)
                elif isinstance(event, ConnectionTerminated):
                    break
        
        await serve(
            SERVER_HOST,
            SERVER_PORT,
            configuration=configuration,
            create_protocol=connection_handler,
        )
        print(f"Server listening on {SERVER_HOST}:{SERVER_PORT}")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(FileTransferServer().run())