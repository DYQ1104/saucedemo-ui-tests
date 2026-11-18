from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By

from core.base_page import BasePage

pytestmark = pytest.mark.offline

BACKPACK = "Sauce Labs Backpack"

LOCATORS = {
    "title": {"by": "css selector", "value": "[data-test='title']"},
    "menu": {"by": "id", "value": "react-burger-menu-btn"},
    "menu_class": {"by": "class name", "value": "menu-button"},
    "sort": {"by": "name", "value": "sort"},
    "sort_xpath": {"by": "xpath", "value": "//select[@data-test='product-sort-container']"},
    "select_tag": {"by": "tag name", "value": "select"},
    "cart_link": {"by": "link text", "value": "Cart"},
    "cart_partial": {"by": "partial link text", "value": "Car"},
    "note": {"by": "css selector", "value": "[data-test='note']"},
    "price_by_name": {
        "by": "xpath",
        "value": (
            "//div[@data-test='inventory-item']"
            "[.//div[@data-test='inventory-item-name' and normalize-space()='{product}']]"
            "//div[@data-test='inventory-item-price']"
        ),
    },
    "missing_element": {"by": "css selector", "value": ".does-not-exist"},
    "unsupported": {"by": "magic", "value": "whatever"},
}


def make_page(driver, base_url, locators=None) -> BasePage:
    return BasePage(driver, locators or LOCATORS, 2, base_url)


def test_locator_supports_all_configured_strategies(driver, base_url, load_page):
    load_page("inventory.html")
    page = make_page(driver, base_url)

    assert page.text("title") == "Products"
    assert page.wait_present("menu").get_attribute("id") == "react-burger-menu-btn"
    assert page.wait_present("menu_class").tag_name == "button"
    assert page.wait_present("sort").tag_name == "select"
    assert page.wait_present("sort_xpath").tag_name == "select"
    assert page.wait_present("select_tag").tag_name == "select"
    assert page.wait_present("cart_link").text == "Cart"
    assert page.wait_present("cart_partial").text == "Cart"


def test_dynamic_locator_formats_product_placeholder(driver, base_url, load_page):
    load_page("inventory.html")
    page = make_page(driver, base_url)

    by, value = page.locator("price_by_name", product=BACKPACK)

    assert by == By.XPATH
    assert BACKPACK in value
    assert page.text("price_by_name", product=BACKPACK) == "$29.99"


def test_locator_rejects_unknown_unsupported_and_bad_placeholder(driver, base_url, load_page):
    load_page("inventory.html")
    page = make_page(driver, base_url)

    with pytest.raises(KeyError, match="no locator named"):
        page.locator("not_defined")
    with pytest.raises(ValueError, match="unsupported strategy"):
        page.locator("unsupported")
    with pytest.raises(ValueError, match="missing placeholder"):
        page.locator("price_by_name", product_name=BACKPACK)


def test_navigation_and_url_wait(driver, base_url):
    page = make_page(driver, base_url)
    result = page.navigate("/inventory.html")

    assert result is page
    assert page.wait_url_contains("/inventory.html") is True
    assert page.current_url().endswith("/inventory.html")
    assert page.wait_visible("title").text == "Products"


def test_input_click_text_and_waits(driver, base_url, load_page):
    load_page("index.html")
    page = make_page(
        driver,
        base_url,
        {
            "username": {"by": "css selector", "value": "[data-test='username']"},
            "password": {"by": "css selector", "value": "[data-test='password']"},
            "login_button": {"by": "css selector", "value": "[data-test='login-button']"},
            "error_message": {"by": "css selector", "value": "[data-test='error']"},
        },
    )

    page.input_text("username", "standard_user")
    page.input_text("password", "secret_sauce")
    page.click("login_button")

    assert page.wait_url_contains("/inventory.html") is True


def test_texts_skips_hidden_elements_and_wait_absent(driver, base_url, load_page):
    load_page("inventory.html")
    page = make_page(driver, base_url)

    assert page.texts("note") == ["visible note"]
    assert page.exists("missing_element") is False
    assert page.is_visible("missing_element", timeout=0.3) is False


def test_wait_text_contains_and_absent_after_removal(driver, base_url, load_page):
    load_page("inventory.html")
    page = make_page(driver, base_url)
    assert page.wait_text_contains("title", "Prod") == "Products"

    load_page("cart.html")
    page = make_page(
        driver,
        base_url,
        {
            "row": {
                "by": "xpath",
                "value": (
                    "//div[@data-test='inventory-item'][.//div[@data-test='inventory-item-name' "
                    "and normalize-space()='{product}']]"
                ),
            },
            "remove": {
                "by": "xpath",
                "value": (
                    "//div[@data-test='inventory-item'][.//div[@data-test='inventory-item-name' "
                    "and normalize-space()='{product}']]//button"
                ),
            },
        },
    )
    page.click("remove", product=BACKPACK)
    assert page.wait_absent("row", product=BACKPACK) is True
    assert page.exists("row", product=BACKPACK) is False
