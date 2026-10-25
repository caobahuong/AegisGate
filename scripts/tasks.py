#!/usr/bin/env python3
"""Task runner for AegisGate.

Windows-first, cross-platform task runner providing unified commands for
development, testing, code quality checks, demo seeding, and cleanup.

Subcommands:
    python scripts/tasks.py dev     - Run backend + frontend together with prefixed logs
    python scripts/tasks.py test    - Run backend unit tests + frontend vitest
    python scripts/tasks.py check   - Run full CI checks (ruff, mypy, pytest, eslint, tsc, vitest)
    python scripts/tasks.py seed    - Seed demo data against simulated plugin
    python scripts/tasks.py clean   - Remove cache, build artifacts, and temporary files

Adheres strictly to python_clean_code.md:
- Full type hints
- Graceful signal handling and subprocess tree cleanup
"""

import argparse
import contextlib
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

# ANSI color codes
CYAN = "\033[96m"
MAGENTA = "\033[95m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_banner(msg: str, color: str = CYAN) -> None:
    """Print a visually distinct banner."""
    print(f"\n{color}{BOLD}=== {msg} ==={RESET}\n", flush=True)


def terminate_process_tree(proc: subprocess.Popen[str] | None) -> None:
    """Safely terminate a process and all of its recursive child processes."""
    if proc is None or proc.poll() is not None:
        return

    pid = proc.pid
    try:
        import psutil  # type: ignore[import-untyped]

        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
                child.terminate()
        parent.terminate()
        _, still_alive = psutil.wait_procs(children + [parent], timeout=3.0)
        for p in still_alive:
            with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
                p.kill()
    except Exception:
        # Fallback for Windows without psutil or unexpected exceptions
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            try:
                proc.terminate()
                proc.wait(timeout=2.0)
            except Exception:
                proc.kill()


def stream_output(pipe: Any, prefix: str, color: str) -> None:
    """Stream process stdout/stderr line-by-line with colored prefix."""
    try:
        for raw_line in iter(pipe.readline, ""):
            line = raw_line.rstrip()
            if line:
                print(f"{color}[{prefix}]{RESET} {line}", flush=True)
    except Exception:
        pass


def ensure_frontend_deps() -> None:
    """Automatically run npm install in frontend if node_modules is missing."""
    if not (FRONTEND_DIR / "node_modules").exists():
        print(f"\n{YELLOW}[frontend] node_modules not found. Running npm install...{RESET}", flush=True)
        cmd = ["npm", "install"]
        if sys.platform == "win32":
            cmd = ["cmd", "/c", "npm", "install"]
        res = subprocess.run(cmd, cwd=str(FRONTEND_DIR))
        if res.returncode != 0:
            print(f"{RED}[frontend] npm install failed!{RESET}", file=sys.stderr)
            sys.exit(res.returncode)


