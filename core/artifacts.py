from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from core.logger import LOG_FILE, LOG_RUNS_DIR, get_logger

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"
RUNS_DIR = REPORTS_DIR / "runs"

log = get_logger("artifacts")

_INVALID_FILENAME_CHARS = re.compile(r"[^0-9A-Za-z_.-]+")


def _safe_name(nodeid: str) -> str:
    name = nodeid.replace("::", "__").replace("/", "_").replace("\\", "_")
    name = _INVALID_FILENAME_CHARS.sub("_", name).strip("_")
    return name[:120] or "test"


def resolve_run_id() -> str:
    """CI 通过 UI_RUN_ID 注入构建号；本地默认使用时间戳。"""
    raw = os.getenv("UI_RUN_ID", "").strip()
    if raw:
        safe = _INVALID_FILENAME_CHARS.sub("_", raw).strip("_")[:80]
        if safe:
            return safe
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def get_run_dir(run_id: str) -> Path:
    return RUNS_DIR / run_id


def save_failure_artifacts(
    driver, nodeid: str, config: dict, run_id: str | None = None
) -> dict[str, str]:
    """在 WebDriver 退出前保存失败现场；截图失败不影响浏览器关闭。"""
    artifacts = config.get("artifacts", {})
    run_id = run_id or config.get("run_id") or resolve_run_id()
    base_dir = get_run_dir(run_id)
    screenshot_dir = base_dir / "screenshots"
    page_source_dir = base_dir / "page_source"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base_name = f"{stamp}_{_safe_name(nodeid)}"

    screenshot_dir.mkdir(parents=True, exist_ok=True)

    saved: dict[str, str] = {}
    try:
        screenshot_path = screenshot_dir / f"{base_name}.png"
        if driver.save_screenshot(str(screenshot_path)):
            saved["screenshot"] = str(screenshot_path)
    except Exception as exc:  # 浏览器崩溃时仍要继续 quit()
        log.warning("Failed to save screenshot: %s", exc)

    try:
        if artifacts.get("save_page_source_on_failure"):
            page_source_dir.mkdir(parents=True, exist_ok=True)
            source_path = page_source_dir / f"{base_name}.html"
            source_path.write_text(driver.page_source, encoding="utf-8")
            saved["page_source"] = str(source_path)
    except Exception as exc:
        log.warning("Failed to save page source: %s", exc)

    try:
        meta_path = base_dir / f"{base_name}.json"
        meta = {
            "run_id": run_id,
            "nodeid": nodeid,
            "saved_at": stamp,
            "current_url": getattr(driver, "current_url", ""),
            "title": getattr(driver, "title", ""),
            "environment": config.get("env"),
            "browser": config.get("browser", {}).get("resolved_name")
            or config.get("browser", {}).get("name"),
            "browser_version": driver.capabilities.get("browserVersion", "unknown"),
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        saved["meta"] = str(meta_path)
    except Exception as exc:
        log.warning("Failed to save failure metadata: %s", exc)

    if saved:
        log.error("Failure artifacts saved: %s", saved)
    return saved


def archive_run(
    run_id: str,
    config: dict | None = None,
    report_path: str | Path | None = None,
    log_path: str | Path | None = None,
) -> Path:
    """将本次运行报告和日志归档到 reports/runs/<run_id>/。"""
    target = get_run_dir(run_id)
    target.mkdir(parents=True, exist_ok=True)

    copied: dict[str, str] = {}
    if report_path:
        report = Path(report_path)
        if report.is_file() and report.stat().st_size > 0:
            destination = target / "report.html"
            shutil.copy2(report, destination)
            copied["report"] = str(destination)

    log_source = Path(log_path) if log_path else LOG_RUNS_DIR / run_id / "ui-tests.log"
    if not log_source.is_file():
        log_source = LOG_FILE
    if log_source.is_file() and log_source.stat().st_size > 0:
        destination = target / "ui-tests.log"
        shutil.copy2(log_source, destination)
        copied["log"] = str(destination)

    config = config or {}
    meta = {
        "run_id": run_id,
        "archived_at": datetime.now().strftime("%Y%m%d-%H%M%S"),
        "environment": config.get("env"),
        "base_url": config.get("base_url"),
        "browser": config.get("browser", {}).get("resolved_name")
        or config.get("browser", {}).get("name"),
        "headless": config.get("browser", {}).get("headless"),
        "artifacts": copied,
    }
    (target / "run.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (RUNS_DIR / "latest.txt").write_text(f"{run_id}\n", encoding="utf-8")
    log.info("Run archived: %s", target)
    return target
