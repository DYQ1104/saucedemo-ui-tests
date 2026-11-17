from __future__ import annotations

import os
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"

SUPPORTED_BROWSERS = ("auto", "chrome", "edge", "firefox")
SUPPORTED_BY = {
    "id",
    "name",
    "class name",
    "css selector",
    "xpath",
    "link text",
    "partial link text",
    "tag name",
}

# 优先级：命令行 > 环境变量 > 默认配置；环境变量在此应用，命令行在 conftest 中应用。
ENV_OVERRIDES: dict[str, tuple[str, ...]] = {
    "UI_BASE_URL": ("base_url",),
    "UI_BROWSER": ("browser", "name"),
    "UI_HEADLESS": ("browser", "headless"),
}


class ConfigError(ValueError):
    pass


def read_data(path: str | Path):
    file_path = Path(path)
    if not file_path.is_file():
        raise ConfigError(f"Data file not found: {file_path}")
    with file_path.open(encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if data is None:
        raise ConfigError(f"Data file is empty: {file_path}")
    return data


def read_yaml(path: str | Path) -> dict[str, Any]:
    data = read_data(path)
    if not isinstance(data, dict):
        raise ConfigError(f"Config file root must be a mapping: {path}")
    return data


def deep_merge(base: dict, override: dict) -> dict:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _set_nested(config: dict, path: tuple[str, ...], value: Any) -> None:
    target = config
    for key in path[:-1]:
        node = target.get(key)
        if not isinstance(node, dict):
            node = {}
            target[key] = node
        target = node
    target[path[-1]] = value


def _coerce_env_value(raw: str) -> str | bool:
    lowered = raw.strip().lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    return raw.strip()


def load_config(env: str) -> dict[str, Any]:
    config = read_yaml(CONFIG_DIR / "config.yaml")
    config = deep_merge(config, read_yaml(CONFIG_DIR / "env" / f"{env}.yaml"))

    for variable, path in ENV_OVERRIDES.items():
        raw = os.getenv(variable)
        if raw is not None and raw.strip() != "":
            _set_nested(config, path, _coerce_env_value(raw))

    config["base_url"] = str(config.get("base_url", "")).rstrip("/")
    validate_config(config, env)
    config["env"] = env
    return config


def apply_cli_overrides(
    config: dict[str, Any], browser: str | None = None, headed: bool = False
) -> dict[str, Any]:
    """命令行优先级最高，叠加在环境变量与 YAML 合并结果之上。"""
    result = deepcopy(config)
    browser_config = result.setdefault("browser", {})

    if browser:
        name = browser.strip().lower()
        if name not in SUPPORTED_BROWSERS:
            raise ConfigError(
                f"Unsupported browser {name!r}; available: {', '.join(SUPPORTED_BROWSERS)}"
            )
        browser_config["name"] = name
    if headed:
        browser_config["headless"] = False
    return result


def _require_mapping(config: dict, key: str) -> dict:
    value = config.get(key)
    if not isinstance(value, dict):
        raise ConfigError(f"Config item '{key}' must be a mapping")
    return value


def _require_positive_number(value: Any, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ConfigError(f"Config item '{name}' must be a positive number, got: {value!r}")


def validate_config(config: dict, env: str) -> None:
    base_url = config.get("base_url")
    if not isinstance(base_url, str) or not base_url.startswith(("http://", "https://")):
        raise ConfigError(
            f"base_url for env '{env}' must be an http(s) URL, got: {base_url!r}"
        )

    browser = _require_mapping(config, "browser")
    name = str(browser.get("name", "")).lower()
    if name not in SUPPORTED_BROWSERS:
        raise ConfigError(
            f"Unsupported browser {name!r}; available: {', '.join(SUPPORTED_BROWSERS)}"
        )
    if not isinstance(browser.get("headless"), bool):
        raise ConfigError("browser.headless must be a boolean")
    window_size = browser.get("window_size")
    if not isinstance(window_size, str) or not _is_window_size(window_size):
        raise ConfigError(
            f"browser.window_size must use '<width>,<height>' format, got: {window_size!r}"
        )
    if browser.get("page_load_strategy", "normal") not in {"normal", "eager", "none"}:
        raise ConfigError("browser.page_load_strategy must be normal/eager/none")

    timeouts = _require_mapping(config, "timeouts")
    if timeouts.get("implicit") != 0:
        raise ConfigError("timeouts.implicit must be 0: this project uses explicit waits only")
    _require_positive_number(timeouts.get("explicit"), "timeouts.explicit")
    _require_positive_number(timeouts.get("page_load"), "timeouts.page_load")


def _is_window_size(value: str) -> bool:
    parts = value.split(",")
    return len(parts) == 2 and all(part.strip().isdigit() for part in parts)


def validate_locators(data: Any, source: str | Path = "locators") -> None:
    if not isinstance(data, dict) or not data:
        raise ConfigError(f"Locator file is empty or not a mapping: {source}")

    for name, entry in data.items():
        if not isinstance(entry, dict) or {"by", "value"} - set(entry):
            raise ConfigError(f"Locator {name!r} in {source} must contain 'by' and 'value'")
        by = str(entry["by"]).strip().lower()
        if by not in SUPPORTED_BY:
            raise ConfigError(f"Locator {name!r} in {source} uses unsupported strategy: {by}")
        if not str(entry["value"]).strip():
            raise ConfigError(f"Locator {name!r} in {source} has an empty value")


@lru_cache(maxsize=None)
def load_locators(page: str) -> dict[str, dict[str, str]]:
    path = CONFIG_DIR / "locators" / f"{page}.yaml"
    data = read_yaml(path)
    validate_locators(data, path)
    return data
