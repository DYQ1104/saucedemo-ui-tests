from __future__ import annotations

import pytest

from core.config_loader import PROJECT_ROOT, read_data

LOGIN_CASES = read_data(PROJECT_ROOT / "testdata" / "login_cases.yaml")

pytestmark = pytest.mark.regression


@pytest.mark.smoke
@pytest.mark.p0
def test_standard_user_login_success(pages, accounts):
    pages.login.open().login(accounts.standard.username, accounts.standard.password)

    pages.inventory.wait_loaded()

    assert pages.inventory.title_text() == "Products"
    assert pages.driver.current_url.endswith("/inventory.html")


@pytest.mark.smoke
@pytest.mark.p0
def test_invalid_password_shows_error(pages, accounts):
    pages.login.open().login(accounts.standard.username, "wrong_password")

    message = pages.login.error_message()

    assert "Username and password do not match" in message
    assert pages.driver.current_url.rstrip("/") == "https://www.saucedemo.com"


@pytest.mark.p1
def test_locked_out_user_shows_error(pages, accounts):
    pages.login.open().login(accounts.locked.username, accounts.locked.password)

    message = pages.login.error_message()

    assert "Sorry, this user has been locked out" in message


@pytest.mark.p1
@pytest.mark.parametrize("case", LOGIN_CASES, ids=[case["id"] for case in LOGIN_CASES])
def test_login_with_empty_field_shows_error(pages, accounts, case):
    values = {
        "username": accounts.standard.username,
        "password": accounts.standard.password,
    }
    values[case["empty_field"]] = ""

    pages.login.open().login(values["username"], values["password"])

    assert pages.login.error_message() == case["expected_error"]


@pytest.mark.p1
def test_direct_protected_page_requires_login(pages):
    pages.login.navigate("/inventory.html")

    assert (
        pages.login.error_message()
        == "Epic sadface: You can only access '/inventory.html' when you are logged in."
    )
    assert pages.login.current_url().rstrip("/") == pages.login.base_url


@pytest.mark.p1
def test_logout_then_direct_access_is_blocked(pages, accounts):
    pages.login.open().login(accounts.standard.username, accounts.standard.password)
    pages.inventory.wait_loaded()

    pages.inventory.logout()

    assert pages.login.is_visible("login_button")
    pages.login.navigate("/inventory.html")
    assert "when you are logged in" in pages.login.error_message()
