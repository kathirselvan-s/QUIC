
import asyncio
import os
import sys
import socket
import argparse
import time
import shutil
from pathlib import Path

# Fix Unicode output on Windows terminals (cp1252 → UTF-8)
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
from aioquic.asyncio import connect
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived, ConnectionTerminated

from config import *
from protocol import Protocol, MessageType
from utils import get_file_size, safe_filename, format_size, progress_bar

class FileTransferClient:
    def __init__(self, server_ip=None, server_port=None, local_ip=None, watch_folder=None):
        self.send_dir = watch_folder or SEND_DIR
        self.server_ip = server_ip or LOCAL_IP
        self.server_port = server_port or SERVER_PORT
        self.local_ip = local_ip
        self.connection_attempts = MAX_RETRIES
        self.sent_files = set()  # Track sent files to avoid duplicates
        self.processing_files = set()  # Track files currently being processed
        self.supported_extensions = {'.pdf', '.docx', '.png', '.jpg', '.jpeg', '.txt', '.csv', '.xlsx', '.pptx', '.zip', '.tar', '.gz', '.mp4', '.avi', '.mkv', '.mp3', '.wav', '.json', '.xml', '.html', '.css', '.js'}
        
    def get_local_ips(self):
        """Get all available local IP addresses"""
        ips = []
        try:
            # Get hostname and all IPs
            hostname = socket.gethostname()
            hostname_ips = socket.gethostbyname_ex(hostname)[2]
            
            for ip in hostname_ips:
                if ip != '127.0.0.1' and not ip.startswith('169.254.'):
                    ips.append((f"eth{len(ips)}", ip))
            
            if not ips:
                ips.append(('localhost', '127.0.0.1'))
            
            return ips
        except:
            try:
                ip = socket.gethostbyname(hostname)
                if ip and ip != '127.0.0.1':
                    return [('default', ip)]
            except:
                pass
            return []
        
    def get_local_ip(self):
        """Get the local IP address for logging"""
        if self.local_ip:
            return self.local_ip
        return get_local_ip()
    
    def get_file_metadata(self, filepath):
        """Get file metadata including size and modification time"""
        try:
            stat = os.stat(filepath)
            return {
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'created': stat.st_ctime
            }
        except:
            return None
    
    def is_supported_file(self, filename):
        """Check if file type is supported"""
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.supported_extensions
    
    def _make_quic_config(self):
        """Build a shared QuicConfiguration for client connections."""
        cfg = QuicConfiguration(
            is_client=True,
            alpn_protocols=[ALPN_PROTOCOL],
        )
        # Always disable peer verification for self-signed LAN certs.
        cfg.verify_peer = False
        try:
            cfg.load_verify_locations(CERT_PATH)
        except Exception:
            pass
        return cfg

    async def check_connection(self, timeout: float = 5.0) -> bool:
        """Verify the server is reachable with a lightweight QUIC handshake.

        Returns True if the handshake succeeds, False otherwise.
        Compatible with Python 3.7+ (uses asyncio.wait_for instead of asyncio.timeout).
        """
        print(f"\n🔍 Checking connection to {self.server_ip}:{self.server_port} ...", flush=True)

        async def _do_connect():
            async with connect(
                self.server_ip,
                self.server_port,
                configuration=self._make_quic_config(),
            ):
                pass  # Handshake succeeded — nothing else needed

        try:
            await asyncio.wait_for(_do_connect(), timeout=timeout)
            print(f"✅ Server is reachable at {self.server_ip}:{self.server_port}")
            return True
        except ConnectionRefusedError:
            print(f"❌ Connection refused — is the server running on {self.server_ip}:{self.server_port}?")
        except asyncio.TimeoutError:
            print(f"❌ Connection timed out — server unreachable at {self.server_ip}:{self.server_port}")
        except Exception as exc:
            print(f"❌ Connection failed: {exc}")
        return False

    async def send_single_file(self, filepath, keep_file=True):
        """Send a single file specified by its full/relative path to the server."""
        filepath = os.path.abspath(filepath)

        if not os.path.exists(filepath):
            print(f"❌ File not found: {filepath}")
            return False

        if not os.path.isfile(filepath):
            print(f"❌ Not a file: {filepath}")
            return False

        filename = os.path.basename(filepath)
        safe_name = safe_filename(filename)
        file_size = get_file_size(filepath)

        if file_size == 0:
            print(f"⚠️  Empty file: {filename} (skipping)")
            return False

        # ── Connectivity check before attempting transfer ──────────────────
        if not await self.check_connection():
            print("🚫 Transfer aborted — server not reachable.")
            return False
        print()

        configuration = self._make_quic_config()

        for attempt in range(self.connection_attempts):
            try:
                print(f"\n📤 Connecting to {self.server_ip}:{self.server_port} (attempt {attempt+1}/{self.connection_attempts})...")
                async with connect(
                    self.server_ip,
                    self.server_port,
                    configuration=configuration,
                ) as connection:
                    reader, writer = await connection.create_stream()

                    # Send file request
                    request_data = Protocol.file_request(safe_name, file_size)
                    writer.write(request_data)

                    # Send file data in chunks
                    chunk_size = CHUNK_SIZE
                    offset = 0
                    bytes_sent = 0

                    print(f"📤 Sending {safe_name} ({format_size(file_size)})")

                    with open(filepath, 'rb') as f:
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            data_packet = Protocol.file_chunk(offset, chunk)
                            writer.write(data_packet)
                            offset += len(chunk)
                            bytes_sent += len(chunk)
                            bar = progress_bar(bytes_sent, file_size)
                            print(f"\r📤 {safe_name}: {bar} {bytes_sent}/{file_size} bytes", end='')
                            await asyncio.sleep(0.001)

                    writer.write(Protocol.file_complete())
                    writer.write_eof()

                    print(f"\n✅ Sent: {safe_name} ({format_size(file_size)})")

                    if not keep_file:
                        try:
                            os.remove(filepath)
                            print(f"🗑️  Deleted: {filename}")
                        except Exception as e:
                            print(f"⚠️  Could not delete {filename}: {e}")

                    return True

            except ConnectionRefusedError:
                print(f"❌ Connection refused. Is server running on {self.server_ip}:{self.server_port}?")
                if attempt < self.connection_attempts - 1:
                    await asyncio.sleep(RETRY_DELAY)
                continue
            except Exception as e:
                print(f"❌ Error sending {filename}: {e}")
                import traceback
                traceback.print_exc()
                if attempt < self.connection_attempts - 1:
                    await asyncio.sleep(RETRY_DELAY)
                continue

        return False

    async def send_file(self, filename, move_after_send=False):
        """Send a file to the server"""
        filepath = os.path.join(self.send_dir, filename)
        
        if not os.path.exists(filepath):
            return False
        
        # Check file type
        if not self.is_supported_file(filename):
            print(f"⚠️  Unsupported file type: {filename} (skipping)")
            # Delete unsupported files to avoid cluttering
            try:
                os.remove(filepath)
                print(f"🗑️  Deleted unsupported file: {filename}")
            except:
                pass
            return False
        
        # Check if file is complete (not being written)
        if not self.is_file_complete(filepath):
            print(f"⏳ File {filename} is still being written, skipping...")
            return False
        
        # Check if already sent
        if filename in self.sent_files:
            return False
        
        # Check if being processed
        if filename in self.processing_files:
            return False
        
        # Add to processing set
        self.processing_files.add(filename)
        
        try:
            # Sanitize filename
            safe_name = safe_filename(filename)
            file_size = get_file_size(filepath)
            
            # Skip empty files
            if file_size == 0:
                print(f"⚠️  Empty file: {filename} (skipping)")
                try:
                    os.remove(filepath)
                    print(f"🗑️  Deleted empty file: {filename}")
                except:
                    pass
                self.processing_files.remove(filename)
                return False
            
            configuration = self._make_quic_config()

            for attempt in range(self.connection_attempts):
                try:
                    print(f"\n📤 Connecting to {self.server_ip}:{self.server_port} (attempt {attempt+1}/{self.connection_attempts})...")
                    
                    # Remove local_addr parameter as it might not be supported
                    async with connect(
                        self.server_ip, 
                        self.server_port,
                        configuration=configuration,
                    ) as connection:
                        reader, writer = await connection.create_stream()

                        # Send file request
                        request_data = Protocol.file_request(safe_name, file_size)
                        writer.write(request_data)

                        # Send file data in chunks
                        chunk_size = CHUNK_SIZE
                        offset = 0
                        bytes_sent = 0

                        print(f"📤 Sending {safe_name} ({format_size(file_size)})")
                        
                        with open(filepath, 'rb') as f:
                            while True:
                                chunk = f.read(chunk_size)
                                if not chunk:
                                    break

                                data_packet = Protocol.file_chunk(offset, chunk)
                                writer.write(data_packet)
                                offset += len(chunk)
                                bytes_sent += len(chunk)

                                # Update progress
                                progress = bytes_sent / file_size
                                bar = progress_bar(bytes_sent, file_size)
                                print(f"\r📤 {safe_name}: {bar} {bytes_sent}/{file_size} bytes", end='')
                                await asyncio.sleep(0.001)

                        complete_data = Protocol.file_complete()
                        writer.write(complete_data)
                        writer.write_eof()

                        print(f"\n✅ Sent: {safe_name} ({format_size(file_size)})")

                        # Mark as sent
                        self.sent_files.add(filename)
                        
                        # Move or delete file after successful send
                        if move_after_send:
                            # Move to archive folder
                            archive_dir = os.path.join(self.send_dir, 'sent')
                            os.makedirs(archive_dir, exist_ok=True)
                            dest_path = os.path.join(archive_dir, filename)
                            shutil.move(filepath, dest_path)
                            print(f"📦 Archived: {dest_path}")
                        else:
                            # Delete the file after sending
                            try:
                                os.remove(filepath)
                                print(f"🗑️  Deleted: {filename}")
                            except Exception as e:
                                print(f"⚠️  Could not delete {filename}: {e}")
                        
                        return True
                        
                except ConnectionRefusedError:
                    print(f"❌ Connection refused. Is server running on {self.server_ip}:{self.server_port}?")
                    if attempt < self.connection_attempts - 1:
                        await asyncio.sleep(RETRY_DELAY)
                    continue
                except Exception as e:
                    print(f"❌ Error sending {filename}: {e}")
                    import traceback
                    traceback.print_exc()
                    if attempt < self.connection_attempts - 1:
                        await asyncio.sleep(RETRY_DELAY)
                    continue
            
            return False
            
        finally:
            # Remove from processing set
            if filename in self.processing_files:
                self.processing_files.remove(filename)
    
    def is_file_complete(self, filepath):
        """Check if file is complete (not being written to)"""
        try:
            # Check if file is not being modified
            initial_size = os.path.getsize(filepath)
            time.sleep(0.5)  # Wait a bit
            final_size = os.path.getsize(filepath)
            
            # Check if file is complete and not being written
            return initial_size == final_size and initial_size > 0
        except:
            return False
    
    def get_new_files(self):
        """Get new files in the watch folder that haven't been sent"""
        new_files = []
        
        if not os.path.exists(self.send_dir):
            return new_files
        
        for filename in os.listdir(self.send_dir):
            filepath = os.path.join(self.send_dir, filename)
            
            # Skip directories
            if os.path.isdir(filepath):
                continue
            
            # Skip hidden files
            if filename.startswith('.'):
                continue
            
            # Skip files already sent or being processed
            if filename in self.sent_files or filename in self.processing_files:
                continue
            
            # Check if file is complete
            if self.is_file_complete(filepath):
                # Get file metadata
                metadata = self.get_file_metadata(filepath)
                if metadata and metadata['size'] > 0:
                    # Check if it's a supported file type
                    if self.is_supported_file(filename):
                        new_files.append((filename, metadata))
                    else:
                        # Delete unsupported files immediately
                        try:
                            os.remove(filepath)
                            print(f"\n🗑️  Deleted unsupported file: {filename}")
                        except:
                            pass
        
        # Sort by creation time (oldest first)
        new_files.sort(key=lambda x: x[1]['created'])
        return [f[0] for f in new_files]
    
    async def watch_and_send(self, interval=2, delete_after_send=True):
        """Watch folder and automatically send new files"""
        print(f"👁️  Watching folder: {self.send_dir}")
        print(f"📤 Will send files to: {self.server_ip}:{self.server_port}")
        print(f"🗑️  Delete after send: {'Yes' if delete_after_send else 'No (archive)'}")
        print(f"⏱️  Check interval: {interval} seconds")
        print(f"📋 Supported file types: {', '.join(sorted(self.supported_extensions))}")
        print("━" * 60)
        print("📊 Status: ", end='', flush=True)
        
        try:
            while True:
                # Get new files
                new_files = self.get_new_files()
                
                if new_files:
                    print(f"\n📁 Found {len(new_files)} new file(s)")
                    for filename in new_files:
                        print(f"   - {filename}")
                        
                        # Send the file
                        await self.send_file(filename, move_after_send=not delete_after_send)
                        
                        # Small delay between files
                        await asyncio.sleep(0.5)
                else:
                    # Print a simple status indicator
                    print(".", end='', flush=True)
                
                # Wait before checking again
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Stopped watching")
        except Exception as e:
            print(f"\n❌ Error in watch loop: {e}")
            import traceback
            traceback.print_exc()
    
    async def send_all_files(self, delete_after_send=True):
        """Send all files in the folder once"""
        files = self.get_new_files()
        if not files:
            print("No files to send")
            return
        
        print(f"📤 Sending {len(files)} files...\n")
        success_count = 0
        
        for filename in files:
            if await self.send_file(filename, move_after_send=not delete_after_send):
                success_count += 1
            await asyncio.sleep(0.5)
        
        print(f"\n✅ Sent {success_count}/{len(files)} files successfully")
    
    async def list_files(self):
        """List available files in send directory"""
        files = []
        if os.path.exists(self.send_dir):
            for f in os.listdir(self.send_dir):
                filepath = os.path.join(self.send_dir, f)
                if os.path.isfile(filepath) and not f.startswith('.'):
                    size = get_file_size(filepath)
                    files.append((f, size))
        
        if files:
            print(f"📁 Files in {self.send_dir}:")
            print("━" * 60)
            total_size = 0
            for i, (f, size) in enumerate(files, 1):
                status = "✅" if f in self.sent_files else "⏳"
                supported = "✓" if self.is_supported_file(f) else "✗"
                print(f"  {i}. {status} {f} ({format_size(size)}) [{'Supported' if supported == '✓' else 'Unsupported'}]")
                total_size += size
            print("━" * 60)
            print(f"Total: {len(files)} files, {format_size(total_size)}")
        else:
            print(f"❌ No files found in {self.send_dir}")
            print(f"📋 Place files in '{self.send_dir}' directory")

    async def list_remote_files(self):
        """List files on the server"""
        configuration = QuicConfiguration(
            is_client=True,
            alpn_protocols=[ALPN_PROTOCOL],
        )
        # Self-signed cert: always disable peer verification for LAN use.
        configuration.verify_peer = False
        try:
            configuration.load_verify_locations(CERT_PATH)
        except Exception:
            pass  # Cert file absent – verification already disabled above
        
        try:
            async with connect(
                self.server_ip, 
                self.server_port,
                configuration=configuration,
            ) as connection:
                reader, writer = await connection.create_stream()
                request = Protocol.file_list()
                writer.write(request)
                writer.write_eof()

                try:
                    response_data = await asyncio.wait_for(reader.read(65535), timeout=5.0)
                    if response_data:
                        msg_type, payload = Protocol.decode(response_data)
                        if msg_type == MessageType.FILE_LIST_RESPONSE:
                            files = payload['files']
                            print(f"📁 Files on server ({self.server_ip}:{self.server_port}):")
                            print("━" * 60)
                            if files:
                                for i, f in enumerate(files, 1):
                                    print(f"  {i}. 📄 {f}")
                            else:
                                print("  No files on server")
                            return
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for server response")
        except Exception as e:
            print(f"❌ Failed to list remote files: {e}")

    def display_available_interfaces(self):
        """Display available network interfaces and IPs"""
        ips = self.get_local_ips()
        if not ips:
            print("❌ No network interfaces found")
            return None
        
        print("\n🌐 Available Network Interfaces:")
        print("━" * 70)
        print(f"{'#':<3} {'Interface':<20} {'IP Address':<20} {'Status':<10}")
        print("━" * 70)
        
        for idx, (iface, ip) in enumerate(ips, 1):
            status = "🟢 Active"
            if ip.startswith('127.'):
                status = "🔴 Loopback"
            print(f"{idx:<3} {iface:<20} {ip:<20} {status:<10}")
        print("━" * 70)
        print("\n💡 To use a specific interface: --local-ip <IP_ADDRESS>")
        return ips

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='QUIC File Transfer Client - Automatic File Sender',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Watch a folder and send files automatically (delete after send)
  python client.py --watch ./output --server 192.168.1.100
  
  # Watch with specific local IP (for multi-homed systems)
  python client.py --watch ./output --local-ip 192.168.1.50 --server 10.0.0.5
  
  # Watch with custom interval (5 seconds)
  python client.py --watch ./output --interval 5 --server 192.168.1.100
  
  # Keep files after sending (archive them instead of deleting)
  python client.py --watch ./output --keep-files --server 192.168.1.100
  
  # Send all files in folder once (don't watch continuously)
  python client.py --send-all ./output --server 192.168.1.100
  
  # List files in the watch folder
  python client.py --list ./output
  
  # Show available network interfaces
  python client.py --show-ips
        '''
    )
    # Positional: python client.py myfile.txt --server IP
    parser.add_argument('file', nargs='?', metavar='FILE',
                        help='Path to a single file to send (alternative to --file)')
    parser.add_argument('--file', metavar='FILE', dest='file_flag',
                        help='Path to a single file to send')
    parser.add_argument('--ping', action='store_true',
                        help='Check connectivity to the server and exit')
    parser.add_argument('--watch', metavar='FOLDER', help='Watch folder and send files automatically')
    parser.add_argument('--send-all', metavar='FOLDER', help='Send all files in folder once')
    parser.add_argument('--list', metavar='FOLDER', help='List files in folder')
    parser.add_argument('--remote-list', action='store_true', help='List files on server')
    parser.add_argument('--server', default=None, help=f'Server IP address (default: {LOCAL_IP})')
    parser.add_argument('--port', type=int, default=SERVER_PORT, help=f'Server port (default: {SERVER_PORT})')
    parser.add_argument('--local-ip', help='Local IP address to bind to (note: may not be supported on all systems)')
    parser.add_argument('--interval', type=int, default=2, help='Watch interval in seconds (default: 2)')
    parser.add_argument('--keep-files', action='store_true', help='Keep files after sending (archive them)')
    parser.add_argument('--show-ips', action='store_true', help='Show available local IP addresses')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Get server IP (use default if not specified)
    server_ip = args.server if args.server else LOCAL_IP
    
    # Create client
    client = FileTransferClient(
        server_ip=server_ip, 
        server_port=args.port, 
        local_ip=args.local_ip,
        watch_folder=args.watch or args.send_all or args.list
    )
    # Resolve the single-file target from positional arg or --file flag
    single_file = getattr(args, 'file_flag', None) or getattr(args, 'file', None)
    local_ip = client.get_local_ip()
    
    # Show available IPs if requested
    if args.show_ips:
        client.display_available_interfaces()
        return
    
    print("╔════════════════════════════════════════════════════════════╗")
    print("║          QUIC FILE TRANSFER - AUTO SENDER                ║")
    print("╠════════════════════════════════════════════════════════════╣")
    print(f"║ Local IP: {local_ip:<40} ║")
    if args.local_ip:
        print(f"║ Bound to: {args.local_ip:<40} ║")
        print(f"║ ⚠️  Note: --local-ip may not be supported on all systems ║")
    print(f"║ Server:  {server_ip}:{args.port:<33} ║")
    if args.watch:
        print(f"║ Watching: {args.watch:<40} ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    
    # Execute commands
    if args.ping:
        ok = await client.check_connection()
        raise SystemExit(0 if ok else 1)
    elif args.remote_list:
        await client.list_remote_files()
    elif single_file:
        # Send a single specific file directly (no watch-folder, no auto-delete)
        await client.send_single_file(single_file, keep_file=args.keep_files)
    elif args.list:
        client.send_dir = args.list
        await client.list_files()
    elif args.send_all:
        client.send_dir = args.send_all
        await client.send_all_files(delete_after_send=not args.keep_files)
    elif args.watch:
        client.send_dir = args.watch
        await client.watch_and_send(interval=args.interval, delete_after_send=not args.keep_files)
    else:
        parser.print_help()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()