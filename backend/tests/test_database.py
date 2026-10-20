import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db import session as database


def test_database_import_does_not_connect(tmp_path):
    root = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "not-created-on-import.db"
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite:///{database_path.as_posix()}"
    environment["PYTHONPATH"] = str(root)
    script = """
import os
import sqlite3
from sqlalchemy.engine import make_url

def unexpected_connection(*args, **kwargs):
    raise AssertionError("Importing the database module opened a connection")

sqlite3.connect = unexpected_connection
sqlite3.dbapi2.connect = unexpected_connection
from app.db.session import engine
assert engine.url == make_url(os.environ["DATABASE_URL"])
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert not database_path.exists()


def test_get_db_executes_query_and_closes_session(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'session.db').as_posix()}")
    session = sessionmaker(bind=engine)()
    close = Mock(wraps=session.close)
    monkeypatch.setattr(session, "close", close)
    monkeypatch.setattr(database, "SessionLocal", lambda: session)
    dependency = database.get_db()

    try:
        yielded_session = next(dependency)
        assert yielded_session is session
        assert yielded_session.scalar(text("SELECT 1")) == 1
    finally:
        dependency.close()
        engine.dispose()

    close.assert_called_once_with()
