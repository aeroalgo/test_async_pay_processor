import os
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlparse

import httpx
import pytest

from core.settings import get_settings, settings


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASE_URL = "http://127.0.0.1:8001"


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "ENVIRONMENT": settings.ENVIRONMENT,
            "POSTGRES_URI": settings.POSTGRES_URI,
            "RABBITMQ_URL": settings.RABBITMQ_URL,
            "API_KEY": settings.API_KEY,
            "OUTBOX_POLL_INTERVAL_SEC": str(settings.OUTBOX_POLL_INTERVAL_SEC),
            "WEBHOOK_MAX_RETRIES": str(settings.WEBHOOK_MAX_RETRIES),
            "WEBHOOK_RETRY_BASE_DELAY_SEC": str(settings.WEBHOOK_RETRY_BASE_DELAY_SEC),
        }
    )
    return env


def _is_server_ready(base_url: str) -> bool:
    try:
        response = httpx.get(f"{base_url}/api/v1/health", timeout=1.0)
    except httpx.HTTPError:
        return False
    return response.status_code == 200


def _wait_for_server(base_url: str, timeout_sec: float = 15.0) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if _is_server_ready(base_url):
            return
        time.sleep(0.25)
    raise RuntimeError(f"API server is not ready at {base_url}")


def _start_server(base_url: str) -> subprocess.Popen[bytes]:
    parsed = urlparse(base_url)
    port = str(parsed.port or 8001)
    env = _subprocess_env()
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            port,
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _start_consumer() -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import asyncio; from consumer.main import app; asyncio.run(app.run())",
        ],
        cwd=PROJECT_ROOT,
        env=_subprocess_env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _resolve_api_key(base_url: str) -> str:
    configured_key = get_settings().API_KEY
    candidates = [
        os.getenv("TEST_API_KEY"),
        configured_key,
    ]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            response = httpx.get(
                f"{base_url}/api/v1/health/protected",
                headers={"X-API-Key": candidate},
                timeout=2.0,
            )
        except httpx.HTTPError:
            continue
        if response.status_code == 200:
            return candidate
    raise RuntimeError("Unable to determine valid X-API-Key for API tests")


@pytest.fixture(scope="session")
def api_base_url() -> str:
    return os.getenv("TEST_API_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


@pytest.fixture(scope="session")
def webhook_base_url(api_base_url: str) -> str:
    return os.getenv("TEST_WEBHOOK_BASE_URL", api_base_url).rstrip("/")


@pytest.fixture(scope="session")
def ensure_api_server(api_base_url: str) -> Iterator[None]:
    process = None
    if not _is_server_ready(api_base_url):
        process = _start_server(api_base_url)
    try:
        _wait_for_server(api_base_url)
        yield
    finally:
        if process is not None:
            process.terminate()
            process.wait(timeout=10)


@pytest.fixture(scope="session")
def api_key(ensure_api_server, api_base_url: str) -> str:
    return _resolve_api_key(api_base_url)


@pytest.fixture(scope="session")
def ensure_consumer(ensure_api_server) -> Iterator[None]:
    process = _start_consumer()
    try:
        time.sleep(2.0)
        if process.poll() is not None:
            raise RuntimeError("Consumer failed to start")
        yield
    finally:
        process.terminate()
        process.wait(timeout=10)


@pytest.fixture(scope="session")
def api_headers(api_key: str) -> dict[str, str]:
    return {"X-API-Key": api_key}


@pytest.fixture(scope="session")
def test_client(ensure_api_server, ensure_consumer, api_base_url: str) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=api_base_url, timeout=10.0) as client:
        yield client
