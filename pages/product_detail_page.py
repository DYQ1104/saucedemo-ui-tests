from __future__ import annotations

from core.base_page import BasePage
from core.logger import get_logger

log = get_logger("page.product_detail")


class ProductDetailPage(BasePage):
    """商品详情页（/inventory-item.html?id=<n>）。"""

    def wait_loaded(self) -> ProductDetailPage:
        self.wait_url_contains("/inventory-item.html")
        self.wait_visible("back_to_products")
        return self

    def product_name(self) -> str:
        return self.text("item_name")

    def item_price(self) -> str:
        return self.text("item_price")

    def cart_badge_count(self) -> int:
        if not self.exists("cart_badge"):
            return 0
        raw = self.text("cart_badge")
        return int(raw) if raw else 0

    def add_to_cart(self) -> ProductDetailPage:
        self.click("add_to_cart")
        self.wait_visible("remove")
        log.info("Added to cart from product detail")
        return self

    def remove_from_cart(self) -> ProductDetailPage:
        self.click("remove")
        self.wait_visible("add_to_cart")
        log.info("Removed from cart on product detail")
        return self

    def back_to_products(self) -> ProductDetailPage:
        self.click("back_to_products")
        self.wait_url_contains("/inventory.html")
        return self
