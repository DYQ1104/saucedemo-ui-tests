from __future__ import annotations

import pytest

pytestmark = pytest.mark.offline

BACKPACK = "Sauce Labs Backpack"
BIKE_LIGHT = "Sauce Labs Bike Light"
BOLT_SHIRT = "Sauce Labs Bolt T-Shirt"


def test_login_page_success_navigates_to_inventory(offline_pages, driver):
    offline_pages.login.open().login("standard_user", "secret_sauce")

    assert driver.current_url.endswith("/inventory.html")


def test_login_page_error_and_dismiss(offline_pages):
    page = offline_pages.login.open().login("standard_user", "wrong_password")

    assert "do not match" in page.error_message()
    page.dismiss_error()
    assert page.is_visible("error_message", timeout=0.5) is False


def test_inventory_page_reads_products(offline_pages):
    page = offline_pages.inventory
    page.navigate("/inventory.html")
    page.wait_loaded()

    assert page.title_text() == "Products"
    assert page.product_names() == [BACKPACK, BIKE_LIGHT, BOLT_SHIRT]
    assert page.product_prices() == [29.99, 9.99, 15.99]
    assert page.item_price(BACKPACK) == "$29.99"
    assert page.cart_badge_count() == 0


def test_inventory_page_add_and_remove_item(offline_pages):
    page = offline_pages.inventory
    page.navigate("/inventory.html")
    page.wait_loaded()

    page.add_item_to_cart(BACKPACK)
    assert page.cart_badge_count() == 1
    assert page.is_visible("remove_by_name", product=BACKPACK)

    page.remove_item(BACKPACK)
    assert page.cart_badge_count() == 0
    assert page.is_visible("add_to_cart_by_name", product=BACKPACK)


def test_inventory_page_sorting_and_detail_navigation(offline_pages, driver):
    page = offline_pages.inventory
    page.navigate("/inventory.html")
    page.wait_loaded()

    page.sort_by("Price (low to high)")
    assert page.product_prices() == sorted(page.product_prices())

    page.sort_by("Name (Z to A)")
    assert page.product_names() == sorted(page.product_names(), reverse=True)

    page.open_product(BACKPACK)
    assert driver.current_url.endswith("/inventory-item.html")


def test_inventory_page_logout_returns_to_login(offline_pages, base_url):
    page = offline_pages.inventory
    page.navigate("/inventory.html")
    page.wait_loaded()

    page.logout()

    assert page.current_url().rstrip("/") == base_url


def test_product_detail_add_and_remove(offline_pages, driver):
    page = offline_pages.product_detail
    page.navigate("/inventory-item.html")
    page.wait_loaded()

    assert page.product_name() == BACKPACK
    assert page.item_price() == "$29.99"
    assert page.cart_badge_count() == 0

    page.add_to_cart()
    assert page.cart_badge_count() == 1
    assert page.is_visible("remove")

    page.remove_from_cart()
    assert page.cart_badge_count() == 0
    assert page.is_visible("add_to_cart")

    page.back_to_products()
    assert driver.current_url.endswith("/inventory.html")


def test_cart_page_reads_and_removes_items(offline_pages):
    page = offline_pages.cart
    page.navigate("/cart.html")
    page.wait_loaded()

    assert page.title_text() == "Your Cart"
    assert page.product_names() == [BACKPACK, BIKE_LIGHT]
    assert page.item_quantity(BACKPACK) == "1"
    assert page.item_price(BACKPACK) == "$29.99"
    assert page.cart_badge_count() == 2

    page.remove_item(BACKPACK)
    assert page.product_names() == [BIKE_LIGHT]
    assert page.cart_badge_count() == 1

    page.remove_item(BIKE_LIGHT)
    page.wait_empty()
    assert page.cart_badge_count() == 0
    assert page.exists("cart_item") is False


def test_cart_page_continue_and_checkout_navigation(offline_pages, driver):
    page = offline_pages.cart
    page.navigate("/cart.html")
    page.wait_loaded()
    page.continue_shopping()
    assert driver.current_url.endswith("/inventory.html")

    page.navigate("/cart.html")
    page.wait_loaded()
    page.open_checkout()
    assert driver.current_url.endswith("/checkout-step-one.html")


def test_cart_page_refresh_keeps_items(offline_pages):
    page = offline_pages.cart
    page.navigate("/cart.html")
    page.wait_loaded()

    page.refresh()

    assert page.product_names() == [BACKPACK, BIKE_LIGHT]
    assert page.cart_badge_count() == 2


def test_checkout_info_validation_and_valid_submit(offline_pages, driver):
    page = offline_pages.checkout_info
    page.navigate("/checkout-step-one.html")
    page.wait_loaded()

    page.submit_customer("", "Doe", "100000")
    assert page.error_message() == "Error: First Name is required"
    assert driver.current_url.endswith("/checkout-step-one.html")

    page.dismiss_error()
    assert page.is_visible("error_message", timeout=0.5) is False

    page.submit_customer("John", "Doe", "100000")
    assert driver.current_url.endswith("/checkout-step-two.html")


def test_checkout_info_cancel_returns_to_cart(offline_pages, driver):
    page = offline_pages.checkout_info
    page.navigate("/checkout-step-one.html")
    page.wait_loaded()

    page.cancel()

    assert driver.current_url.endswith("/cart.html")


def test_checkout_overview_reads_totals_and_finishes(offline_pages, driver):
    page = offline_pages.checkout_overview
    page.navigate("/checkout-step-two.html")
    page.wait_loaded()

    assert page.product_names() == [BACKPACK, BIKE_LIGHT]
    assert page.subtotal_text() == "Item total: $39.98"
    assert page.tax_text() == "Tax: $3.20"
    assert page.total_text() == "Total: $43.18"
    assert page.payment_info() == "SauceCard #31337"
    assert page.shipping_info() == "Free Pony Express Delivery!"

    page.finish()
    assert driver.current_url.endswith("/checkout-complete.html")


def test_checkout_overview_cancel_returns_to_inventory(offline_pages, driver):
    page = offline_pages.checkout_overview
    page.navigate("/checkout-step-two.html")
    page.wait_loaded()

    page.cancel()

    assert driver.current_url.endswith("/inventory.html")


def test_checkout_complete_reads_message_and_back_home(offline_pages, driver):
    page = offline_pages.checkout_complete
    page.navigate("/checkout-complete.html")
    page.wait_loaded()

    assert page.header_text() == "Thank you for your order!"
    assert page.message_text() == "Your order has been dispatched."

    page.back_home()
    assert driver.current_url.endswith("/inventory.html")
