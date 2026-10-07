def create_files_table(conn):
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        hash TEXT NOT NULL UNIQUE,
        size INTEGER NOT NULL,
        path TEXT NOT NULL,
        nameInDisk TEXT NOT NULL,
        creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()


def get_file_by_filename(conn, filename: str):
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM files WHERE filename = ?",
        (filename,)
    )

    row = cursor.fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "filename": row[1],
        "hash": row[2],
        "size": row[3],
        "path": row[4],
        "nameInDisk": row[5],
        "creation_date": row[6],
    }

def upsert_file(conn, filename, hash, size, path, nameInDisk):
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO files (filename, hash, size, path, nameInDisk)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(hash) DO UPDATE SET
        filename = excluded.filename,
        size = excluded.size,
        path = excluded.path,
        nameInDisk = excluded.nameInDisk,
        creation_date = CURRENT_TIMESTAMP
    """, (filename, hash, size, str(path), str(nameInDisk)))

    conn.commit()

def delete_file_by_filename(conn, filename: str):
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM files WHERE filename = ?",
        (filename,)
    )

    conn.commit()

    return cursor.rowcount  # number of deleted rows