import os

def resume_offset(part_path: str) -> int:
    return os.path.getsize(part_path) if os.path.exists(part_path) else 0
