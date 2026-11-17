from __future__ import annotations

import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "ui-tests.log"
LOG_RUNS_DIR = LOG_DIR / "runs"


def configure_logging(level: str = "INFO", run_id: str | None = None) -> None:
    root = logging.getLogger()
    if getattr(root, "_ui_configured", False):
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    targets = [LOG_FILE]
    if run_id:
        run_log = LOG_RUNS_DIR / run_id / "ui-tests.log"
        run_log.parent.mkdir(parents=True, exist_ok=True)
        targets.append(run_log)

    formatter = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s | %(message)s")
    for target in targets:
        handler = logging.FileHandler(target, encoding="utf-8")
        handler.setFormatter(formatter)
        root.addHandler(handler)
    root._ui_configured = True


def get_logger(name: str = "ui") -> logging.Logger:
    return logging.getLogger(name)
