"""PDF-TOOL desktop launcher.

Starts the local PDF engine (FastAPI) on 127.0.0.1, then opens the app in its own
window (Edge/Chrome "app mode", no tabs or address bar). Closing that window stops
the engine again.

Flags:
  --no-browser   start the engine only and wait (Ctrl+C to stop)
  --check        start the engine, verify it answers, stop, exit 0/1 (used by the installer)
  --port N       preferred port (default 8765)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

APP_NAME = "PDF-TOOL"
DEFAULT_PORT = 8765
HERE = Path(__file__).resolve().parent
IS_WINDOWS = os.name == "nt"


# ----------------------------------------------------------------------------
# Locations (works both when installed and when run from a git checkout)
# ----------------------------------------------------------------------------
def find_backend() -> Path:
    for c in (HERE / "backend", HERE.parent / "backend"):
        if (c / "app" / "main.py").is_file():
            return c
    raise RuntimeError("Cannot find the 'backend' folder next to the launcher.")


def find_web() -> Path:
    for c in (HERE / "web", HERE.parent / "frontend" / "out"):
        if (c / "index.html").is_file():
            return c
    raise RuntimeError(
        "The web UI is missing (no 'web' / 'frontend/out' folder). "
        "Run `npm run build:desktop` inside the frontend folder, or re-run the installer."
    )


def data_dir() -> Path:
    if IS_WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    d = base / APP_NAME / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------
def message_box(text: str, title: str = APP_NAME, error: bool = False) -> None:
    if IS_WINDOWS:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, text, title, 0x10 if error else 0x40)
    else:
        print(f"[{title}] {text}", file=sys.stderr)


def health(port: int, timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=timeout) as r:
            return json.load(r).get("status") == "ok"
    except Exception:
        return False


def port_in_use(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def find_browser() -> str | None:
    override = os.environ.get("PDF_TOOL_BROWSER")
    if override and Path(override).is_file():
        return override
    if not IS_WINDOWS:
        for name in ("microsoft-edge", "google-chrome", "chromium", "chromium-browser"):
            p = shutil.which(name)
            if p:
                return p
        return None
    roots = [os.environ.get(k) for k in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA")]
    rels = [
        r"Microsoft\Edge\Application\msedge.exe",
        r"Google\Chrome\Application\chrome.exe",
        r"BraveSoftware\Brave-Browser\Application\brave.exe",
    ]
    for rel in rels:  # Edge first (ships with Windows), then Chrome, then Brave
        for root in roots:
            if root and (Path(root) / rel).is_file():
                return str(Path(root) / rel)
    return None


def browser_running(profile: Path) -> bool:
    """Windows: Chromium keeps profile\\lockfile open exclusively while it runs."""
    lf = profile / "lockfile"
    if not lf.exists():
        return False
    try:
        lf.open("rb").close()
        return False  # we could open it -> nobody holds it
    except OSError:
        return True


def quit_running_engine(data: Path) -> int:
    try:
        port = int((data / "engine.port").read_text().strip())
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/desktop/quit", method="POST",
                                     headers={"X-PDF-Tool": "1"})
        urllib.request.urlopen(req, timeout=3).read()
        print("PDF-TOOL stopped.")
    except Exception:
        print("PDF-TOOL is not running.")
    return 0


# ----------------------------------------------------------------------------
# Engine
# ----------------------------------------------------------------------------
def start_engine(port: int, data: Path, autoexit: bool = False) -> subprocess.Popen:
    backend, web = find_backend(), find_web()
    storage = data / "storage"
    env = os.environ.copy()
    env.update(
        STORAGE_DIR=str(storage),
        TMP_DIR=str(storage / "tmp"),
        OUTPUT_DIR=str(storage / "output"),
        WEB_DIR=str(web),
        # Only this app's own origin may call the local API.
        CORS_ORIGINS=f"http://127.0.0.1:{port}",
        PYTHONUNBUFFERED="1",
    )
    if autoexit:
        env["PDFTOOL_AUTOEXIT"] = "1"  # engine stops itself when the app window closes
    py = sys.executable
    if IS_WINDOWS and py.lower().endswith("pythonw.exe"):
        py = py[:-len("pythonw.exe")] + "python.exe"  # uvicorn needs real stdio
    (data / "engine.port").write_text(str(port))
    log = open(data / "server.log", "ab", buffering=0)
    kwargs = {}
    if IS_WINDOWS:
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.Popen(
        [py, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port),
         "--log-level", "warning"],
        cwd=str(backend) if not (data / ".env").exists() else str(data),  # .env (GROQ key) lives in data/
        env={**env, "PYTHONPATH": str(backend) + os.pathsep + env.get("PYTHONPATH", "")},
        stdout=log, stderr=log, stdin=subprocess.DEVNULL, **kwargs,
    )


def wait_ready(port: int, proc: subprocess.Popen | None, seconds: int = 45) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        if proc is not None and proc.poll() is not None:
            return False
        if health(port):
            return True
        time.sleep(0.25)
    return False


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--quit", action="store_true", help="stop a running PDF-TOOL engine")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = ap.parse_args()

    data = data_dir()
    if args.quit:
        return quit_running_engine(data)
    port = args.port
    proc: subprocess.Popen | None = None

    if health(port):
        pass  # PDF-TOOL engine already running (e.g. second window) -> reuse it
    else:
        if port_in_use(port):
            port = free_port()
        proc = start_engine(port, data, autoexit=not (args.check or args.no_browser))
        if not wait_ready(port, proc):
            if proc.poll() is None:
                proc.terminate()
            message_box(
                "The PDF engine could not start.\n\nDetails are in:\n" + str(data / "server.log"),
                error=True,
            )
            return 1

    url = f"http://127.0.0.1:{port}/"
    try:
        if args.check:
            ok = health(port)
            with urllib.request.urlopen(url, timeout=5) as r:
                ok = ok and r.status == 200 and b"PDF-TOOL" in r.read()
            print("PDF-TOOL self-check:", "OK" if ok else "FAILED")
            return 0 if ok else 1

        if args.no_browser:
            print(f"PDF-TOOL running at {url}  (Ctrl+C to stop)")
            while proc is None or proc.poll() is None:
                time.sleep(0.5)
            return 0

        browser = find_browser()
        profile = data / "browser-profile"
        if browser:
            subprocess.Popen([
                browser, f"--app={url}", f"--user-data-dir={profile}",
                "--no-first-run", "--no-default-browser-check", "--window-size=1280,860",
                "--disable-background-mode", "--disable-features=msStartupBoost",
            ])
        else:
            import webbrowser

            webbrowser.open(url)
        # The engine exits by itself once the window is closed. As a second signal (Windows),
        # also stop when the private browser profile is no longer in use.
        seen_locked, free_since = False, None
        while proc is not None and proc.poll() is None:
            time.sleep(0.5)
            if IS_WINDOWS and browser:
                if browser_running(profile):
                    seen_locked, free_since = True, None
                elif seen_locked:
                    free_since = free_since or time.time()
                    if time.time() - free_since > 8:
                        break
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(5)
            except subprocess.TimeoutExpired:
                proc.kill()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # pythonw has no console, so surface errors in a dialog
        message_box(f"{type(e).__name__}: {e}", error=True)
        sys.exit(1)
