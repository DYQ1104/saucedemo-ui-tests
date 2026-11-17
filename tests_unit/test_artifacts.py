from __future__ import annotations

import json
from pathlib import Path

import core.artifacts as artifacts


def test_run_id_uses_sanitized_environment_value(monkeypatch):
    monkeypatch.setenv("UI_RUN_ID", "12345/attempt 1")

    assert artifacts.resolve_run_id() == "12345_attempt_1"


def test_run_id_falls_back_to_timestamp(monkeypatch):
    monkeypatch.delenv("UI_RUN_ID", raising=False)

    run_id = artifacts.resolve_run_id()

    assert len(run_id) == 15
    assert run_id[8] == "-"


def test_archive_run_copies_report_log_and_metadata(tmp_path, monkeypatch):
    runs_dir = tmp_path / "runs"
    monkeypatch.setattr(artifacts, "RUNS_DIR", runs_dir)
    report = tmp_path / "report.html"
    report.write_text("<html>report</html>", encoding="utf-8")
    log = tmp_path / "ui-tests.log"
    log.write_text("log line\n", encoding="utf-8")

    target = artifacts.archive_run(
        "build-42",
        {"env": "demo", "base_url": "https://www.saucedemo.com", "browser": {"name": "edge", "headless": True}},
        report_path=report,
        log_path=log,
    )

    assert target == runs_dir / "build-42"
    assert (target / "report.html").read_text(encoding="utf-8") == "<html>report</html>"
    assert (target / "ui-tests.log").read_text(encoding="utf-8") == "log line\n"
    meta = json.loads((target / "run.json").read_text(encoding="utf-8"))
    assert meta["run_id"] == "build-42"
    assert meta["environment"] == "demo"
    assert meta["browser"] == "edge"
    assert (runs_dir / "latest.txt").read_text(encoding="utf-8") == "build-42\n"


def test_archive_run_skips_missing_report(tmp_path, monkeypatch):
    monkeypatch.setattr(artifacts, "RUNS_DIR", tmp_path / "runs")
    log = tmp_path / "ui-tests.log"
    log.write_text("log line\n", encoding="utf-8")

    target = artifacts.archive_run(
        "build-43", {"env": "demo"}, report_path=tmp_path / "missing.html", log_path=log
    )

    assert not (target / "report.html").exists()
    assert Path(target / "run.json").is_file()
