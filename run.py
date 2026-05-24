from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
BACKEND_HOST = os.getenv("JOGAYJOGA_BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.getenv("JOGAYJOGA_BACKEND_PORT", "8001"))
FRONTEND_HOST = os.getenv("JOGAYJOGA_FRONTEND_HOST", "127.0.0.1")
FRONTEND_PORT = int(os.getenv("JOGAYJOGA_FRONTEND_PORT", "8501"))


def streamlit_executable() -> str:
    if os.name == "nt":
        candidate = ROOT_DIR / ".venv" / "Scripts" / "streamlit.exe"
    else:
        candidate = ROOT_DIR / ".venv" / "bin" / "streamlit"
    return str(candidate) if candidate.exists() else "streamlit"


def can_bind(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
        return True
    except OSError:
        return False


def find_available_port(host: str, preferred_port: int) -> int:
    if can_bind(host, preferred_port):
        return preferred_port

    for port in range(preferred_port + 1, preferred_port + 50):
        if can_bind(host, port):
            print(
                f"[run] port {preferred_port} unavailable; using {port} instead",
                flush=True,
            )
            return port

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        port = sock.getsockname()[1]
        print(
            f"[run] no nearby port available; using random free port {port}",
            flush=True,
        )
        return int(port)


def start_process(name: str, command: list[str], env: dict[str, str]) -> subprocess.Popen:
    print(f"[run] starting {name}: {' '.join(command)}", flush=True)
    return subprocess.Popen(command, cwd=ROOT_DIR, env=env)


def stop_process(name: str, process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return

    print(f"[run] stopping {name}...", flush=True)
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        print(f"[run] killing {name}...", flush=True)
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    backend_port = find_available_port(BACKEND_HOST, BACKEND_PORT)
    frontend_port = find_available_port(FRONTEND_HOST, FRONTEND_PORT)

    env = os.environ.copy()
    env["JOGAYJOGA_API_URL"] = f"http://{BACKEND_HOST}:{backend_port}"

    backend = start_process(
        "backend",
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.backend.main:app",
            "--host",
            BACKEND_HOST,
            "--port",
            str(backend_port),
            "--reload",
        ],
        env,
    )
    frontend = start_process(
        "frontend",
        [
            streamlit_executable(),
            "run",
            "app/frontend/streamlit_app.py",
            "--server.address",
            FRONTEND_HOST,
            "--server.port",
            str(frontend_port),
        ],
        env,
    )

    print(f"[run] backend:  http://{BACKEND_HOST}:{backend_port}", flush=True)
    print(f"[run] frontend: http://{FRONTEND_HOST}:{frontend_port}", flush=True)
    print("[run] press Ctrl+C to stop both services", flush=True)

    processes = {"frontend": frontend, "backend": backend}

    def handle_stop(signum: int, frame: object) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, handle_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_stop)

    try:
        while True:
            for name, process in processes.items():
                return_code = process.poll()
                if return_code is not None:
                    print(f"[run] {name} exited with code {return_code}", flush=True)
                    return return_code
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[run] shutting down...", flush=True)
        return 0
    finally:
        stop_process("frontend", frontend)
        stop_process("backend", backend)


if __name__ == "__main__":
    raise SystemExit(main())
