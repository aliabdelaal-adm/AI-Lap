from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path
from typing import Literal

from fastapi import HTTPException, UploadFile

MediaKind = Literal["image", "audio"]
CHUNK_SIZE = 1024 * 1024


def detect_media_type(
    header: bytes, kind: MediaKind, filename: str | None = None
) -> str | None:
    if kind == "image":
        if header.startswith(b"\xff\xd8\xff"):
            return "jpg"
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"
        if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
            return "webp"
        return None

    if header.startswith(b"RIFF") and header[8:12] == b"WAVE":
        return "wav"
    if header.startswith(b"ID3") or (
        len(header) >= 2 and header[0] == 0xFF and header[1] & 0xE0 == 0xE0
    ):
        return "mp3"
    if (
        len(header) >= 12
        and header[4:8] == b"ftyp"
        and Path(filename or "").suffix.lower() == ".m4a"
    ):
        return "m4a"
    return None


def user_directory(data_dir: Path, user_id: str) -> Path:
    owner_key = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
    directory = data_dir / "users" / owner_key
    make_private_directory(directory)
    return directory


def make_private_directory(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "posix":
        os.chmod(directory, 0o700)


async def save_upload(
    upload: UploadFile,
    destination_dir: Path,
    kind: MediaKind,
    max_bytes: int,
) -> Path:
    path: Path | None = None
    total = 0
    header = bytearray()
    try:
        while chunk := await upload.read(CHUNK_SIZE):
            total += len(chunk)
            if total > max_bytes:
                raise HTTPException(status_code=413, detail=f"{kind} file is too large")
            if len(header) < 32:
                header.extend(chunk[: 32 - len(header)])
            if path is None:
                extension = detect_media_type(bytes(header), kind, upload.filename)
                if extension is not None:
                    make_private_directory(destination_dir)
                    path = destination_dir / f"{uuid.uuid4().hex}.{extension}"
                    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    with os.fdopen(fd, "wb") as output:
                        output.write(chunk)
                elif len(header) == 32:
                    raise HTTPException(
                        status_code=415,
                        detail=f"unsupported {kind} file signature",
                    )
            else:
                with path.open("ab") as output:
                    output.write(chunk)
        if total == 0:
            raise HTTPException(status_code=400, detail=f"{kind} file is empty")
        if path is None:
            extension = detect_media_type(bytes(header), kind, upload.filename)
            if extension is None:
                raise HTTPException(
                    status_code=415, detail=f"unsupported {kind} file signature"
                )
            make_private_directory(destination_dir)
            path = destination_dir / f"{uuid.uuid4().hex}.{extension}"
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd)
        return path
    except Exception:
        if path is not None:
            path.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()
