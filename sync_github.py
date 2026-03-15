"""
Auto-sync: watches for file changes and commits + pushes to GitHub automatically.
Run with: py sync_github.py
Stop with: Ctrl+C
"""

import subprocess
import time
import sys
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

WATCH_DIR = Path(__file__).parent
WATCH_EXTENSIONS = {".py", ".txt", ".md"}
IGNORE_DIRS = {"venv", "__pycache__", ".git"}

# Debounce: wait this many seconds after last change before committing
DEBOUNCE_SECONDS = 5


def git(*args):
    result = subprocess.run(
        ["git", "-C", str(WATCH_DIR), *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def has_changes():
    code, out, _ = git("status", "--porcelain")
    return code == 0 and bool(out)


def commit_and_push():
    if not has_changes():
        return

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    git("add", ".")
    code, out, err = git("commit", "-m", f"Auto-sync: {timestamp}")
    if code != 0:
        print(f"[sync] Commit failed: {err}")
        return

    print(f"[sync] Committed at {timestamp}")
    code, out, err = git("push")
    if code != 0:
        print(f"[sync] Push failed: {err}")
    else:
        print(f"[sync] Pushed to GitHub")


class ChangeHandler(FileSystemEventHandler):
    def __init__(self):
        self._last_change = 0

    def on_any_event(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        # Ignore files in excluded dirs
        if any(part in IGNORE_DIRS for part in path.parts):
            return
        # Ignore files without watched extensions
        if path.suffix not in WATCH_EXTENSIONS:
            return
        self._last_change = time.time()

    @property
    def pending(self):
        return self._last_change > 0

    def consume(self):
        elapsed = time.time() - self._last_change
        if elapsed >= DEBOUNCE_SECONDS:
            self._last_change = 0
            return True
        return False


def main():
    print(f"[sync] Watching {WATCH_DIR} for changes...")
    print(f"[sync] Will commit + push {DEBOUNCE_SECONDS}s after last change.")
    print(f"[sync] Press Ctrl+C to stop.\n")

    handler = ChangeHandler()
    observer = Observer()
    observer.schedule(handler, str(WATCH_DIR), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
            if handler.pending and handler.consume():
                commit_and_push()
    except KeyboardInterrupt:
        print("\n[sync] Stopped.")
        observer.stop()

    observer.join()


if __name__ == "__main__":
    main()
