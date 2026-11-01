"""Start the private Streamlit worker behind the authenticated same-origin gateway."""
from __future__ import annotations

import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import uvicorn

from services.auth.gateway import create_app, load_settings


def _wait_for_worker(process: subprocess.Popen, port: int, timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Streamlit worker did not start.")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.25)
    raise RuntimeError("Streamlit worker startup timed out.")


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    settings = load_settings()
    env = os.environ.copy()
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_SERVER_ADDRESS"] = "127.0.0.1"
    env["STREAMLIT_SERVER_PORT"] = str(settings.streamlit_port)
    env["STREAMLIT_SERVER_ENABLE_CORS"] = "false"
    env["STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION"] = "false"
    command = [
        sys.executable, "-m", "streamlit", "run", str(root / "demo" / "app.py"),
        "--server.address=127.0.0.1", f"--server.port={settings.streamlit_port}",
        "--server.headless=true", "--server.enableCORS=false", "--server.enableXsrfProtection=false",
    ]
    worker = subprocess.Popen(command, cwd=root, env=env, stdin=subprocess.DEVNULL,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        _wait_for_worker(worker, settings.streamlit_port)
        uvicorn.run(create_app(settings=settings), host=os.environ.get("INDICNOTICE_AUTH_BIND", "127.0.0.1"),
                    port=int(os.environ.get("INDICNOTICE_AUTH_PORT", "8501")), log_level="warning")
    finally:
        if worker.poll() is None:
            worker.terminate()
            try:
                worker.wait(timeout=8)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait(timeout=5)


if __name__ == "__main__":
    main()
