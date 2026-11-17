from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from core.artifacts import archive_run, resolve_run_id, save_failure_artifacts
from core.config_loader import (
    SUPPORTED_BROWSERS,
    apply_cli_overrides,
    load_config,
    load_locators,
)
from core.credentials import get_account
from core.driver_factory import create_driver
from core.logger import configure_logging, get_logger
from pages.cart_page import CartPage
from pages.checkout_complete_page import CheckoutCompletePage
from pages.checkout_info_page import CheckoutInfoPage
from pages.checkout_overview_page import CheckoutOverviewPage
from pages.inventory_page import InventoryPage
from pages.login_page import LoginPage

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
def driver(app_config, request):
    browser = create_driver(app_config)
    yield browser

    failed = getattr(getattr(request.node, "rep_call", None), "failed", False)
    try:
        if failed and app_config["artifacts"].get("screenshot_on_failure"):
            save_failure_artifacts(browser, request.node.nodeid, app_config)
    finally:
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


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


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
