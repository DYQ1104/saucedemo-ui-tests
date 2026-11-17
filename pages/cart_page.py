from __future__ import annotations

from core.base_page import BasePage
from core.logger import get_logger

log = get_logger("page.cart")


class CartPage(BasePage):
    """购物车页（/cart.html）。"""

    PAGE_TITLE = "Your Cart"

    def wait_loaded(self) -> "CartPage":
        self.wait_url_contains("/cart.html")
        self.wait_text("title", self.PAGE_TITLE)
        return self

    def wait_empty(self) -> "CartPage":
        self.wait.until(lambda _: not self.exists("cart_item"))
        return self

    def title_text(self) -> str:
        return self.text("title")

    def cart_badge_count(self) -> int:
        if not self.exists("cart_badge"):
            return 0
        raw = self.text("cart_badge")
        return int(raw) if raw else 0

    def product_names(self) -> list[str]:
        return self.texts("item_name")

    def item_quantity(self, product_name: str) -> str:
        return self.text("item_quantity_by_name", product=product_name)

    def item_price(self, product_name: str) -> str:
        return self.text("item_price_by_name", product=product_name)

    def remove_item(self, product_name: str) -> "CartPage":
        self.click("remove_by_name", product=product_name)
        self.wait_absent("item_row_by_name", product=product_name)
        log.info("Removed from cart: %s", product_name)
        return self

    def continue_shopping(self) -> "CartPage":
        self.click("continue_shopping_button")
        self.wait_url_contains("/inventory.html")
        return self

    def open_checkout(self) -> "CartPage":
        self.click("checkout_button")
        self.wait_url_contains("/checkout-step-one.html")
        return self
