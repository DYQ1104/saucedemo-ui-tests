from __future__ import annotations

from selenium.webdriver.support.ui import Select

from core.base_page import BasePage
from core.logger import get_logger

log = get_logger("page.inventory")


class InventoryPage(BasePage):
    """商品列表页（/inventory.html）。"""

    PAGE_TITLE = "Products"

    def wait_loaded(self) -> InventoryPage:
        self.wait_url_contains("/inventory.html")
        self.wait_text("title", self.PAGE_TITLE)
        return self

    def title_text(self) -> str:
        return self.text("title")

    def add_item_to_cart(self, product_name: str) -> InventoryPage:
        self.click("add_to_cart_by_name", product=product_name)
        # 加入成功后按钮变为 Remove，作为业务状态完成的信号。
        self.wait_visible("remove_by_name", product=product_name)
        log.info("Added to cart: %s", product_name)
        return self

    def remove_item(self, product_name: str) -> InventoryPage:
        self.click("remove_by_name", product=product_name)
        self.wait_visible("add_to_cart_by_name", product=product_name)
        return self

    def cart_badge_count(self) -> int:
        if not self.exists("cart_badge"):
            return 0
        raw = self.text("cart_badge")
        return int(raw) if raw else 0

    def open_cart(self) -> InventoryPage:
        self.click("cart_link")
        self.wait_url_contains("/cart.html")
        return self

    def sort_by(self, option_label: str) -> InventoryPage:
        Select(self.wait_visible("sort_select")).select_by_visible_text(option_label)
        self.wait.until(
            lambda _: Select(self.wait_present("sort_select")).first_selected_option.text
            == option_label
        )
        log.info("Sorted products by: %s", option_label)
        return self

    def product_names(self) -> list[str]:
        return self.texts("item_name")

    def product_prices(self) -> list[float]:
        return [self._to_amount(value) for value in self.texts("item_price")]

    def item_price(self, product_name: str) -> str:
        return self.text("item_price_by_name", product=product_name)

    def open_product(self, product_name: str) -> InventoryPage:
        self.click("open_item_by_name", product=product_name)
        self.wait_url_contains("/inventory-item.html")
        log.info("Opened product detail: %s", product_name)
        return self

    def logout(self) -> InventoryPage:
        self.click("menu_button")
        self.click("logout_link")
        self.wait.until(lambda _: self.current_url().rstrip("/") == self.base_url)
        log.info("Logged out")
        return self

    @staticmethod
    def _to_amount(price_text: str) -> float:
        return float(price_text.replace("$", "").replace(",", "").strip())
