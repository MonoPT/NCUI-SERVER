def _create_table(conn, name):
    conn.execute(f"""
        CREATE TABLE {name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL UNIQUE,
            hash TEXT NOT NULL,
            size INTEGER NOT NULL,
            path TEXT NOT NULL,
            nameInDisk TEXT NOT NULL,
            creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def create_files_table(conn):
    """Upgrade cache metadata atomically; never move or migrate storage files."""
    conn.execute("SAVEPOINT files_key_upgrade")
    try:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='files'"
        ).fetchone()
        if not exists:
            _create_table(conn, "files")
        else:
            unique_columns = []
            for index in conn.execute("PRAGMA index_list(files)").fetchall():
                if index[2]:
                    quoted = index[1].replace("'", "''")
                    unique_columns.append(tuple(
                        row[2] for row in conn.execute(f"PRAGMA index_info('{quoted}')")
                    ))
            if ("hash",) in unique_columns or ("filename",) not in unique_columns:
                _create_table(conn, "files_key_upgrade")
                # Old hash-keyed caches may contain several versions of one key.
                # Preserve the most recently recorded version and all distinct keys.
                conn.execute("""
                    INSERT INTO files_key_upgrade
                        (id, filename, hash, size, path, nameInDisk, creation_date)
                    SELECT id, filename, hash, size, path, nameInDisk, creation_date
                    FROM (
                        SELECT *, ROW_NUMBER() OVER (
                            PARTITION BY filename ORDER BY creation_date DESC, id DESC
                        ) AS version FROM files
                    ) WHERE version = 1
                """)
                conn.execute("DROP TABLE files")
                conn.execute("ALTER TABLE files_key_upgrade RENAME TO files")
        conn.execute("RELEASE SAVEPOINT files_key_upgrade")
    except BaseException:
        conn.execute("ROLLBACK TO SAVEPOINT files_key_upgrade")
        conn.execute("RELEASE SAVEPOINT files_key_upgrade")
        raise


def get_file_by_filename(conn, filename: str):
    row = conn.execute("SELECT * FROM files WHERE filename = ?", (filename,)).fetchone()
    if row is None:
        return None
    return dict(zip(
        ("id", "filename", "hash", "size", "path", "nameInDisk", "creation_date"), row
    ))


def upsert_file(conn, filename, hash, size, path, nameInDisk):
    with conn:
        conn.execute("""
            INSERT INTO files (filename, hash, size, path, nameInDisk)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(filename) DO UPDATE SET
                hash = excluded.hash,
                size = excluded.size,
                path = excluded.path,
                nameInDisk = excluded.nameInDisk,
                creation_date = CURRENT_TIMESTAMP
        """, (filename, hash, size, str(path), str(nameInDisk)))


def delete_file_by_filename(conn, filename: str):
    with conn:
        cursor = conn.execute("DELETE FROM files WHERE filename = ?", (filename,))
    return cursor.rowcount
