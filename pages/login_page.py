from __future__ import annotations

from core.base_page import BasePage
from core.logger import get_logger

log = get_logger("page.login")


class LoginPage(BasePage):
    """SauceDemo 登录页。"""

    def open(self) -> "LoginPage":
        self.navigate("/")
        self.wait_visible("login_button")
        return self

    def login(self, username: str, password: str) -> "LoginPage":
        self.input_text("username", username)
        self.input_text("password", password)
        self.click("login_button")
        log.info("Login submitted: username=%s", username)
        return self

    def error_message(self) -> str:
        return self.text("error_message")

    def dismiss_error(self) -> "LoginPage":
        if self.exists("error_close_button"):
            self.click("error_close_button")
        return self
