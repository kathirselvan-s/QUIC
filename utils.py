import hashlib
import os
import shutil
import time
from pathlib import Path
from datetime import datetime


# ==========================================================
# Directory Utilities
# ==========================================================

def ensure_directory(path):
    """
    Create directory if it doesn't exist.
    """
    Path(path).mkdir(parents=True, exist_ok=True)


# ==========================================================
# File Utilities
# ==========================================================

def get_file_size(filepath):
    """
    Return file size in bytes.
    """
    return os.path.getsize(filepath)


def file_exists(filepath):
    """
    Check whether file exists.
    """
    return os.path.isfile(filepath)


def list_files(directory):
    """
    Return all files inside a directory.
    """
    ensure_directory(directory)

    return sorted(
        [
            f
            for f in os.listdir(directory)
            if os.path.isfile(os.path.join(directory, f))
        ]
    )


# ==========================================================
# File Information
# ==========================================================

def get_file_info(filepath):
    """
    Return file information.
    """

    stat = os.stat(filepath)

    return {
        "name": os.path.basename(filepath),
        "size": stat.st_size,
        "created": datetime.fromtimestamp(stat.st_ctime),
        "modified": datetime.fromtimestamp(stat.st_mtime),
    }


# ==========================================================
# SHA256
# ==========================================================

def sha256(filepath, chunk_size=1024 * 1024):
    """
    Calculate SHA256 checksum.
    """

    h = hashlib.sha256()

    with open(filepath, "rb") as f:

        while True:

            chunk = f.read(chunk_size)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


# ==========================================================
# Safe Filename
# ==========================================================

def safe_filename(filename):
    """
    Prevent directory traversal.
    """

    filename = os.path.basename(filename)

    invalid = '<>:"/\\|?*'

    for c in invalid:
        filename = filename.replace(c, "_")

    filename = filename.replace("..", "_")

    return filename


# ==========================================================
# Human Readable Size
# ==========================================================

def format_size(size):

    units = ["B", "KB", "MB", "GB", "TB"]

    size = float(size)

    for unit in units:

        if size < 1024:
            return f"{size:.2f} {unit}"

        size /= 1024

    return f"{size:.2f} PB"


# ==========================================================
# Human Readable Speed
# ==========================================================

def format_speed(bytes_per_sec):

    units = ["B/s", "KB/s", "MB/s", "GB/s"]

    speed = float(bytes_per_sec)

    for unit in units:

        if speed < 1024:
            return f"{speed:.2f} {unit}"

        speed /= 1024

    return f"{speed:.2f} TB/s"


# ==========================================================
# Progress Bar
# ==========================================================

def progress_bar(current, total, width=40):

    if total == 0:
        total = 1

    progress = current / total

    filled = int(width * progress)

    bar = "█" * filled + "░" * (width - filled)

    percent = progress * 100

    return f"[{bar}] {percent:6.2f}%"


# ==========================================================
# Copy File
# ==========================================================

def copy_file(src, dst):

    ensure_directory(os.path.dirname(dst))

    shutil.copy2(src, dst)


# ==========================================================
# Timer
# ==========================================================

class TransferTimer:

    def __init__(self):

        self.start = time.perf_counter()

    @property
    def elapsed(self):

        return time.perf_counter() - self.start

    def speed(self, transferred):

        elapsed = max(self.elapsed, 0.001)

        return transferred / elapsed


# ==========================================================
# Console Divider
# ==========================================================

def divider(title=None):

    line = "=" * 70

    if title:

        print(line)

        print(title)

        print(line)

    else:

        print(line)