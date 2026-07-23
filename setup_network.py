#!/usr/bin/env python3
"""
Network setup helper for QUIC File Transfer
Run this on both Windows and Linux to check network configuration
"""

import socket
import subprocess
import platform
import sys
import os

def get_local_ips():
    """Get all local IP addresses"""
    ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.append(s.getsockname()[0])
        s.close()
    except:
        pass
    
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if ip not in ips:
            ips.append(ip)
    except:
        pass
    
    return list(set(ips))

def check_port_available(port=4433):
    """Check if port is available"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result != 0
    except:
        return False

def get_os_info():
    """Get OS information"""
    return f"{platform.system()} {platform.release()}"

def get_firewall_status():
    """Check firewall status"""
    if platform.system() == "Windows":
        try:
            result = subprocess.run(['netsh', 'advfirewall', 'show', 'currentprofile'], 
                                  capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'State' in line:
                    return line.strip()
        except:
            return "Unknown (could not check)"
    elif platform.system() == "Linux":
        try:
            result = subprocess.run(['sudo', 'ufw', 'status'], 
                                  capture_output=True, text=True)
            return "UFW Status: " + result.stdout.split('\n')[0]
        except:
            return "Unknown (could not check)"
    return "Unknown"

def main():
    print("╔════════════════════════════════════════════════════════════╗")
    print("║        QUIC FILE TRANSFER - NETWORK SETUP                ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    
    # OS Information
    print(f"🖥️  Operating System: {get_os_info()}")
    print(f"🐍 Python Version: {sys.version.split()[0]}")
    print()
    
    # Local IP Addresses
    print("📡 Local IP Addresses:")
    ips = get_local_ips()
    if ips:
        for i, ip in enumerate(ips, 1):
            print(f"   {i}. {ip}")
    else:
        print("   ⚠️  No IP addresses found!")
    print()
    
    # Port availability
    print(f"🔌 Port {4433} (UDP):")
    if check_port_available(4433):
        print("   ✅ Port is available")
    else:
        print("   ⚠️  Port is in use or blocked")
    print()
    
    # Firewall status
    print("🔒 Firewall Status:")
    print(f"   {get_firewall_status()}")
    print()
    
    # Network connectivity check
    print("🌐 Network Interfaces:")
    if platform.system() == "Windows":
        try:
            result = subprocess.run(['ipconfig'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'IPv4' in line or 'IP Address' in line:
                    print(f"   {line.strip()}")
        except:
            print("   Could not retrieve network interface information")
    else:  # Linux/Mac
        try:
            result = subprocess.run(['ifconfig'], capture_output=True, text=True)
            current_iface = ""
            for line in result.stdout.split('\n'):
                if line and not line.startswith(' '):
                    current_iface = line.split(':')[0] if ':' in line else line.split()[0]
                elif 'inet ' in line and '127.0.0.1' not in line:
                    ip = line.strip().split()[1]
                    print(f"   {current_iface}: {ip}")
        except:
            try:
                result = subprocess.run(['ip', 'addr'], capture_output=True, text=True)
                current_iface = ""
                for line in result.stdout.split('\n'):
                    if line and ':' in line and not line.startswith(' '):
                        current_iface = line.split(':')[1].strip()
                    elif 'inet ' in line and '127.0.0.1' not in line:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            ip = parts[1].split('/')[0]
                            print(f"   {current_iface}: {ip}")
            except:
                print("   Could not retrieve network interface information")
    print()
    
    # Next steps
    print("╔════════════════════════════════════════════════════════════╗")
    print("║                    NEXT STEPS                            ║")
    print("╠════════════════════════════════════════════════════════════╣")
    print("║ 1. On the SERVER machine, run:                          ║")
    print("║    python server.py                                      ║")
    print("║                                                         ║")
    print("║ 2. On the CLIENT machine, use the server IP:            ║")
    print("║    python client.py <filename> --server <SERVER_IP>     ║")
    print("║                                                         ║")
    print("║ Example:                                                ║")
    print("║    python client.py test.txt --server 192.168.1.100    ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

if __name__ == "__main__":
    main()