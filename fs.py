from pathlib import Path

from apis import environment
from migrations.files import get_file_by_filename

from fastapi import WebSocket

from node import UploadFile, UploadFolder

from events.event_types.upload_file import UploadFileMetadata

def load_asset(filename: str) -> Path | None:
    """Converts a path on the origin machine to the file on this container"""

    file = get_file_by_filename(environment["db"] ,filename)

    if file:
        path = Path(file["nameInDisk"])

        if path.exists():
            return path.resolve()
        
    return None

def assets_folder() -> Path:
    return environment["base"]

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

    metadata: list[tuple[str, str]] = []

    # Communicate metadata
    for file in valid_files:
        filename = file.path.name
        folder_value = file.folder.value

        metadata.append((filename, folder_value))

    await ws.send_json(
        UploadFileMetadata(metadata=metadata).to_dict()
    ) 

    import struct
    
    # Upload file
    for file in valid_files:
        filename = file.path.name.encode("utf-8")
        
        filename_header = struct.pack("!I", len(filename)) + filename
    
        with file.path.open("rb") as f:
            while True:
                chunk = f.read(64 * 1024)
    
                if not chunk:
                    break
    
                # Check if this is the final chunk
                is_last = f.tell() == file.path.stat().st_size
    
                final_flag = b"\x01" if is_last else b"\x00"
    
                await ws.send_bytes(
                    filename_header + final_flag + chunk
                )


def resolve_path_to_main_machine(path: Path) -> Path:
    """Converts a path in the container machine to be usable in the user machine. """

    parts = str(path).split("data/")

    path_str = "data/".join(parts[1:])

    path_str = f"/{path_str}".replace("//", "/")
    
    return Path(path_str)
    
__all__ = ["load_asset", "assets_folder", "send_image_to_client", "resolve_path_to_main_machine"]