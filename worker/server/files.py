import asyncio
import threading

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path
import sqlite3
from pydantic import BaseModel

from worker.storage.migrations.files import create_files_table, get_file_by_filename, upsert_file, delete_file_by_filename

router = APIRouter()

# sqlite3 connections can only be used from the thread that created them
# unless check_same_thread=False, and the module isn't safe for concurrent
# use from multiple threads at once - serialize access with a lock so we
# can run db calls off the event loop without blocking it.
db_lock = threading.Lock()

def resolve_data_dir():
    preferred = Path("/data")
    fallback = Path("data")

    if preferred.exists() and preferred.is_dir():
        return preferred

    fallback.mkdir(parents=True, exist_ok=True)
    return fallback

def ensure_environment(base_dir: Path | str = "."):
    base = Path(base_dir)

    # required folders
    folders = ["input", "output", "temp"]

    for folder in folders:
        (base / folder).mkdir(parents=True, exist_ok=True)

    # sqlite database file
    db_path = base / "filesystem.db"

    conn = sqlite3.connect(db_path, check_same_thread=False)

    return {
        "base": base,
        "input": base / "input",
        "output": base / "output",
        "temp": base / "temp",
        "db": conn
    }


data_folder = resolve_data_dir()
environment = ensure_environment(data_folder)

conn = environment['db']

create_files_table(conn)

class FileRequest(BaseModel):
    hash: str
    size: int
    path: str
    filename: str
    dest_path: str

def _get_file_by_filename(filename: str):
    with db_lock:
        return get_file_by_filename(conn, filename)

def _delete_file_by_filename(filename: str):
    with db_lock:
        return delete_file_by_filename(conn, filename)

def _upsert_file(filename, hash, size, path, name_in_disk):
    with db_lock:
        return upsert_file(conn, filename, hash, size, path, name_in_disk)

## Receives metadata and tells client what files it needs
@router.post("/files")
async def files(payload: list[FileRequest]):
    from worker.execution.context import cache_lock
    async with cache_lock:
        return await _files(payload)

async def _files(payload: list[FileRequest]):
    needed_files: list[str] = []

    for file in payload:
        file_item = await asyncio.to_thread(_get_file_by_filename, file.dest_path)

        if not file_item:
            needed_files.append(file.path)
        else:
            # validate if the file changed
            hash = file_item['hash']
            size = file_item['size']

            if not Path(file_item["nameInDisk"]).exists(): # Check if file was deleted
                needed_files.append(file.path)
                continue

            if hash != file.hash or size != file.size:
                base = Path(environment["base"]).resolve()
                path = Path(file_item["nameInDisk"]).resolve()

                # check if path is inside base
                if base not in path.parents and path != base:
                    raise HTTPException(400, "invalid stored path")

                await asyncio.to_thread(_delete_file_by_filename, file.dest_path)

                if path.exists() and path.is_file():
                    path.unlink()

                needed_files.append(file.path)

    return needed_files

## Receives files and stores them
import uuid
import logging

logger = logging.getLogger("upload")

@router.put("/files")
async def upload(
    file: UploadFile = File(...),
    hash: str = Form(...),
    size: int = Form(...),
    path: str = Form(...),
    dest_path: str = Form(...),
):
    from worker.execution.context import cache_lock
    async with cache_lock:
        return await _upload(file, hash, size, path, dest_path)

async def _upload(file: UploadFile, hash: str, size: int, path: str, dest_path: str):
    if not file.filename:
        raise HTTPException(400, "missing filename")

    base = Path(environment["base"]).resolve()

    # normalize and force directory semantics
    dest_dir = (base / dest_path.lstrip("/")).resolve()

    # security check
    if base not in dest_dir.parents and dest_dir != base:
        raise HTTPException(400, "invalid destination path")

    # dest_path is always a complete file key, including extensionless files.
    dest_dir = dest_dir.parent

    dest_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename).suffix
    new_name = f"{uuid.uuid4()}{suffix}"
    dest = dest_dir / new_name

    chunk_size = 1024 * 1024
    written = 0

    f = await asyncio.to_thread(open, dest, "xb")
    try:
        try:
            while chunk := await file.read(chunk_size):
                await asyncio.to_thread(f.write, chunk)
                written += len(chunk)
                if written > size:
                    raise HTTPException(400, "upload exceeds declared size")
                percent = (written / size) * 100 if size > 0 else 0
                logger.debug("%s - %d/%d (%.1f%%)", file.filename, written, size, percent)
        finally:
            await asyncio.to_thread(f.close)
        if written != size:
            raise HTTPException(400, "incomplete upload")
        # The cache key becomes visible only after a complete upload.
        await asyncio.to_thread(_upsert_file, dest_path, hash, size, path, dest)
    except BaseException:
        dest.unlink(missing_ok=True)
        raise

    logger.info("%s - completed", file.filename)

    return {
        "status": "saved",
        "stored_as": new_name,
        "saved_to": str(dest),
    }