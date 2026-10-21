"""Run the two development servers; Ctrl+C stops only our child processes."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def frontend_command() -> list[str]:
    node = shutil.which("node")
    if node is None:
        bundled = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
        node = str(bundled) if bundled.is_file() else None
    if node is None:
        raise RuntimeError("Install Node.js with npm, then reopen the PyCharm terminal.")
    npm_command = shutil.which("npm.cmd") or shutil.which("npm")
    candidates = [
        Path(npm_command).parent / "node_modules/npm/bin/npm-cli.js" if npm_command else ROOT / "work/missing-npm",
        Path(node).parent / "node_modules/npm/bin/npm-cli.js",
        ROOT / "work/tools/npm/package/bin/npm-cli.js",
    ]
    npm_cli = next((path for path in candidates if path.is_file()), None)
    if npm_cli is None:
        raise RuntimeError("Install Node.js with npm. The current Node runtime does not include npm.")
    if not (ROOT / "frontend/node_modules/@dcloudio/vite-plugin-uni").is_dir():
        raise RuntimeError("Install frontend dependencies first: cd frontend; npm ci")
    return [node, str(npm_cli), "run", "dev:h5"]


def stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name != "nt":
            os.killpg(process.pid, signal.SIGTERM)
        # In a Windows terminal Ctrl+C already reaches all inherited children.
        # Give them time to shut down before cleaning up any remaining tree.
        process.wait(timeout=3)
    except (OSError, subprocess.TimeoutExpired):
        if os.name == "nt":
            # The PID was created by this launcher; includes reload/npm workers.
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        else:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("component", choices=["all", "backend", "frontend"], default="all", nargs="?")
    args = parser.parse_args()
    commands: list[tuple[list[str], Path]] = []
    if args.component in {"all", "backend"}:
        commands.append(([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0",
                          "--port", "8000", "--reload", "--reload-dir", "app"], ROOT / "backend"))
    if args.component in {"all", "frontend"}:
        commands.append((frontend_command(), ROOT / "frontend"))
    processes: list[subprocess.Popen] = []
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    print("Web: http://localhost:5173  |  API: http://127.0.0.1:8000/docs", flush=True)
    print("Save Vue/CSS for HMR; save backend/app Python for API reload. Ctrl+C stops these servers.", flush=True)
    try:
        for command, cwd in commands:
            # Do not use CREATE_NEW_PROCESS_GROUP on Windows: it disables Ctrl+C
            # in descendants, breaking Uvicorn's reload worker shutdown.
            options = {} if os.name == "nt" else {"start_new_session": True}
            child_env = env.copy()
            child_env["PATH"] = str(Path(command[0]).parent) + os.pathsep + env.get("PATH", "")
            processes.append(subprocess.Popen(command, cwd=cwd, env=child_env, **options))
            print(f"Started {cwd.name}: PID {processes[-1].pid}", flush=True)
        reported = set()
        exit_code = 0
        while True:
            for index, process in enumerate(processes):
                if process.poll() is not None and index not in reported:
                    reported.add(index)
                    exit_code = process.returncode or exit_code
                    print(f"{commands[index][1].name} stopped: exit {process.returncode}. Other servers remain running.", flush=True)
            if len(reported) == len(processes):
                return exit_code
            time.sleep(0.5)
    except KeyboardInterrupt:
        return 0
    finally:
        for process in reversed(processes):
            stop_process(process)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
