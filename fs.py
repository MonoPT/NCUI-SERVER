from pathlib import Path
from execution_context import scoped_key, folder, owner_id

from apis import environment
from migrations.files import get_file_by_filename

from fastapi import WebSocket

from node import UploadFile, UploadFolder

from events.event_types.upload_file import UploadFileMetadata

def load_asset(filename: str) -> Path | None:
    """Converts a path on the origin machine to the file on this container"""

    key = scoped_key(filename)
    file = get_file_by_filename(environment["db"], key)

    if file:
        path = Path(file["nameInDisk"])

        category = key.split("/")[1]
        root = (Path(environment["base"]) / "public") if category == "public" else storage_folder(category)
        root = root.absolute()
        absolute = path.absolute()
        if not absolute.is_relative_to(root):
            raise ValueError("Stored input outside owner storage")
        for part in (absolute, *absolute.parents):
            if part.is_symlink():
                raise ValueError("Symlink input")
            if part == root:
                break
        if path.is_file():
            return path.resolve()
        
    return None

def assets_folder() -> Path:
    raise RuntimeError("Use owner-scoped storage_folder(category)")

def storage_folder(category: str) -> Path:
    return folder(environment["base"], category)

async def send_image_to_client(
    ws: WebSocket,
    files: list[UploadFile]
):
    valid_files: list[UploadFile] = list()
    
    for file in files:
        #print(f"Trying to upload file: {file.path}")

        # Check if file exists
        if not file.path.exists() or not file.path.is_file():
            continue

        # Validate all files path, and ignore those which tries to upload to a invalid folder
        if not file.folder.value in [e.value for e in UploadFolder]:
            continue

        valid_files.append(file)        

    import uuid
    metadata: list[dict] = []

    # Communicate metadata
    for file in valid_files:
        category = "temp" if file.folder == UploadFolder.TEMP else "output"
        if file.path.resolve().parent != storage_folder(category).resolve() or file.path.is_symlink():
            raise ValueError("Upload outside owner storage")
        filename = file.path.name
        folder_value = file.folder.value

        metadata.append({"transfer_id": str(uuid.uuid4()), "filename": filename,
                         "folder": folder_value, "size": file.path.stat().st_size})

    await ws.send_json(
        UploadFileMetadata(metadata=metadata).to_dict()
    ) 

    # Upload frames refer only to the immutable transfer ID, never a filename.
    for file, item in zip(valid_files, metadata):
        transfer_header = uuid.UUID(item["transfer_id"]).bytes
    
        if file.path.stat().st_size == 0:
            await ws.send_bytes(transfer_header + b"\x01")
            continue
        with file.path.open("rb") as f:
            while True:
                chunk = f.read(64 * 1024)
    
                if not chunk:
                    break
    
                # Check if this is the final chunk
                is_last = f.tell() == file.path.stat().st_size
    
                final_flag = b"\x01" if is_last else b"\x00"
    
                await ws.send_bytes(
                    transfer_header + final_flag + chunk
                )


def resolve_path_to_main_machine(path: Path) -> Path:
    """Converts a path in the container machine to be usable in the user machine. """

    for category in ("output", "temp"):
        root = storage_folder(category).resolve()
        if path.resolve().parent == root:
            prefix = "/temp" if category == "temp" else "/assets/output"
            return Path(prefix) / path.name
    raise ValueError("Result outside owner storage")
    
__all__ = ["load_asset", "assets_folder", "send_image_to_client", "resolve_path_to_main_machine"]