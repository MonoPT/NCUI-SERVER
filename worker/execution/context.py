"""Execution-local storage authority supplied by the trusted orchestration server."""
from contextvars import ContextVar
from pathlib import Path
import re
import asyncio

owner_context = ContextVar("workflow_owner")
execution_context = ContextVar("workflow_execution")

# Shared by every WebSocket execution and HTTP cache mutation on this worker.
# A dropped orchestration connection must not permit another connection's
# preparation to modify inputs before the original execution has stopped.
cache_lock = asyncio.Lock()

def owner_id():
    owner = owner_context.get()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", owner):
        raise ValueError("Invalid execution owner")
    return owner

def scoped_key(logical):
    parts = str(logical).lstrip("/").split("/")
    if parts[0] == "assets":
        parts = parts[1:]
    if len(parts) < 2 or any(p in ("", ".", "..") or "\\" in p or "\0" in p for p in parts):
        raise ValueError("Invalid asset path")
    if parts[0] == "public":
        return "/" + "/".join(parts)
    if parts[0] not in ("input", "output", "temp"):
        raise ValueError("Invalid asset category")
    return "/" + "/".join([parts[0], owner_id(), *parts[1:]])

def folder(base, category):
    if category not in ("input", "output", "temp"):
        raise ValueError("Invalid category")
    base = Path(base).absolute()
    path = base / category / owner_id()
    for ancestor in (base, base / category, path):
        if ancestor.is_symlink():
            raise ValueError("Symlink storage directory")
        ancestor.mkdir(exist_ok=True, parents=True)
    return path

def filename(value):
    value = str(value)
    if not value or value in (".", "..") or any(c in value for c in ("/", "\\", "\0")):
        raise ValueError("Invalid output filename")
    return value

class ExecutionSocket:
    def __init__(self, ws, token):
        self.ws, self.token = ws, token
    async def send_json(self, event):
        await self.ws.send_json({**event, "execution_id": self.token})
    async def send_bytes(self, data):
        await self.ws.send_bytes(data)
