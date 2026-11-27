"""Local conversation archive. No project writes, tool replay or permission storage."""
from __future__ import annotations

import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from .transcript import from_json, to_json

MAX_CONVERSATIONS = 200


class ConversationStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self._db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS projects (alias TEXT PRIMARY KEY, project TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY, project TEXT NOT NULL, path TEXT NOT NULL,
                    title TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL,
                    transcript TEXT NOT NULL, session TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS heads (project TEXT PRIMARY KEY, conversation TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS conversation_updated ON conversations(updated);
            ''')
        os.chmod(self.path, 0o600)

    @contextmanager
    def _db(self):
        db = sqlite3.connect(str(self.path), timeout=2)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def project(self, alias=''):
        """A saved path aliases a stable identity; each unsaved project gets its own identity."""
        with self._db() as db:
            row = db.execute('SELECT project FROM projects WHERE alias=?', (alias,)).fetchone() if alias else None
            if row:
                return row['project']
            project = uuid.uuid4().hex
            if alias:
                db.execute('INSERT INTO projects VALUES (?, ?)', (alias, project))
            return project

    def alias(self, alias, project):
        if alias:
            with self._db() as db:
                db.execute('INSERT OR REPLACE INTO projects VALUES (?, ?)', (alias, project))

    def has_alias(self, alias):
        with self._db() as db:
            return db.execute('SELECT 1 FROM projects WHERE alias=?', (alias,)).fetchone() is not None

    def head(self, project):
        with self._db() as db:
            row = db.execute('SELECT conversation FROM heads WHERE project=?', (project,)).fetchone()
        return self.get(row['conversation']) if row else None

    def start(self, project, path=''):
        previous = self.head(project)
        if previous and not previous['transcript'] and not previous['session']:
            return previous['id']  # repeated clicks on an empty thread must not evict real conversations
        identifier = uuid.uuid4().hex
        self.save(identifier, project, [], path=path)
        return identifier

    def save(self, identifier, project, transcript, session=None, path=''):
        """Atomically checkpoint the thread and active pointer. None preserves the saved model session."""
        text = to_json(transcript)
        title = next((entry['text'] for entry in from_json(text) if entry['kind'] == 'user'), '')
        title = ' '.join(title.split())[:160]
        now = time.time()
        with self._db() as db:
            old = db.execute('SELECT project, session, title FROM conversations WHERE id=?', (identifier,)).fetchone()
            if old and old['project'] != project:
                raise ValueError('a conversation cannot move to another project')
            kept_session = str(session) if session is not None else old['session'] if old else ''
            title = old['title'] or title if old else title
            if len(kept_session) > 1_000_000:
                raise ValueError('model session exceeds the archive limit')
            db.execute('''INSERT INTO conversations VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET path=excluded.path, title=excluded.title,
                updated=excluded.updated, transcript=excluded.transcript, session=excluded.session''',
                       (identifier, project, path, title, now, now, text, kept_session))
            db.execute('INSERT OR REPLACE INTO heads VALUES (?, ?)', (project, identifier))
            # Keep the most recent conversations, including the newly opened empty one.
            db.execute("DELETE FROM conversations WHERE title<>'' AND id IN "
                       "(SELECT id FROM conversations WHERE title<>'' ORDER BY updated DESC LIMIT -1 OFFSET ?)",
                       (MAX_CONVERSATIONS,))
            db.execute('DELETE FROM heads WHERE conversation NOT IN (SELECT id FROM conversations)')
            db.execute("DELETE FROM conversations WHERE title='' AND id NOT IN (SELECT conversation FROM heads)")

    def get(self, identifier):
        with self._db() as db:
            row = db.execute('SELECT * FROM conversations WHERE id=?', (identifier,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result['transcript'] = from_json(result['transcript'])
        return result

    def list(self):
        with self._db() as db:
            rows = db.execute('SELECT id, project, path, title, created, updated FROM conversations '
                              "WHERE title<>'' ORDER BY updated DESC").fetchall()
        return [dict(row) for row in rows]