def run_dev(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run backend (uvicorn) and frontend (Next.js) concurrently with prefixed logs."""
    ensure_frontend_deps()
    print_banner("Starting AegisGate Development Servers (Backend + Frontend)", CYAN)

    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "core.main:app",
        "--host",
        host,
        "--port",
        str(port),
        "--reload",
    ]
    frontend_cmd = ["npm", "run", "dev"]
    if sys.platform == "win32":
        frontend_cmd = ["cmd", "/c", "npm", "run", "dev"]

    backend_proc: subprocess.Popen[str] | None = None
    frontend_proc: subprocess.Popen[str] | None = None

    def handle_exit(signum: int, frame: Any) -> None:
        print(f"\n{YELLOW}Received shutdown signal. Stopping services cleanly...{RESET}", flush=True)
        terminate_process_tree(backend_proc)
        terminate_process_tree(frontend_proc)
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    try:
        backend_proc = subprocess.Popen(
            backend_cmd,
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )

        frontend_proc = subprocess.Popen(
            frontend_cmd,
            cwd=str(FRONTEND_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        t_backend = threading.Thread(
            target=stream_output,
            args=(backend_proc.stdout, "backend", CYAN),
            daemon=True,
        )
        t_frontend = threading.Thread(
            target=stream_output,
            args=(frontend_proc.stdout, "frontend", MAGENTA),
            daemon=True,
        )
        t_backend.start()
        t_frontend.start()

        # Monitor both processes
        while True:
            b_code = backend_proc.poll()
            f_code = frontend_proc.poll()
            if b_code is not None:
                print(f"{RED}[backend] process exited with code {b_code}{RESET}", flush=True)
                break
            if f_code is not None:
                print(f"{RED}[frontend] process exited with code {f_code}{RESET}", flush=True)
                break
            time.sleep(0.5)

    except KeyboardInterrupt:
        handle_exit(signal.SIGINT, None)
    finally:
        terminate_process_tree(backend_proc)
        terminate_process_tree(frontend_proc)


def run_test() -> None:
    """Run backend unit tests and frontend vitest."""
    ensure_frontend_deps()
    print_banner("1/2 Running Backend Tests (pytest)", CYAN)
    pytest_cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--ignore=tests/browser_verification.py",
        "--ignore=tests/system_verification.py",
    ]
    res_b = subprocess.run(pytest_cmd, cwd=str(BASE_DIR))
    if res_b.returncode != 0:
        print(f"{RED}Backend tests failed!{RESET}", file=sys.stderr)
        sys.exit(res_b.returncode)

    print_banner("2/2 Running Frontend Tests (Vitest)", MAGENTA)
    npm_cmd = ["npx", "vitest", "run"]
    if sys.platform == "win32":
        npm_cmd = ["cmd", "/c", "npx", "vitest", "run"]

    res_f = subprocess.run(npm_cmd, cwd=str(FRONTEND_DIR))
    if res_f.returncode != 0:
        print(f"{RED}Frontend tests failed!{RESET}", file=sys.stderr)
        sys.exit(res_f.returncode)

    print(f"\n{GREEN}{BOLD}[OK] ALL TEST SUITES PASSED!{RESET}\n")


def run_check() -> None:
    """Run complete CI checks: ruff, mypy, pytest, eslint, tsc, vitest."""
    ensure_frontend_deps()
    print_banner("1/6 Backend Linting (Ruff)", CYAN)
    res = subprocess.run([sys.executable, "-m", "ruff", "check", "core", "plugins", "sdk", "tests"], cwd=str(BASE_DIR))
    if res.returncode != 0:
        sys.exit(res.returncode)

    print_banner("2/6 Backend Static Type Checking (Mypy)", CYAN)
    res = subprocess.run([sys.executable, "-m", "mypy", "core", "sdk"], cwd=str(BASE_DIR))
    if res.returncode != 0:
        sys.exit(res.returncode)

    print_banner("3/6 Backend Test Suite (Pytest)", CYAN)
    res = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--ignore=tests/browser_verification.py",
            "--ignore=tests/system_verification.py",
        ],
        cwd=str(BASE_DIR),
    )
    if res.returncode != 0:
        sys.exit(res.returncode)

    cmd_prefix = ["cmd", "/c"] if sys.platform == "win32" else []

    print_banner("4/6 Frontend Linting (ESLint)", MAGENTA)
    res = subprocess.run(cmd_prefix + ["npm", "run", "lint"], cwd=str(FRONTEND_DIR))
    if res.returncode != 0:
        sys.exit(res.returncode)

    print_banner("5/6 Frontend Static Type Checking (TypeScript tsc)", MAGENTA)
    res = subprocess.run(cmd_prefix + ["npx", "tsc", "--noEmit"], cwd=str(FRONTEND_DIR))
    if res.returncode != 0:
        sys.exit(res.returncode)

    print_banner("6/6 Frontend Unit Tests (Vitest)", MAGENTA)
    res = subprocess.run(cmd_prefix + ["npx", "vitest", "run"], cwd=str(FRONTEND_DIR))
    if res.returncode != 0:
        sys.exit(res.returncode)

    print(f"\n{GREEN}{BOLD}[OK] ALL CI CHECKS (6/6) PASSED CLEANLY!{RESET}\n")


def run_seed(extra_args: list[str]) -> None:
    """Run the idempotent demo seeder."""
    print_banner("Seeding AegisGate Demo Data", CYAN)
    cmd = [sys.executable, str(BASE_DIR / "scripts" / "seed_demo.py")] + extra_args
    res = subprocess.run(cmd, cwd=str(BASE_DIR))
    if res.returncode != 0:
        sys.exit(res.returncode)


def run_clean() -> None:
    """Remove cache directories, build artifacts, and temporary test profiles."""
    print_banner("Cleaning Temporary & Cache Artifacts", YELLOW)
    patterns_to_delete = [
        BASE_DIR / ".pytest_cache",
        BASE_DIR / ".mypy_cache",
        BASE_DIR / ".ruff_cache",
        BASE_DIR / ".coverage",
        BASE_DIR / "htmlcov",
        BASE_DIR / "build",
        BASE_DIR / "dist",
        BASE_DIR / "report" / "tmp",
        FRONTEND_DIR / ".next",
        FRONTEND_DIR / "out",
    ]

    for p in patterns_to_delete:
        if p.is_dir():
            print(f"Removing directory: {p.relative_to(BASE_DIR)}")
            shutil.rmtree(p, ignore_errors=True)
        elif p.is_file():
            print(f"Removing file: {p.relative_to(BASE_DIR)}")
            with contextlib.suppress(Exception):
                p.unlink()

    # Remove all __pycache__ and *.egg-info recursively
    removed_pycache = 0
    for root, dirs, _ in os.walk(str(BASE_DIR)):
        for d in list(dirs):
            if d == "__pycache__" or d.endswith(".egg-info"):
                target = Path(root) / d
                shutil.rmtree(target, ignore_errors=True)
                removed_pycache += 1

    print(f"Removed {removed_pycache} cache/egg-info folders.")
    print(f"\n{GREEN}[OK] Clean completed.{RESET}\n")


def main() -> None:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="AegisGate Task Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # dev
    dev_parser = subparsers.add_parser("dev", help="Run backend and frontend servers together.")
    dev_parser.add_argument("--host", default="127.0.0.1", help="Backend host interface (default: 127.0.0.1)")
    dev_parser.add_argument("--port", type=int, default=8000, help="Backend port (default: 8000)")

    # test
    subparsers.add_parser("test", help="Run backend unit tests and frontend vitest.")

    # check
    subparsers.add_parser("check", help="Run full CI verification suite (lint, types, tests).")

    # seed
    subparsers.add_parser("seed", help="Seed demonstration data against simulated plugin.")

    # clean
    subparsers.add_parser("clean", help="Remove cache, build artifacts, and temporary files.")

    args, extra = parser.parse_known_args()

    if args.command == "dev":
        run_dev(host=args.host, port=args.port)
    elif args.command == "test":
        run_test()
    elif args.command == "check":
        run_check()
    elif args.command == "seed":
        run_seed(extra)
    elif args.command == "clean":
        run_clean()


if __name__ == "__main__":
    main()
