from __future__ import annotations

import pytest

BACKPACK = "Sauce Labs Backpack"

pytestmark = pytest.mark.regression


@pytest.mark.p1
def test_sort_products_by_price_and_name(pages, accounts):
    pages.login.open().login(accounts.standard.username, accounts.standard.password)
    pages.inventory.wait_loaded()

    pages.inventory.sort_by("Price (low to high)")
    prices = pages.inventory.product_prices()
    assert len(prices) == 6
    assert prices == sorted(prices)

    pages.inventory.sort_by("Name (Z to A)")
    names = pages.inventory.product_names()
    assert names == sorted(names, reverse=True)


@pytest.mark.p1
def test_sort_products_by_price_high_to_low(pages, accounts):
    pages.login.open().login(accounts.standard.username, accounts.standard.password)
    pages.inventory.wait_loaded()

    pages.inventory.sort_by("Price (high to low)")
    prices = pages.inventory.product_prices()

    assert prices == sorted(prices, reverse=True)


@pytest.mark.p2
def test_inventory_product_list_is_complete(pages, accounts):
    pages.login.open().login(accounts.standard.username, accounts.standard.password)
    pages.inventory.wait_loaded()

    names = pages.inventory.product_names()
    prices = pages.inventory.product_prices()

    assert len(names) == len(prices) == 6
    assert all(names)
    assert len(set(names)) == 6
    assert all(price > 0 for price in prices)


@pytest.mark.p1
def test_product_detail_add_to_cart_updates_badge_and_list(pages, accounts):
    pages.login.open().login(accounts.standard.username, accounts.standard.password)
    pages.inventory.wait_loaded()
    expected_price = pages.inventory.item_price(BACKPACK)

    pages.inventory.open_product(BACKPACK)
    pages.product_detail.wait_loaded()

    assert pages.product_detail.product_name() == BACKPACK
    assert pages.product_detail.item_price() == expected_price

    pages.product_detail.add_to_cart()
    assert pages.product_detail.cart_badge_count() == 1

    pages.product_detail.back_to_products()
    pages.inventory.wait_loaded()

    assert pages.inventory.cart_badge_count() == 1
    assert pages.inventory.is_visible("remove_by_name", product=BACKPACK)


@pytest.mark.p2
def test_product_detail_remove_clears_cart_state(pages, accounts):
    pages.login.open().login(accounts.standard.username, accounts.standard.password)
    pages.inventory.wait_loaded()
    pages.inventory.add_item_to_cart(BACKPACK)

    pages.inventory.open_product(BACKPACK)
    pages.product_detail.wait_loaded()
    assert pages.product_detail.cart_badge_count() == 1

    pages.product_detail.remove_from_cart()
    assert pages.product_detail.cart_badge_count() == 0
    assert pages.product_detail.is_visible("add_to_cart")

    pages.product_detail.back_to_products()
    pages.inventory.wait_loaded()

    assert pages.inventory.cart_badge_count() == 0
    assert pages.inventory.is_visible("add_to_cart_by_name", product=BACKPACK)
