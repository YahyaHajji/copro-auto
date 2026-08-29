from __future__ import annotations

import atexit
import logging
import os
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path
from queue import SimpleQueue

from platformdirs import user_log_path


_listener: QueueListener | None = None


def configure_logging(level: int = logging.INFO) -> Path:
    global _listener
    configured_log_dir = os.environ.get("COPRO_AUTO_LOG_DIR", "").strip()
    log_dir = (
        Path(configured_log_dir).resolve()
        if configured_log_dir
        else Path(user_log_path("CoproAuto", ensure_exists=True))
    )
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"
    handler = RotatingFileHandler(log_file, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    queue: SimpleQueue = SimpleQueue()
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(QueueHandler(queue))
    _listener = QueueListener(queue, handler, respect_handler_level=True)
    _listener.start()
    atexit.register(shutdown_logging)
    return log_file


def shutdown_logging() -> None:
    global _listener
    if _listener is not None:
        _listener.stop()
        _listener = None
