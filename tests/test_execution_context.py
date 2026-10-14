import asyncio
from pathlib import Path
import tempfile
import unittest
from worker.execution.context import owner_context, owner_id, scoped_key, folder, filename, ExecutionSocket

class StorageContextTests(unittest.TestCase):
    def setUp(self):
        self.token = owner_context.set("user-a")
    def tearDown(self):
        owner_context.reset(self.token)
    def test_keys_separate_private_owners_and_share_only_public(self):
        self.assertEqual(scoped_key("/assets/input/photo.png"), "/input/user-a/photo.png")
        self.assertEqual(scoped_key("/public/shared"), "/public/shared")
        token = owner_context.set("user-b")
        try:
            self.assertEqual(scoped_key("/input/photo.png"), "/input/user-b/photo.png")
            # A supplied UUID is just a nested filename, never an owner override.
            self.assertEqual(scoped_key("/input/user-a/secret"), "/input/user-b/user-a/secret")
        finally:
            owner_context.reset(token)
    def test_creation_and_traversal(self):
        with tempfile.TemporaryDirectory() as base:
            for category in ("input", "output", "temp"):
                path = folder(base, category)
                self.assertEqual(path, Path(base) / category / "user-a")
                self.assertTrue(path.is_dir())
            for invalid in ("../secret", "a/b", "a\\b", ".", "..", ""):
                with self.assertRaises(ValueError): filename(invalid)
            for invalid in ("/input/../secret", "/input//file", "/other/file"):
                with self.assertRaises(ValueError): scoped_key(invalid)
    def test_missing_or_invalid_authority_fails_closed(self):
        token = owner_context.set("../other")
        try:
            with self.assertRaises(ValueError): owner_id()
        finally:
            owner_context.reset(token)
    def test_symlink_storage_denied(self):
        with tempfile.TemporaryDirectory() as base, tempfile.TemporaryDirectory() as other:
            (Path(base) / "output").symlink_to(other, target_is_directory=True)
            with self.assertRaises(ValueError): folder(base, "output")
    def test_event_transport_attaches_server_execution_token(self):
        class Socket:
            async def send_json(self, event): self.event = event
        socket = Socket()
        asyncio.run(ExecutionSocket(socket, "server-token").send_json({"name": "finished", "execution_id": "forged"}))
        self.assertEqual(socket.event["execution_id"], "server-token")

if __name__ == "__main__": unittest.main()
