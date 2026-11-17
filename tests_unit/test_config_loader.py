from __future__ import annotations

import copy

import pytest

from core.config_loader import (
    ConfigError,
    apply_cli_overrides,
    deep_merge,
    load_config,
    load_locators,
    validate_config,
    validate_locators,
)

PAGES = ("login", "inventory", "cart", "checkout_info", "checkout_overview", "checkout_complete")


@pytest.fixture(autouse=True)
def clear_ui_env(monkeypatch):
    for name in ("UI_BASE_URL", "UI_BROWSER", "UI_HEADLESS"):
        monkeypatch.delenv(name, raising=False)


def _default_config() -> dict:
    return load_config("demo")


def test_default_config_loads_demo_environment():
    config = _default_config()

    assert config["env"] == "demo"
    assert config["base_url"] == "https://www.saucedemo.com"
    assert config["browser"]["name"] == "auto"
    assert config["browser"]["headless"] is True
    assert config["timeouts"]["implicit"] == 0


def test_deep_merge_preserves_unrelated_nested_keys():
    base = {"browser": {"name": "auto", "headless": True}, "timeouts": {"explicit": 10}}

    merged = deep_merge(base, {"browser": {"name": "edge"}})

    assert merged == {
        "browser": {"name": "edge", "headless": True},
        "timeouts": {"explicit": 10},
    }
    assert base["browser"]["name"] == "auto"


def test_environment_variables_override_files(monkeypatch):
    monkeypatch.setenv("UI_BASE_URL", "https://example.com/")
    monkeypatch.setenv("UI_BROWSER", "firefox")
    monkeypatch.setenv("UI_HEADLESS", "false")

    config = _default_config()

    assert config["base_url"] == "https://example.com"
    assert config["browser"]["name"] == "firefox"
    assert config["browser"]["headless"] is False
    assert config["timeouts"]["explicit"] == 10


def test_blank_environment_variables_are_ignored(monkeypatch):
    monkeypatch.setenv("UI_BASE_URL", "   ")
    monkeypatch.setenv("UI_BROWSER", "")
    monkeypatch.setenv("UI_HEADLESS", " ")

    config = _default_config()

    assert config["base_url"] == "https://www.saucedemo.com"
    assert config["browser"]["name"] == "auto"
    assert config["browser"]["headless"] is True


def test_cli_overrides_win_over_environment(monkeypatch):
    monkeypatch.setenv("UI_BROWSER", "firefox")
    config = _default_config()

    overridden = apply_cli_overrides(config, browser="edge", headed=True)

    assert config["browser"]["name"] == "firefox"
    assert config["browser"]["headless"] is True
    assert overridden["browser"]["name"] == "edge"
    assert overridden["browser"]["headless"] is False


def test_cli_browser_rejects_unsupported_value():
    with pytest.raises(ConfigError, match="Unsupported browser"):
        apply_cli_overrides(_default_config(), browser="opera")


def test_missing_environment_reports_the_missing_file():
    with pytest.raises(ConfigError, match="missing.yaml"):
        load_config("missing")


@pytest.mark.parametrize(
    ("case_id", "mutate", "match"),
    [
        ("implicit-wait", lambda c: c["timeouts"].__setitem__("implicit", 1), "implicit must be 0"),
        ("window-size", lambda c: c["browser"].__setitem__("window_size", "1440x1000"), "window_size"),
        ("base-url", lambda c: c.__setitem__("base_url", "ftp://example.com"), "http\\(s\\) URL"),
        ("browser-name", lambda c: c["browser"].__setitem__("name", "opera"), "Unsupported browser"),
        ("headless-type", lambda c: c["browser"].__setitem__("headless", "true"), "must be a boolean"),
        ("explicit-timeout", lambda c: c["timeouts"].__setitem__("explicit", 0), "positive number"),
        (
            "page-load-strategy",
            lambda c: c["browser"].__setitem__("page_load_strategy", "fast"),
            "page_load_strategy",
        ),
        ("timeouts-mapping", lambda c: c.__setitem__("timeouts", []), "must be a mapping"),
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_invalid_config_is_rejected(case_id, mutate, match):
    config = copy.deepcopy(_default_config())
    mutate(config)

    with pytest.raises(ConfigError, match=match):
        validate_config(config, "demo")


@pytest.mark.parametrize("page", PAGES)
def test_locator_files_are_valid(page):
    load_locators.cache_clear()

    locators = load_locators(page)

    assert locators
    assert all({"by", "value"} <= set(entry) for entry in locators.values())


@pytest.mark.parametrize(
    ("data", "match"),
    [
        (None, "empty or not a mapping"),
        ({}, "empty or not a mapping"),
        ({"item": "id"}, "must contain"),
        ({"item": {"by": "id"}}, "must contain"),
        ({"item": {"by": "magic", "value": "x"}}, "unsupported strategy"),
        ({"item": {"by": "id", "value": "   "}}, "empty value"),
    ],
)
def test_invalid_locator_structure_is_rejected(data, match):
    with pytest.raises(ConfigError, match=match):
        validate_locators(data, "test-locators")


def test_minimal_locator_structure_is_accepted():
    validate_locators({"item": {"by": "css selector", "value": "[data-test='item']"}})
