import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_default_frontend_origins_are_explicit(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    assert Settings(_env_file=None).cors_origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


@pytest.mark.parametrize(
    "origins", [["*"], ["http://localhost:5173", "*"]]
)
def test_wildcard_origin_is_rejected(origins):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins=origins)


def test_settings_read_environment_values(monkeypatch):
    monkeypatch.setenv("APP_NAME", "Family Banking Test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test-settings.db")
    monkeypatch.setenv("CORS_ORIGINS", '["http://192.168.1.20:5173"]')

    settings = Settings(_env_file=None)

    assert settings.app_name == "Family Banking Test"
    assert settings.database_url == "sqlite:///./test-settings.db"
    assert settings.cors_origins == ["http://192.168.1.20:5173"]
