from __future__ import annotations

import pytest

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
