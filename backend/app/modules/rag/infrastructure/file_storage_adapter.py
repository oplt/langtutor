from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from backend.app.core.config import BASE_DIR, settings


class LocalFileStorageAdapter:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or (BASE_DIR / settings.RAG_STORAGE_ROOT)
        self.root.mkdir(parents=True, exist_ok=True)

    def user_dir(self, user_id: str) -> Path:
        path = self.root / str(user_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_upload(self, *, user_id: str, filename: str, data: bytes) -> str:
        safe_name = f"{uuid.uuid4().hex}_{Path(filename).name}"
        dest = self.user_dir(user_id) / safe_name
        dest.write_bytes(data)
        return str(dest.relative_to(BASE_DIR))

    def resolve_path(self, storage_path: str) -> Path:
        path = Path(storage_path)
        if not path.is_absolute():
            path = BASE_DIR / storage_path
        return path

    def delete_file(self, storage_path: str) -> None:
        path = self.resolve_path(storage_path)
        if path.exists():
            path.unlink()

    def read_bytes(self, storage_path: str) -> bytes:
        return self.resolve_path(storage_path).read_bytes()


_storage: LocalFileStorageAdapter | None = None


def get_file_storage() -> LocalFileStorageAdapter:
    global _storage
    if _storage is None:
        _storage = LocalFileStorageAdapter()
    return _storage
