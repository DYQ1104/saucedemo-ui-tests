from __future__ import annotations

import functools
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from core.config_loader import load_locators
from core.driver_factory import create_driver
from pages.cart_page import CartPage
from pages.checkout_complete_page import CheckoutCompletePage
from pages.checkout_info_page import CheckoutInfoPage
from pages.checkout_overview_page import CheckoutOverviewPage
from pages.inventory_page import InventoryPage
from pages.login_page import LoginPage
from pages.product_detail_page import ProductDetailPage

FIXTURES_DIR = Path(__file__).parent / "fixtures"
TIMEOUT = 3


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


@pytest.fixture(scope="session")
def base_url():
    handler = functools.partial(_QuietHandler, directory=str(FIXTURES_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()


@pytest.fixture(scope="session")
def driver():
    config = {
        "browser": {
            "name": os.getenv("UI_OFFLINE_BROWSER", "auto"),
            "headless": True,
            "window_size": "1280,900",
            "page_load_strategy": "normal",
        },
        "timeouts": {"page_load": 10},
    }
    browser = create_driver(config)
    yield browser
    browser.quit()


@pytest.fixture(autouse=True)
def _blank_page(driver):
    driver.get("about:blank")
    yield


@pytest.fixture
def load_page(driver, base_url):
    def _load(name: str = "index.html"):
        driver.get(f"{base_url}/{name}")
        return driver

    return _load


@pytest.fixture
def offline_pages(driver, base_url):
    class Pages:
        def __init__(self):
            self.driver = driver
            self.login = LoginPage(driver, load_locators("login"), TIMEOUT, base_url)
            self.inventory = InventoryPage(driver, load_locators("inventory"), TIMEOUT, base_url)
            self.product_detail = ProductDetailPage(
                driver, load_locators("product_detail"), TIMEOUT, base_url
            )
            self.cart = CartPage(driver, load_locators("cart"), TIMEOUT, base_url)
            self.checkout_info = CheckoutInfoPage(
                driver, load_locators("checkout_info"), TIMEOUT, base_url
            )
            self.checkout_overview = CheckoutOverviewPage(
                driver, load_locators("checkout_overview"), TIMEOUT, base_url
            )
            self.checkout_complete = CheckoutCompletePage(
                driver, load_locators("checkout_complete"), TIMEOUT, base_url
            )

    return Pages()
