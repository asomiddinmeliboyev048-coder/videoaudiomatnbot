import os
import uuid
from config import TEMP_DIR


def ensure_temp_dir():
    os.makedirs(TEMP_DIR, exist_ok=True)


def get_temp_path(extension: str) -> str:
    ensure_temp_dir()
    filename = f"{uuid.uuid4().hex}.{extension}"
    return os.path.join(TEMP_DIR, filename)


def cleanup_file(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass