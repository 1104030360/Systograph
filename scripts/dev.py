#!/usr/bin/env python3
"""Run the local API and Vite frontend together for development."""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Start the KAI-Mind local API and frontend dev server."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--frontend-port", type=int, default=5173)
    parser.add_argument(
        "--no-backend-reload",
        action="store_true",
        help="Start uvicorn without --reload.",
    )
    return parser.parse_args()


def resolve_command(name: str) -> str | None:
    return shutil.which(name)


def command_display(command: Sequence[str]) -> str:
    return " ".join(command)


def backend_command(args: argparse.Namespace) -> list[str]:
    uv = resolve_command("uv")
    if uv is None:
        raise RuntimeError(
            "Could not find `uv`. Install UV first, then run `uv sync`."
        )

    command = [
        uv,
        "run",
        "uvicorn",
        "kai_mind.web.app:create_app",
        "--factory",
        "--host",
        args.host,
        "--port",
        str(args.api_port),
    ]
    if not args.no_backend_reload:
        command.append("--reload")
    return command


def frontend_command(args: argparse.Namespace) -> list[str]:
    pnpm = resolve_command("pnpm")
    if pnpm is not None:
        return [
            pnpm,
            "run",
            "dev",
            "--",
            "--host",
            args.host,
            "--port",
            str(args.frontend_port),
        ]

    corepack = resolve_command("corepack")
    if corepack is not None:
        return [
            corepack,
            "pnpm",
            "run",
            "dev",
            "--",
            "--host",
            args.host,
            "--port",
            str(args.frontend_port),
        ]

    raise RuntimeError(
        "Could not find `pnpm` or `corepack`. Install Node.js with Corepack "
        "enabled, then run `corepack enable`."
    )


def stream_output(name: str, process: subprocess.Popen[str]) -> None:
    assert process.stdout is not None
    for line in process.stdout:
        print(f"[{name}] {line}", end="", flush=True)


def start_process(
    name: str,
    command: Sequence[str],
    cwd: Path,
    env: dict[str, str],
) -> subprocess.Popen[str]:
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    print(f"Starting {name}: {command_display(command)}")
    return subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )


def stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return

    if os.name == "nt":
        try:
            process.send_signal(signal.CTRL_BREAK_EVENT)
        except (AttributeError, ProcessLookupError, OSError):
            process.terminate()
    else:
        process.terminate()

    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def warn_if_frontend_dependencies_are_missing() -> None:
    if not (FRONTEND_DIR / "node_modules").exists():
        print(
            "Warning: frontend/node_modules was not found. If Vite fails to "
            "start, run `corepack pnpm --dir frontend install` first."
        )


def main() -> int:
    args = parse_args()
    warn_if_frontend_dependencies_are_missing()

    try:
        backend = backend_command(args)
        frontend = frontend_command(args)
    except RuntimeError as error:
        print(f"dev server setup failed: {error}", file=sys.stderr)
        return 1

    frontend_env = os.environ.copy()
    frontend_env.setdefault(
        "VITE_API_BASE_URL", f"http://{args.host}:{args.api_port}"
    )

    processes: list[subprocess.Popen[str]] = []
    threads: list[threading.Thread] = []

    try:
        processes.append(
            start_process("api", backend, ROOT, os.environ.copy())
        )
        processes.append(
            start_process("web", frontend, FRONTEND_DIR, frontend_env)
        )

        for name, process in zip(("api", "web"), processes, strict=True):
            thread = threading.Thread(
                target=stream_output,
                args=(name, process),
                daemon=True,
            )
            thread.start()
            threads.append(thread)

        print(
            f"\nAPI:      http://{args.host}:{args.api_port}\n"
            f"Frontend: http://{args.host}:{args.frontend_port}\n"
            "Press Ctrl+C to stop both servers.\n"
        )

        while True:
            for process in processes:
                exit_code = process.poll()
                if exit_code is not None:
                    print(
                        f"Process exited with code {exit_code}; "
                        f"stopping dev servers."
                    )
                    return exit_code
            time.sleep(0.25)
    except KeyboardInterrupt:
        print("\nStopping dev servers...")
        return 130
    finally:
        for process in reversed(processes):
            stop_process(process)
        for thread in threads:
            thread.join(timeout=1)


if __name__ == "__main__":
    raise SystemExit(main())
