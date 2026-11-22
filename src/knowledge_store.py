"""Folder-scoped notes and text documents. SQLite supplies the local search index."""

import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATABASE = Path(__file__).resolve().parent.parent / "data" / "knowledge.sqlite3"
MAX_DOCUMENT_BYTES = 1024 * 1024


@contextmanager
def open_store(path=None):
    path = Path(path or DATABASE)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    try:
        with db:
            db.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS knowledge USING fts5(
                folder UNINDEXED, kind UNINDEXED, source, content
            )""")
            yield db
    finally:
        db.close()


def remember(db, folder, text):
    text = text.strip()
    if not text or len(text) > 4000:
        raise ValueError("Use between 1 and 4,000 characters for a memory.")
    row = db.execute(
        "INSERT INTO knowledge(folder, kind, source, content) VALUES (?, 'memory', 'Memory', ?)",
        (folder, text),
    )
    return row.lastrowid


def forget(db, folder, memory_id):
    result = db.execute(
        "DELETE FROM knowledge WHERE folder=? AND rowid=? AND kind='memory'",
        (folder, memory_id),
    )
    if not result.rowcount:
        raise ValueError(f"No memory #{memory_id} in this folder.")


def search(db, folder, query, limit=5):
    words = re.findall(r"[^\W_]+", query.casefold())[:24]
    if not words:
        return []
    expression = " OR ".join(f'"{word}"' for word in dict.fromkeys(words))
    return db.execute(
        """SELECT rowid AS id, source, content FROM knowledge
           WHERE knowledge MATCH ? AND folder=? ORDER BY rank, rowid LIMIT ?""",
        (expression, folder, limit),
    ).fetchall()


def references(folder, query):
    if not DATABASE.is_file():
        return []
    with open_store() as db:
        return [
            f"[{Path(row['source']).name}, excerpt {row['id']}] {row['content'][:800]}"
            for row in search(db, folder, query, 3)
        ]


def import_document(folder, path, database=None):
    path = Path(path)
    if path.suffix.lower() not in (".txt", ".md"):
        raise ValueError("Choose a UTF-8 .txt or .md document.")
    with path.open("rb") as stream:
        raw = stream.read(MAX_DOCUMENT_BYTES + 1)
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise ValueError("Choose a document of 1 MiB or less.")
    text = raw.decode("utf-8-sig").strip()
    if not text or "\x00" in text:
        raise ValueError("The document must contain readable text.")
    # Re-importing the same path replaces its old excerpts in one transaction.
    source = str(path.resolve())
    with open_store(database) as db:
        db.execute(
            "DELETE FROM knowledge WHERE folder=? AND kind='document' AND source=?",
            (folder, source),
        )
        for start in range(0, len(text), 900):
            db.execute(
                "INSERT INTO knowledge(folder, kind, source, content) VALUES (?, 'document', ?, ?)",
                (folder, source, text[start : start + 1000]),
            )


def list_memories(db, folder):
    return db.execute(
        "SELECT rowid AS id, content FROM knowledge WHERE folder=? AND kind='memory' ORDER BY rowid",
        (folder,),
    ).fetchall()
