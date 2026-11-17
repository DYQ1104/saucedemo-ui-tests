from __future__ import annotations

from core.base_page import BasePage
from core.logger import get_logger

log = get_logger("page.checkout_info")


class CheckoutInfoPage(BasePage):
    """结账第一步：填写收货信息（/checkout-step-one.html）。"""

    PAGE_TITLE = "Checkout: Your Information"

    def wait_loaded(self) -> CheckoutInfoPage:
        self.wait_url_contains("/checkout-step-one.html")
        self.wait_text("title", self.PAGE_TITLE)
        return self

    def fill_customer(self, first_name: str, last_name: str, postal_code: str) -> CheckoutInfoPage:
        self.input_text("first_name", first_name)
        self.input_text("last_name", last_name)
        self.input_text("postal_code", postal_code)
        return self

    def submit_customer(self, first_name: str, last_name: str, postal_code: str) -> CheckoutInfoPage:
        self.fill_customer(first_name, last_name, postal_code)
        self.click("continue_button")
        log.info("Checkout information submitted")
        return self

    def error_message(self) -> str:
        return self.text("error_message")

    def dismiss_error(self) -> CheckoutInfoPage:
        if self.exists("error_close_button"):
            self.click("error_close_button")
        return self

    def cancel(self) -> CheckoutInfoPage:
        self.click("cancel_button")
        self.wait_url_contains("/cart.html")
        return self
