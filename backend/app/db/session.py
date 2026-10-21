from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings

def create_db_engine(database_url: str) -> Engine:
    """Create an engine without connecting; apply SQLite settings per connection."""
    url = make_url(database_url)
    options = {}
    if url.get_backend_name() == "sqlite":
        options["connect_args"] = {"check_same_thread": False, "timeout": 10}
        if url.database in {None, "", ":memory:"}:
            options["poolclass"] = StaticPool
    db_engine = create_engine(url, **options)
    if url.get_backend_name() == "sqlite":
        @event.listens_for(db_engine, "connect")
        def configure_sqlite(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return db_engine


engine = create_db_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Provide one session per request and close it after the request."""
    with SessionLocal() as session:
        yield session


def get_request_db(request: Request) -> Generator[Session, None, None]:
    """Use the session factory belonging to this application, including tests."""
    with request.app.state.session_factory() as session:
        yield session
