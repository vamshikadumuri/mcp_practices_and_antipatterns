"""Start/stop the mlops Flask backend for benchmark runs and tests."""
import socket
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FlaskInfo:
    url: str
    port: int
    process: subprocess.Popen


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_healthy(url: str, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    health = url.rstrip("/") + "/health"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(health, timeout=1) as r:
                if r.status == 200:
                    return
        except Exception:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"Flask did not become healthy at {health} within {timeout}s")


@contextmanager
def running(log_path: Path | None = None):
    """Start the Flask backend, yield FlaskInfo, then shut it down."""
    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    env_extra = {"FLASK_PORT": str(port)}

    import os
    env = os.environ.copy()
    env.update(env_extra)

    log_file = open(log_path, "w") if log_path else subprocess.DEVNULL
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "mlops_backend.flask_app"],
            stderr=log_file,
            stdout=subprocess.DEVNULL,
            env=env,
        )
        try:
            _wait_healthy(url)
            yield FlaskInfo(url=url, port=port, process=proc)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
    finally:
        if log_path and log_file is not subprocess.DEVNULL:
            log_file.close()
