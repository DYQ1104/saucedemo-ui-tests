from __future__ import annotations

from core.base_page import BasePage


class CheckoutCompletePage(BasePage):
    """结账完成页（/checkout-complete.html）。"""

    PAGE_TITLE = "Checkout: Complete!"

    def wait_loaded(self) -> CheckoutCompletePage:
        self.wait_url_contains("/checkout-complete.html")
        self.wait_text("title", self.PAGE_TITLE)
        return self

    def header_text(self) -> str:
        return self.text("complete_header")

    def message_text(self) -> str:
        return self.text("complete_text")

    def back_home(self) -> CheckoutCompletePage:
        self.click("back_home_button")
        self.wait_url_contains("/inventory.html")
        return self
