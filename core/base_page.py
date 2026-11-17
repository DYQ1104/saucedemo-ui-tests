from __future__ import annotations

from urllib.parse import urljoin

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.logger import get_logger

BY_MAP = {
    "id": By.ID,
    "name": By.NAME,
    "class name": By.CLASS_NAME,
    "css selector": By.CSS_SELECTOR,
    "xpath": By.XPATH,
    "link text": By.LINK_TEXT,
    "partial link text": By.PARTIAL_LINK_TEXT,
    "tag name": By.TAG_NAME,
}

log = get_logger("page")


class BasePage:
    """页面基类：只沉淀定位、显式等待和基础交互，不承载业务流程。"""

    def __init__(self, driver, locators: dict, timeout: int = 10, base_url: str = ""):
        self.driver = driver
        self.locators = locators
        self.timeout = timeout
        self.base_url = base_url.rstrip("/")
        self.wait = WebDriverWait(driver, timeout)

    # ---------- 定位 ----------

    def locator(self, name: str, **params) -> tuple[str, str]:
        if name not in self.locators:
            raise KeyError(f"{self.__class__.__name__} has no locator named {name!r}")
        entry = self.locators[name]
        by = str(entry["by"]).strip().lower()
        if by not in BY_MAP:
            raise ValueError(f"Locator {name!r} uses unsupported strategy: {by}")
        value = str(entry["value"])
        if params:
            try:
                value = value.format(**params)
            except KeyError as exc:
                raise ValueError(f"Locator {name!r} is missing placeholder: {exc}") from exc
        return BY_MAP[by], value

    # ---------- 显式等待 ----------

    def wait_visible(self, name: str, timeout: float | None = None, **params) -> WebElement:
        return self._wait(timeout).until(
            EC.visibility_of_element_located(self.locator(name, **params))
        )

    def wait_clickable(self, name: str, timeout: float | None = None, **params) -> WebElement:
        return self._wait(timeout).until(
            EC.element_to_be_clickable(self.locator(name, **params))
        )

    def wait_present(self, name: str, timeout: float | None = None, **params) -> WebElement:
        return self._wait(timeout).until(
            EC.presence_of_element_located(self.locator(name, **params))
        )

    def wait_absent(self, name: str, timeout: float | None = None, **params) -> bool:
        return self._wait(timeout).until(
            EC.invisibility_of_element_located(self.locator(name, **params))
        )

    def wait_text(self, name: str, expected: str, timeout: float | None = None, **params) -> str:
        return self._wait(timeout).until(
            EC.text_to_be_present_in_element(self.locator(name, **params), expected)
        )

    def wait_text_contains(
        self, name: str, fragment: str, timeout: float | None = None, **params
    ) -> str:
        def _contains(_driver) -> str | bool:
            try:
                actual = self.wait_visible(name, timeout=0.5, **params).text.strip()
            except (TimeoutException, StaleElementReferenceException):
                return False
            return actual if fragment in actual else False

        return self._wait(timeout).until(_contains)

    def wait_url_contains(self, fragment: str, timeout: float | None = None) -> bool:
        return self._wait(timeout).until(EC.url_contains(fragment))

    # ---------- 基础交互 ----------

    def click(self, name: str, **params) -> None:
        element = self.wait_clickable(name, **params)
        element.click()
        log.debug("click %s:%s", self.__class__.__name__, name)

    def input_text(self, name: str, text: str, clear: bool = True, **params) -> None:
        element = self.wait_visible(name, **params)
        if clear:
            element.clear()
        element.send_keys(text)
        # 不输出具体输入内容，避免密码等敏感信息进入日志。
        log.debug("input %s:%s (len=%d)", self.__class__.__name__, name, len(text))

    def text(self, name: str, **params) -> str:
        return self.wait_visible(name, **params).text.strip()

    def texts(self, name: str, **params) -> list[str]:
        self.wait_present(name, **params)
        by, value = self.locator(name, **params)
        return [
            element.text.strip()
            for element in self.driver.find_elements(by, value)
            if element.is_displayed()
        ]

    def exists(self, name: str, **params) -> bool:
        by, value = self.locator(name, **params)
        return len(self.driver.find_elements(by, value)) > 0

    def is_visible(self, name: str, timeout: float = 2, **params) -> bool:
        try:
            self.wait_visible(name, timeout=timeout, **params)
            return True
        except TimeoutException:
            return False

    def current_url(self) -> str:
        return self.driver.current_url

    def navigate(self, path: str = "/") -> "BasePage":
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        log.info("navigate %s", url)
        self.driver.get(url)
        return self

    def _wait(self, timeout: float | None = None) -> WebDriverWait:
        if timeout is None:
            return self.wait
        return WebDriverWait(self.driver, timeout)
