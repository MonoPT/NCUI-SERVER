import asyncio
from io import BytesIO
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from fastapi import HTTPException, UploadFile
import worker.server.files as apis
import worker.storage.files as fs
from worker.execution.context import owner_context
from worker.storage.migrations.files import create_files_table, get_file_by_filename


class CacheUploadTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        create_files_table(self.conn)
        self.patches = [patch("worker.execution.context.cache_lock", asyncio.Lock()),
                        patch.dict(apis.environment, {"base": self.base, "db": self.conn}),
                        patch("worker.server.files.conn", self.conn)]
        for item in self.patches: item.start()
    async def asyncTearDown(self):
        for item in reversed(self.patches): item.stop()
        self.conn.close()
        self.temp.cleanup()
    async def test_identical_content_uploads_keep_owner_and_public_cache_paths(self):
        keys = ["/input/owner-a/same", "/input/owner-b/same", "/public/same"]
        for key in keys:
            file = UploadFile(file=BytesIO(b"identical"), filename="same")
            result = await apis.upload(file, "same-hash", 9, "source" + key, key)
            self.assertEqual(result["status"], "saved")
        disk_paths = [get_file_by_filename(self.conn, key)["nameInDisk"] for key in keys]
        self.assertEqual(len(set(disk_paths)), 3)
        for key, disk_path in zip(keys, disk_paths):
            self.assertEqual(Path(disk_path).read_bytes(), b"identical")
            self.assertEqual(Path(disk_path).parent, (self.base / key.lstrip("/")).parent)
        for owner, key in zip(["owner-a", "owner-b"], keys):
            token = owner_context.set(owner)
            try:
                self.assertEqual(fs.load_asset("/input/same"), Path(get_file_by_filename(self.conn, key)["nameInDisk"]))
                self.assertEqual(fs.load_asset("/public/same"), Path(disk_paths[2]))
            finally:
                owner_context.reset(token)
    async def test_failed_and_truncated_uploads_are_not_published_or_left_on_disk(self):
        for size in [2, 4]:
            file = UploadFile(file=BytesIO(b"abc"), filename="same")
            with self.assertRaises(HTTPException):
                await apis.upload(file, "hash", size, "source", "/input/owner-a/same")
            self.assertIsNone(get_file_by_filename(self.conn, "/input/owner-a/same"))
            self.assertEqual(list((self.base / "input/owner-a").iterdir()), [])
        class BrokenUpload:
            filename = "same"
            calls = 0
            async def read(self, size):
                self.calls += 1
                if self.calls == 1: return b"x"
                raise OSError("connection lost")
        with self.assertRaises(OSError):
            await apis.upload(BrokenUpload(), "hash", 3, "source", "/input/owner-a/same")
        self.assertIsNone(get_file_by_filename(self.conn, "/input/owner-a/same"))
        self.assertEqual(list((self.base / "input/owner-a").iterdir()), [])


if __name__ == "__main__": unittest.main()
