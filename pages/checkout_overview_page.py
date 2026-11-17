from __future__ import annotations

from core.base_page import BasePage
from core.logger import get_logger

log = get_logger("page.checkout_overview")


class CheckoutOverviewPage(BasePage):
    """结账第二步：订单概览（/checkout-step-two.html）。"""

    PAGE_TITLE = "Checkout: Overview"

    def wait_loaded(self) -> CheckoutOverviewPage:
        self.wait_url_contains("/checkout-step-two.html")
        self.wait_text("title", self.PAGE_TITLE)
        return self

    def product_names(self) -> list[str]:
        return self.texts("item_name")

    def subtotal_text(self) -> str:
        return self.text("subtotal_label")

    def tax_text(self) -> str:
        return self.text("tax_label")

    def total_text(self) -> str:
        return self.text("total_label")

    def payment_info(self) -> str:
        return self.text("payment_info")

    def shipping_info(self) -> str:
        return self.text("shipping_info")

    def finish(self) -> CheckoutOverviewPage:
        self.click("finish_button")
        self.wait_url_contains("/checkout-complete.html")
        log.info("Order finished")
        return self

    def cancel(self) -> CheckoutOverviewPage:
        self.click("cancel_button")
        self.wait_url_contains("/inventory.html")
        return self
