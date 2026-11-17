from __future__ import annotations

import re

import pytest

from core.config_loader import PROJECT_ROOT, read_data

BACKPACK = "Sauce Labs Backpack"
BIKE_LIGHT = "Sauce Labs Bike Light"
CHECKOUT_CASES = read_data(PROJECT_ROOT / "testdata" / "checkout_cases.yaml")

pytestmark = pytest.mark.regression


def _amount(text: str) -> float:
    match = re.search(r"\$([\d,]+\.\d{2})", text)
    assert match, f"Amount not found in text: {text}"
    return float(match.group(1).replace(",", ""))


def _login_add_items_and_open_checkout(pages, accounts, items: list[str]) -> list[str]:
    pages.login.open().login(accounts.standard.username, accounts.standard.password)
    pages.inventory.wait_loaded()
    price_texts = [pages.inventory.item_price(item) for item in items]

    for item in items:
        pages.inventory.add_item_to_cart(item)
    pages.inventory.open_cart()
    pages.cart.wait_loaded()
    pages.cart.open_checkout()
    pages.checkout_info.wait_loaded()
    return price_texts


@pytest.mark.smoke
@pytest.mark.p0
def test_complete_single_item_checkout(pages, accounts):
    unit_price = _login_add_items_and_open_checkout(pages, accounts, [BACKPACK])[0]

    pages.checkout_info.submit_customer("John", "Doe", "100000")
    pages.checkout_overview.wait_loaded()

    assert pages.checkout_overview.product_names() == [BACKPACK]
    assert pages.checkout_overview.subtotal_text().endswith(unit_price)
    assert re.fullmatch(r"Total: \$\d+\.\d{2}", pages.checkout_overview.total_text())
    assert pages.checkout_overview.payment_info()
    assert pages.checkout_overview.shipping_info()

    pages.checkout_overview.finish()
    pages.checkout_complete.wait_loaded()

    assert pages.checkout_complete.header_text() == "Thank you for your order!"
    assert pages.checkout_complete.message_text()
    assert pages.driver.current_url.endswith("/checkout-complete.html")


@pytest.mark.p1
@pytest.mark.parametrize("case", CHECKOUT_CASES, ids=[case["id"] for case in CHECKOUT_CASES])
def test_checkout_required_field_validation(pages, accounts, case):
    _login_add_items_and_open_checkout(pages, accounts, [BACKPACK])

    pages.checkout_info.submit_customer(
        case["first_name"], case["last_name"], case["postal_code"]
    )

    assert pages.checkout_info.error_message() == case["expected_error"]
    assert pages.driver.current_url.endswith("/checkout-step-one.html")


@pytest.mark.p1
def test_multi_item_checkout_totals_are_correct(pages, accounts):
    items = [BACKPACK, BIKE_LIGHT]
    price_texts = _login_add_items_and_open_checkout(pages, accounts, items)

    pages.checkout_info.submit_customer("John", "Doe", "100000")
    pages.checkout_overview.wait_loaded()

    assert pages.checkout_overview.product_names() == items
    subtotal = _amount(pages.checkout_overview.subtotal_text())
    tax = _amount(pages.checkout_overview.tax_text())
    total = _amount(pages.checkout_overview.total_text())

    assert round(subtotal, 2) == round(sum(_amount(price) for price in price_texts), 2)
    assert abs(total - (subtotal + tax)) <= 0.01

    pages.checkout_overview.finish()
    pages.checkout_complete.wait_loaded()
    assert pages.checkout_complete.header_text() == "Thank you for your order!"


@pytest.mark.p1
def test_cancel_checkout_returns_to_cart_with_items(pages, accounts):
    _login_add_items_and_open_checkout(pages, accounts, [BACKPACK])

    pages.checkout_info.cancel()
    pages.cart.wait_loaded()

    assert pages.cart.product_names() == [BACKPACK]
    assert pages.cart.cart_badge_count() == 1


@pytest.mark.p2
def test_back_home_after_order_clears_cart(pages, accounts):
    _login_add_items_and_open_checkout(pages, accounts, [BACKPACK])
    pages.checkout_info.submit_customer("John", "Doe", "100000")
    pages.checkout_overview.wait_loaded()
    pages.checkout_overview.finish()
    pages.checkout_complete.wait_loaded()

    pages.checkout_complete.back_home()
    pages.inventory.wait_loaded()

    assert pages.inventory.cart_badge_count() == 0
    pages.inventory.open_cart()
    pages.cart.wait_loaded()
    pages.cart.wait_empty()
    assert not pages.cart.exists("cart_item")
