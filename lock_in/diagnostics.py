"""
diagnostics.py
==============
A small log file, so a problem that happens quietly (an update that
didn't install, a camera that wouldn't open, a buddy link that dropped)
can be found out later instead of vanishing.

Where it lives: a "logs" folder inside Lock In's own settings folder
(next to config.json). It keeps at most 3 small files and throws the
oldest away, so it can never grow big.

Privacy, in plain words: the log is for "what went wrong", never "what
you were doing". It never writes window titles, task names, anything you
typed, or what was sent to the Claude helper. Code that wants to mention
something personal wraps it in `private(...)`, which writes
"<hidden>" -- unless you turn on the extra-detail switch yourself by
starting Lock In with LOCKIN_DEBUG_LOG=1.

Nothing here ever shows a technical error on screen.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType

LOG_FILE_NAME = "lock_in.log"
MAX_BYTES = 256 * 1024
BACKUP_COUNT = 2  # lock_in.log plus two older copies
DEBUG_SWITCH = "LOCKIN_DEBUG_LOG"
HIDDEN = "<hidden>"

_handler: logging.Handler | None = None


def debug_enabled() -> bool:
    """True only if you turned on extra detail yourself (LOCKIN_DEBUG_LOG=1)."""
    return os.environ.get(DEBUG_SWITCH, "").strip().lower() in {"1", "true", "yes", "on"}


def private(value: object) -> str:
    """Something personal (a window title, a task name). Written as
    "<hidden>" unless the extra-detail switch is on."""
    return str(value) if debug_enabled() else HIDDEN


def default_log_dir() -> Path:
    from .config import app_data_dir

    return app_data_dir() / "logs"


def setup_logging(log_dir: Path | None = None) -> Path | None:
    """Start writing the log file. Safe to call more than once (the
    second call does nothing). Returns the file's path, or None if the
    log couldn't be set up -- the app works the same either way."""
    global _handler
    root = logging.getLogger("lock_in")
    if _handler is not None:
        return Path(getattr(_handler, "baseFilename", "")) or None
    try:
        folder = log_dir or default_log_dir()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / LOG_FILE_NAME
        handler = RotatingFileHandler(
            path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8", delay=True
        )
    except OSError:
        return None
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    )
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if debug_enabled() else logging.INFO)
    _handler = handler
    _catch_unhandled_errors()
    from . import __version__

    root.info("Lock In %s started on %s", __version__, sys.platform)
    return path


def stop_logging() -> None:
    """Close the log file (for tests, and at the very end)."""
    global _handler
    if _handler is not None:
        logging.getLogger("lock_in").removeHandler(_handler)
        _handler.close()
        _handler = None


def _catch_unhandled_errors() -> None:
    """An error nothing else caught is written to the log too. (In the
    packaged app there's no console, so it would otherwise be lost.)"""
    log = logging.getLogger("lock_in")
    previous_hook = sys.excepthook

    def hook(kind: type[BaseException], error: BaseException, trace: TracebackType | None) -> None:
        if not issubclass(kind, KeyboardInterrupt):
            log.critical("Unhandled error", exc_info=(kind, error, trace))
        previous_hook(kind, error, trace)

    def thread_hook(args: threading.ExceptHookArgs) -> None:
        if args.exc_value is not None:
            log.error(
                "Unhandled error in background helper %s",
                getattr(args.thread, "name", "?"),
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            )

    sys.excepthook = hook
    threading.excepthook = thread_hook


_logged_once: set[str] = set()
_logged_once_lock = threading.Lock()


def log_once(log: logging.Logger, key: str, message: str, *args: object) -> None:
    """Log a warning (with the error's details) only the first time `key`
    comes up. For failures that would otherwise repeat every second, like
    a window watcher that keeps failing, so the log can't fill up."""
    with _logged_once_lock:
        if key in _logged_once:
            return
        _logged_once.add(key)
    log.warning(message, *args, exc_info=True)
