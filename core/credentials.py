from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Account:
    username: str
    password: str


# 仅用于 SauceDemo 公开演示站点，账号信息本身展示在登录页。
# 真实项目应只从环境变量/CI Secret 注入，不在仓库保存任何凭据。
_DEMO_ACCOUNTS = {
    "standard": ("standard_user", "secret_sauce"),
    "locked": ("locked_out_user", "secret_sauce"),
    "problem": ("problem_user", "secret_sauce"),
    "performance_glitch": ("performance_glitch_user", "secret_sauce"),
}


def get_account(role: str = "standard") -> Account:
    if role not in _DEMO_ACCOUNTS:
        raise KeyError(f"Unknown demo account role: {role}")
    prefix = f"SAUCE_{role.upper()}"
    default_username, default_password = _DEMO_ACCOUNTS[role]
    return Account(
        username=os.getenv(f"{prefix}_USERNAME", default_username),
        password=os.getenv(f"{prefix}_PASSWORD", default_password),
    )
