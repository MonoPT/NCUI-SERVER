import asyncio
import importlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import fs
from execution_context import owner_context
from node import UploadFile, UploadFolder
from state import GlobalState

class WorkflowStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.owner_token = owner_context.set("a")
        self.environment = patch.dict(fs.environment, {"base": self.base})
        self.environment.start()
    def tearDown(self):
        self.environment.stop()
        owner_context.reset(self.owner_token)
        self.temp.cleanup()
    def test_lookup_uses_owner_key_and_rejects_foreign_storage(self):
        own = fs.storage_folder("input") / "photo"
        own.write_bytes(b"own")
        with patch.object(fs, "get_file_by_filename", return_value={"nameInDisk": str(own)}) as lookup:
            self.assertEqual(fs.load_asset("/input/photo"), own)
            self.assertEqual(lookup.call_args.args[1], "/input/a/photo")
        other = self.base / "input" / "b" / "secret"
        other.parent.mkdir()
        other.write_bytes(b"other")
        with patch.object(fs, "get_file_by_filename", return_value={"nameInDisk": str(other)}):
            with self.assertRaises(ValueError): fs.load_asset("/input/photo")
    def test_result_urls_and_empty_file_transfer(self):
        path = fs.storage_folder("temp") / "empty.jpg"
        path.write_bytes(b"")
        self.assertEqual(str(fs.resolve_path_to_main_machine(path)), "/temp/empty.jpg")
        class Socket:
            def __init__(self): self.json, self.binary = [], []
            async def send_json(self, event): self.json.append(event)
            async def send_bytes(self, data): self.binary.append(data)
        socket = Socket()
        asyncio.run(fs.send_image_to_client(socket, [UploadFile(path, UploadFolder.TEMP)]))
        self.assertEqual(len(socket.json), 1)
        self.assertEqual(len(socket.binary), 1)
        import uuid
        item = socket.json[0]["data"]["metadata"][0]
        self.assertEqual(item["filename"], "empty.jpg")
        self.assertEqual(item["size"], 0)
        self.assertEqual(socket.binary[0], uuid.UUID(item["transfer_id"]).bytes + b"\x01")
        with self.assertRaises(ValueError): fs.resolve_path_to_main_machine(self.base / "temp" / "b" / "secret")
    def test_same_filename_in_different_folders_has_distinct_transfer_ids(self):
        import uuid
        output = fs.storage_folder("output") / "same"
        temp = fs.storage_folder("temp") / "same"
        output.write_bytes(b"output")
        temp.write_bytes(b"temp")
        class Socket:
            def __init__(self): self.json, self.binary = [], []
            async def send_json(self, event): self.json.append(event)
            async def send_bytes(self, data): self.binary.append(data)
        socket = Socket()
        asyncio.run(fs.send_image_to_client(socket, [UploadFile(output, UploadFolder.OUTPUT), UploadFile(temp, UploadFolder.TEMP)]))
        items = socket.json[0]["data"]["metadata"]
        self.assertNotEqual(items[0]["transfer_id"], items[1]["transfer_id"])
        for item, frame, expected in zip(items, socket.binary, [b"output", b"temp"]):
            self.assertEqual(frame[:16], uuid.UUID(item["transfer_id"]).bytes)
            self.assertEqual(frame[16:], b"\x01" + expected)
    def test_csv_output_is_scoped_and_synchronized(self):
        import polars as pl
        module = importlib.import_module("nodes.dataframes.save_as_csv")
        with patch.object(module, "get_connect_value_by_input_handle_name", side_effect=[pl.DataFrame({"x": [1]}).lazy(), "report"]):
            result = module.func({"id": "node", "data": {}}, [], GlobalState())
        self.assertEqual(len(result.files_to_upload), 1)
        path = result.files_to_upload[0].path
        self.assertEqual(path, self.base / "output" / "a" / "report.csv")
        self.assertEqual(path.read_text(), "x\n1\n")
        self.assertEqual(str(fs.resolve_path_to_main_machine(path)), "/assets/output/report.csv")
    def test_dataframe_state_is_private(self):
        state = GlobalState()
        state.for_owner("a").models["model"] = "private"
        self.assertEqual(state.for_owner("a").models["model"], "private")
        self.assertNotIn("model", state.for_owner("b").models)

if __name__ == "__main__": unittest.main()
