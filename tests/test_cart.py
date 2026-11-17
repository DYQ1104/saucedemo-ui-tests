from __future__ import annotations

import pytest

BACKPACK = "Sauce Labs Backpack"
BIKE_LIGHT = "Sauce Labs Bike Light"
BOLT_SHIRT = "Sauce Labs Bolt T-Shirt"

pytestmark = pytest.mark.regression


def _login_and_open_inventory(pages, accounts):
    pages.login.open().login(accounts.standard.username, accounts.standard.password)
    pages.inventory.wait_loaded()


@pytest.mark.smoke
@pytest.mark.p0
def test_add_single_item_to_cart(pages, accounts):
    _login_and_open_inventory(pages, accounts)
    expected_price = pages.inventory.item_price(BACKPACK)

    pages.inventory.add_item_to_cart(BACKPACK)

    assert pages.inventory.cart_badge_count() == 1

    pages.inventory.open_cart()
    pages.cart.wait_loaded()
    assert pages.cart.product_names() == [BACKPACK]
    assert pages.cart.item_quantity(BACKPACK) == "1"
    assert pages.cart.item_price(BACKPACK) == expected_price


@pytest.mark.p1
def test_remove_item_from_cart(pages, accounts):
    _login_and_open_inventory(pages, accounts)
    pages.inventory.add_item_to_cart(BACKPACK)
    pages.inventory.add_item_to_cart(BIKE_LIGHT)
    assert pages.inventory.cart_badge_count() == 2

    pages.inventory.open_cart()
    pages.cart.wait_loaded()
    pages.cart.remove_item(BACKPACK)

    assert pages.cart.product_names() == [BIKE_LIGHT]
    assert pages.cart.cart_badge_count() == 1
    assert pages.cart.is_visible("cart_badge") is True


@pytest.mark.p1
def test_add_multiple_items_updates_badge_and_quantities(pages, accounts):
    _login_and_open_inventory(pages, accounts)
    items = [BACKPACK, BIKE_LIGHT, BOLT_SHIRT]

    for item in items:
        pages.inventory.add_item_to_cart(item)

    assert pages.inventory.cart_badge_count() == 3

    pages.inventory.open_cart()
    pages.cart.wait_loaded()
    assert pages.cart.product_names() == items
    for item in items:
        assert pages.cart.item_quantity(item) == "1"


@pytest.mark.p2
def test_remove_all_items_empties_cart(pages, accounts):
    _login_and_open_inventory(pages, accounts)
    pages.inventory.add_item_to_cart(BACKPACK)
    pages.inventory.add_item_to_cart(BIKE_LIGHT)

    pages.inventory.open_cart()
    pages.cart.wait_loaded()
    pages.cart.remove_item(BACKPACK)
    pages.cart.remove_item(BIKE_LIGHT)
    pages.cart.wait_empty()

    assert not pages.cart.exists("cart_item")
    assert pages.cart.cart_badge_count() == 0
    assert not pages.cart.exists("cart_badge")


@pytest.mark.p2
def test_continue_shopping_keeps_cart_items(pages, accounts):
    _login_and_open_inventory(pages, accounts)
    pages.inventory.add_item_to_cart(BACKPACK)
    pages.inventory.add_item_to_cart(BIKE_LIGHT)

    pages.inventory.open_cart()
    pages.cart.wait_loaded()
    pages.cart.continue_shopping()

    pages.inventory.wait_loaded()
    assert pages.inventory.cart_badge_count() == 2
