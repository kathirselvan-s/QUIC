import os
import hashlib
from pathlib import Path

def get_file_hash(filepath, chunk_size=8192):
    """Calculate SHA-256 hash of a file"""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def ensure_directory(path):
    """Ensure a directory exists"""
    Path(path).mkdir(parents=True, exist_ok=True)

def get_file_size(filepath):
    """Get file size in bytes"""
    return os.path.getsize(filepath)

def list_files(directory):
    """List all files in a directory"""
    try:
        return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    except FileNotFoundError:
        return []
    