from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions

from core.logger import get_logger

log = get_logger("driver")

# Windows 常见安装路径；Selenium Manager 负责解析驱动，这里只负责发现浏览器本体。
_WINDOWS_BROWSER_PATHS = {
    "chrome": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ],
    "edge": [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ],
    "firefox": [r"C:\Program Files\Mozilla Firefox\firefox.exe"],
}

_BINARY_NAMES = {
    "chrome": ("google-chrome", "chrome", "chromium"),
    "edge": ("microsoft-edge", "msedge"),
    "firefox": ("firefox",),
}


def _is_installed(name: str) -> bool:
    if os.name == "nt":
        return any(Path(path).is_file() for path in _WINDOWS_BROWSER_PATHS.get(name, []))
    return any(shutil.which(binary) for binary in _BINARY_NAMES.get(name, ()))


def resolve_browser_name(configured: str) -> str:
    name = configured.strip().lower()
    if name != "auto":
        return name
    for candidate in ("chrome", "edge", "firefox"):
        if _is_installed(candidate):
            log.info("browser.name=auto resolved to: %s", candidate)
            return candidate
    raise RuntimeError(
        "No Chrome/Edge/Firefox found. Install a browser or set 'browser.name' / --browser explicitly."
    )


def create_driver(config: dict):
    browser = resolve_browser_name(config["browser"]["name"])
    config["browser"]["resolved_name"] = browser
    headless = config["browser"]["headless"]
    window_size = config["browser"].get("window_size", "1440,1000")
    page_load_strategy = config["browser"].get("page_load_strategy", "normal")

    if browser == "chrome":
        options = ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.page_load_strategy = page_load_strategy
        driver = webdriver.Chrome(options=options)
    elif browser == "edge":
        options = EdgeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.page_load_strategy = page_load_strategy
        driver = webdriver.Edge(options=options)
    elif browser == "firefox":
        options = FirefoxOptions()
        if headless:
            options.add_argument("-headless")
        options.page_load_strategy = page_load_strategy
        driver = webdriver.Firefox(options=options)
    else:
        raise ValueError(f"Unsupported browser: {browser}")

    width, height = (int(part.strip()) for part in window_size.split(","))
    driver.set_window_size(width, height)
    driver.set_page_load_timeout(config["timeouts"]["page_load"])
    # 隐式等待保持为 0，避免与显式等待叠加导致超时不可预测。
    driver.implicitly_wait(0)
    log.info(
        "WebDriver created: browser=%s version=%s headless=%s",
        browser,
        driver.capabilities.get("browserVersion", "unknown"),
        headless,
    )
    return driver
