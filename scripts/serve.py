#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time


def _pid_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _read_pid(pid_file: str) -> int | None:
    try:
        with open(pid_file, "r", encoding="utf-8") as handle:
            return int(handle.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def _stop_existing(pid_file: str) -> None:
    pid = _read_pid(pid_file)
    if not pid or not _pid_is_running(pid):
        if pid:
            try:
                os.remove(pid_file)
            except FileNotFoundError:
                pass
        return

    os.kill(pid, signal.SIGTERM)
    for _ in range(50):
        if not _pid_is_running(pid):
            break
        time.sleep(0.1)
    if _pid_is_running(pid):
        os.kill(pid, signal.SIGKILL)
        for _ in range(50):
            if not _pid_is_running(pid):
                break
            time.sleep(0.1)

    try:
        os.remove(pid_file)
    except FileNotFoundError:
        pass


def _can_bind(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
    except OSError:
        return False
    return True


def _pick_livereload_port(host: str, preferred: int) -> int | None:
    for port in range(preferred, preferred + 101):
        if _can_bind(host, port):
            return port
    return None


def main() -> int:
    host = os.getenv("JEKYLL_HOST") or os.getenv("INTERNAL_NET_IP") or os.getenv("INTERNET_NET_IP") or "0.0.0.0"
    port = os.getenv("JEKYLL_PORT") or "4000"

    livereload = os.getenv("JEKYLL_LIVERELOAD", "1") not in {"", "0", "false", "False", "no", "No"}
    livereload_port = os.getenv("JEKYLL_LIVERELOAD_PORT") or "35729"
    watch = os.getenv("JEKYLL_WATCH", "1") not in {"", "0", "false", "False", "no", "No"}

    jekyll_config = os.getenv("JEKYLL_CONFIG") or "_config.yml"
    if os.getenv("JEKYLL_ENABLE_RST", "0") not in {"", "0", "false", "False", "no", "No"}:
        jekyll_config = f"{jekyll_config},_config.rst.yml"

    cmd = ["bundle", "exec", "jekyll", "serve", "--config", jekyll_config, "--host", host, "--port", port]
    if watch:
        cmd.append("--watch")
    if livereload:
        requested_port = int(livereload_port)
        picked_port = _pick_livereload_port(host, requested_port)
        if picked_port is None:
            print("LiveReload disabled (no available port in range).", file=sys.stderr)
        else:
            if picked_port != requested_port:
                print(
                    f"LiveReload port {requested_port} busy; using {picked_port} instead.",
                    file=sys.stderr,
                )
            cmd.extend(["--livereload", "--livereload-port", str(picked_port)])

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    pid_file = os.getenv("JEKYLL_PID_FILE") or os.path.join(repo_root, ".jekyll-serve.pid")
    _stop_existing(pid_file)

    proc = subprocess.Popen(cmd)
    with open(pid_file, "w", encoding="utf-8") as handle:
        handle.write(f"{proc.pid}\n")

    try:
        return proc.wait()
    finally:
        existing_pid = _read_pid(pid_file)
        if existing_pid == proc.pid:
            try:
                os.remove(pid_file)
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
