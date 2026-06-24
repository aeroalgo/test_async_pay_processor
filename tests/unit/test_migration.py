from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations" / "versions"


def test_initial_migration_exists():
    migrations = list(MIGRATIONS_DIR.glob("*.py"))
    assert len(migrations) >= 1


def test_initial_migration_creates_payments_and_outbox():
    content = _read_initial_migration()
    assert "payments" in content
    assert "outbox" in content
    assert "idempotency_key" in content


def test_initial_migration_has_outbox_partial_index():
    content = _read_initial_migration()
    assert "ix_outbox_status_pending" in content
    assert "status = 'pending'" in content


def _read_initial_migration() -> str:
    migrations = sorted(MIGRATIONS_DIR.glob("*.py"))
    assert migrations, "migration file not found"
    return migrations[0].read_text(encoding="utf-8")
