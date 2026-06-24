from importlib import reload

import pytest


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("API_KEY", "my-secret-key")
    monkeypatch.setenv("POSTGRES_URI", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

    import core.settings as settings_module

    reload(settings_module)
    settings = settings_module.get_settings()

    assert settings.API_KEY == "my-secret-key"
    assert settings.POSTGRES_URI.startswith("postgresql+asyncpg://")
    assert settings.ENVIRONMENT == "testing"


def test_settings_singleton():
    import core.settings as settings_module

    reload(settings_module)
    s1 = settings_module.get_settings()
    s2 = settings_module.get_settings()
    assert s1 is s2
