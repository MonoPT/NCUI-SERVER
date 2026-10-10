import hashlib
import sqlite3
import unittest
from migrations.files import create_files_table, get_file_by_filename, upsert_file


class FileCacheTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
    def tearDown(self):
        self.conn.close()
    def test_identical_bytes_keep_private_and_public_keys_independent(self):
        create_files_table(self.conn)
        digest = hashlib.blake2b(b"identical").hexdigest()
        keys = ["/input/a/photo", "/input/b/photo", "/public/photo"]
        for key in keys:
            upsert_file(self.conn, key, digest, 9, key, "/cache" + key)
        for key in keys:
            self.assertEqual(get_file_by_filename(self.conn, key)["nameInDisk"], "/cache" + key)
        upsert_file(self.conn, keys[0], "new-hash", 3, "updated", "/cache/new")
        self.assertEqual(get_file_by_filename(self.conn, keys[0])["hash"], "new-hash")
        for key in keys[1:]:
            self.assertEqual(get_file_by_filename(self.conn, key)["hash"], digest)
    def legacy_schema(self):
        self.conn.execute("""CREATE TABLE files (
            id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT NOT NULL,
            hash TEXT NOT NULL UNIQUE, size INTEGER NOT NULL, path TEXT NOT NULL,
            nameInDisk TEXT NOT NULL, creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        for key, digest, date in [("/input/a/file", "old", "2025-01-01"),
                                  ("/input/a/file", "latest", "2026-01-01"),
                                  ("/public/file", "public", "2026-01-01")]:
            self.conn.execute("INSERT INTO files (filename,hash,size,path,nameInDisk,creation_date) VALUES (?,?,1,?,?,?)", (key, digest, key, "/cache/" + digest, date))
        self.conn.commit()
    def test_legacy_schema_upgrade_preserves_keys_and_is_idempotent(self):
        self.legacy_schema()
        create_files_table(self.conn)
        create_files_table(self.conn)
        self.assertEqual(get_file_by_filename(self.conn, "/input/a/file")["hash"], "latest")
        self.assertEqual(get_file_by_filename(self.conn, "/public/file")["nameInDisk"], "/cache/public")
        upsert_file(self.conn, "/input/b/file", "latest", 1, "b", "/cache/b")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM files").fetchone()[0], 3)
    def test_failed_schema_upgrade_rolls_back_original_metadata(self):
        self.legacy_schema()
        self.conn.set_authorizer(lambda action, *_: sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_DROP_TABLE else sqlite3.SQLITE_OK)
        with self.assertRaises(sqlite3.DatabaseError): create_files_table(self.conn)
        self.conn.set_authorizer(None)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM files").fetchone()[0], 3)
        self.assertIsNone(self.conn.execute("SELECT name FROM sqlite_master WHERE name='files_key_upgrade'").fetchone())
        create_files_table(self.conn)


if __name__ == "__main__": unittest.main()
