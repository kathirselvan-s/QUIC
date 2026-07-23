import os
import hashlib
import shutil
from pathlib import Path
from datetime import datetime

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

def get_file_info(filepath):
    """Get detailed file information"""
    stat = os.stat(filepath)
    return {
        'name': os.path.basename(filepath),
        'size': stat.st_size,
        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        'hash': get_file_hash(filepath)
    }

def safe_filename(filename):
    """Sanitize filename to prevent path traversal"""
    # Remove any path separators
    filename = os.path.basename(filename)
    # Remove any dangerous characters
    dangerous_chars = ['/', '\\', '..', ':', '*', '?', '"', '<', '>', '|']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    return filename

def format_size(size_bytes):
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

def create_progress_bar(progress, width=30):
    """Create a progress bar string"""
    filled = int(width * progress)
    bar = '█' * filled + '░' * (width - filled)
    return f"[{bar}] {progress*100:.1f}%"