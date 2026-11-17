from __future__ import annotations

import base64
from pathlib import Path
from types import SimpleNamespace

import pytest
from pytest_html import extras

from core.artifacts import archive_run, resolve_run_id, save_failure_artifacts
from core.config_loader import (
    SUPPORTED_BROWSERS,
    apply_cli_overrides,
    load_config,
    load_locators,
)
from core.credentials import get_account
from core.driver_factory import create_driver
from core.logger import LOG_FILE, LOG_RUNS_DIR, configure_logging, get_logger
from pages.cart_page import CartPage
from pages.checkout_complete_page import CheckoutCompletePage
from pages.checkout_info_page import CheckoutInfoPage
from pages.checkout_overview_page import CheckoutOverviewPage
from pages.inventory_page import InventoryPage
from pages.login_page import LoginPage
from pages.product_detail_page import ProductDetailPage

log = get_logger("conftest")
RUN_ID = resolve_run_id()


def pytest_addoption(parser):
    group = parser.getgroup("ui-automation", "UI automation run options")
    group.addoption(
        "--env", action="store", default="demo", help="Environment name: config/env/<env>.yaml"
    )
    group.addoption(
        "--browser",
        action="store",
        choices=list(SUPPORTED_BROWSERS),
        default=None,
        help="Override browser.name from config.yaml",
    )
    group.addoption(
        "--headed", action="store_true", default=False, help="Run in headed mode for local debugging"
    )


@pytest.fixture(scope="session")
def app_config(request):
    config = apply_cli_overrides(
        load_config(request.config.getoption("--env")),
        browser=request.config.getoption("--browser"),
        headed=request.config.getoption("--headed"),
    )
    config["run_id"] = RUN_ID
    request.config._ui_app_config = config

    configure_logging(config.get("logging", {}).get("level", "INFO"), run_id=RUN_ID)
    log.info(
        "Run config: env=%s base_url=%s browser=%s headless=%s",
        config["env"],
        config["base_url"],
        config["browser"]["name"],
        config["browser"]["headless"],
    )
    return config


@pytest.fixture
def driver(app_config):
    browser = create_driver(app_config)
    yield browser
    try:
        browser.quit()
    except Exception as exc:
        log.warning("Failed to quit browser: %s", exc)


@pytest.fixture
def pages(driver, app_config):
    timeout = app_config["timeouts"]["explicit"]
    base_url = app_config["base_url"]

    class Pages:
        def __init__(self):
            self.driver = driver
            self.login = LoginPage(driver, load_locators("login"), timeout, base_url)
            self.inventory = InventoryPage(driver, load_locators("inventory"), timeout, base_url)
            self.product_detail = ProductDetailPage(
                driver, load_locators("product_detail"), timeout, base_url
            )
            self.cart = CartPage(driver, load_locators("cart"), timeout, base_url)
            self.checkout_info = CheckoutInfoPage(
                driver, load_locators("checkout_info"), timeout, base_url
            )
            self.checkout_overview = CheckoutOverviewPage(
                driver, load_locators("checkout_overview"), timeout, base_url
            )
            self.checkout_complete = CheckoutCompletePage(
                driver, load_locators("checkout_complete"), timeout, base_url
            )

    return Pages()


@pytest.fixture(scope="session")
def accounts():
    return SimpleNamespace(standard=get_account("standard"), locked=get_account("locked"))


def _read_log_tail(limit: int = 80) -> str:
    for path in (LOG_RUNS_DIR / RUN_ID / "ui-tests.log", LOG_FILE):
        if path.is_file() and path.stat().st_size > 0:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            return "\n".join(lines[-limit:])
    return ""


def _failure_extras(browser, nodeid: str, config: dict) -> list[dict]:
    saved = save_failure_artifacts(browser, nodeid, config, run_id=RUN_ID)
    attached: list[dict] = []
    screenshot = saved.get("screenshot")
    if screenshot and Path(screenshot).is_file():
        encoded = base64.b64encode(Path(screenshot).read_bytes()).decode("ascii")
        attached.append(extras.image(encoded, name="失败截图 (PNG)"))
    meta = saved.get("meta")
    if meta and Path(meta).is_file():
        attached.append(
            extras.text(Path(meta).read_text(encoding="utf-8"), name="失败现场信息 (JSON)")
        )
    log_tail = _read_log_tail()
    if log_tail:
        attached.append(extras.text(log_tail, name="运行日志尾部 (80 行)"))
    return attached


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)
    if report.when != "call" or not report.failed:
        return
    config = getattr(item.config, "_ui_app_config", None)
    browser = item.funcargs.get("driver")
    if not config or browser is None:
        return
    if not config.get("artifacts", {}).get("screenshot_on_failure"):
        return
    try:
        report.extras = getattr(report, "extras", []) + _failure_extras(
            browser, item.nodeid, config
        )
    except Exception as exc:
        log.warning("Failed to attach failure evidence to report: %s", exc)


def pytest_unconfigure(config):
    if getattr(config.option, "collectonly", False):
        return
    app_config = getattr(config, "_ui_app_config", None)
    if not app_config:
        return
    report_path = getattr(config.option, "htmlpath", None)
    target = archive_run(
        RUN_ID,
        app_config,
        report_path=Path(report_path).resolve() if report_path else None,
    )
    print(f"\nArtifacts archived: {target}")
