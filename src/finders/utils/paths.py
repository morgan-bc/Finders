"""Path utilities for finders user data directory."""
import os
from pathlib import Path


def get_finders_dir() -> Path:
    """获取 .finders 目录路径。"""
    return Path(os.environ.get("FINDERS_DIR", Path.home() / ".finders"))


def finders_path(*parts: str) -> Path:
    """构建 .finders 子路径。"""
    path = get_finders_dir() / Path(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def ensure_dir(path: Path) -> Path:
    """确保目录存在。"""
    path.mkdir(parents=True, exist_ok=True)
    return path
