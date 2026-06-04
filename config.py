import os
from pathlib import Path


def get_minecraft_path() -> Path:
    if os.name == "nt":  # Windows
        return Path(os.environ["APPDATA"]) / ".minecraft"
    elif hasattr(os, "uname") and os.uname().sysname == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "minecraft"
    else:  # Linux
        return Path.home() / ".minecraft"
