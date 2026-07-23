from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import datetime
import os
import socket

def get_local_ips():
    """Get all local IP addresses for certificate SAN"""
    ips = set()
    try:
        # Get local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except:
        pass
    
    # Get hostname
    try:
        hostname = socket.gethostname()
        ips.add(socket.gethostbyname(hostname))
    except:
        pass
    
    return list(ips)

def generate_self_signed_cert():
    """Generate self-signed certificate with SAN for IP addresses"""
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Get all local IPs for SAN
    local_ips = get_local_ips()
    
    # Create certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "QUIC File Transfer"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])
    
    # Build SAN extension
    san_list = [x509.DNSName("localhost")]
    for ip in local_ips:
        san_list.append(x509.IPAddress(ip))
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName(san_list),
        critical=False,
    ).sign(private_key, hashes.SHA256(), default_backend())
    
    # Ensure certs directory exists
    os.makedirs("certs", exist_ok=True)
    
    # Save private key
    with open("certs/key.pem", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Save certificate
    with open("certs/cert.pem", "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    print("✅ Certificates generated successfully!")
    print(f"📋 Certificate includes IPs: {', '.join(local_ips)}")

if __name__ == "__main__":
    generate_self_signed_cert()