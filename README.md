# SauceDemo UI 自动化测试方案

> 技术栈：Selenium 4.52 + pytest 9.2 + PyYAML 6 + pytest-html 4（PO 模式）
> 演示站点：<https://www.saucedemo.com/>
> 最近验证：2026-11-17，Windows 11 + Python 3.13.12 + Edge 157（无头）。改造后全量 20/20（158.04s）；此前连续 3 轮 20/20（123.86s、131.95s、116.72s）。
> CI：Chrome/Firefox 双浏览器 smoke 矩阵 + 定时全量回归，产物按 `UI_RUN_ID` 归档。2026-11-17 托管验收：run #5 全量 regression 通过（unit 12s、Chrome 58s、Firefox 102s）。

本仓库是一套可直接运行、可继续扩展的 Web UI 自动化工程，覆盖「登录 → 商品列表 → 加购 → 购物车 → 结账信息 → 订单概览 → 完成页」完整链路。定位器全部在真实站点 DOM 上核对过，不依赖猜测的 selector。

**配套文档**：[需求规格说明书](docs/需求规格说明书.md)（项目范围、功能/非功能需求、20 条用例范围与验收标准）、[需求追踪矩阵](docs/需求追踪矩阵.md)（TC → BR/FR → 测试节点 → 标记 → 断言 → 结果逐条映射）。矩阵可用 `python tools/verify_traceability.py` 自动校验。

---

## 1. 方案概览

### 1.1 目标

- 用一套结构清晰的工程跑通 SauceDemo 的核心业务链路，验证框架闭环。
- 页面定位器、环境地址、业务数据与测试代码分离，降低站点小改版带来的维护成本。
- 失败时能定位问题：HTML 报告、截图、失败元信息、结构化日志四件套齐全。
- 本地一条命令运行，CI 可复用同一套命令。

### 1.2 范围与边界

| 项目 | 首期范围 |
|---|---|
| 浏览器 | Chrome / Edge / Firefox，默认自动探测，无头执行 |
| 环境 | demo（SauceDemo 公网演示站），单环境 |
| 执行方式 | 串行，每条用例独立浏览器会话 |
| 覆盖深度 | 核心正向链路 + 多商品流程 + 登录/表单负向 + 排序 + 购物车边界 |
| 暂不包含 | 并行、多环境矩阵、移动端、视觉回归、接口/数据库校验 |

SauceDemo 是公开共享演示站点，**不做并发压测、不制造脏数据、不修改共享账号状态**。每条用例结束即关闭浏览器。

### 1.3 技术选型

| 组件 | 版本 | 职责 |
|---|---|---|
| Python | 3.13 | 运行环境 |
| Selenium | 4.52.0 | 浏览器操作，Selenium Manager 自动解析驱动 |
| pytest | 9.2.0 | 用例发现、fixture、参数化、标记 |
| PyYAML | 6.0.3 | 环境配置、定位器、参数化数据 |
| pytest-html | 4.2.0 | 单文件 HTML 报告 |

---

## 2. 快速开始

### 2.1 环境要求

- Python 3.11+（本项目验证于 3.13.12）
- Chrome、Edge、Firefox 任一已安装
- 首次运行需要联网：Selenium Manager 会解析并下载匹配的浏览器驱动

### 2.2 初始化

Windows PowerShell：

```powershell
cd C:\path\to\saucedemo-ui-tests
python -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass   # 如激活脚本被策略拦截
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Git Bash / macOS / Linux：

```bash
cd /path/to/project
python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash
# source .venv/bin/activate        # macOS / Linux
python -m pip install -r requirements.txt
```

### 2.3 运行

```bash
# 全量（默认环境 demo，浏览器自动探测，无头）
pytest -v

# 冒烟集（提交前必跑）
pytest -m smoke -v

# 核心 P0 集
pytest -m p0 -v

# 指定文件 / 单条用例
pytest tests/test_checkout.py -v
pytest tests/test_cart.py::test_remove_item_from_cart -v

# 有头模式观察执行过程
pytest --headed -v

# 指定浏览器
pytest --browser=chrome -v
pytest --browser=edge -v

# 按关键字筛选
pytest -k "login and not locked" -v

# 配置层单元测试（不启动浏览器）
pytest -c pytest-unit.ini -v

# 校验用例、单元测试与需求追踪矩阵是否一致（不启动浏览器）
python tools/verify_traceability.py
```

运行结束后：

- 最新 HTML 报告：`reports/report.html`
- 构建归档目录：`reports/runs/<run_id>/`，包含报告、`run.json`、失败产物与本次日志
- 失败截图：`reports/runs/<run_id>/screenshots/<时间戳>_<用例ID>.png`
- 失败元信息：`reports/runs/<run_id>/<时间戳>_<用例ID>.json`
- 页面源码（可选）：`reports/runs/<run_id>/page_source/*.html`
- 运行日志：`logs/ui-tests.log`（累计）与 `logs/runs/<run_id>/ui-tests.log`（单次）

`run_id` 默认取时间戳；CI 通过 `UI_RUN_ID` 注入构建号，本地也可手动指定：

```bash
UI_RUN_ID=local-debug pytest -m smoke -v
```

---

## 3. 项目架构

### 3.1 目录结构

```text
.
├── config/
│   ├── config.yaml                 # 浏览器、超时、产物、日志级别
│   ├── env/
│   │   └── demo.yaml               # SauceDemo base_url
│   └── locators/                   # 按页面拆分定位器（全部来自真实 DOM）
│       ├── login.yaml
│       ├── inventory.yaml
│       ├── cart.yaml
│       ├── checkout_info.yaml
│       ├── checkout_overview.yaml
│       └── checkout_complete.yaml
├── core/
│   ├── config_loader.py            # YAML 读取、深度合并、校验、环境变量覆盖
│   ├── driver_factory.py           # 浏览器探测、WebDriver 创建、超时设置
│   ├── base_page.py                # 定位解析、显式等待、基础交互
│   ├── logger.py                   # 日志初始化（累计日志 + 单次运行日志）
│   ├── artifacts.py                # 失败产物与按 run_id 归档
│   └── credentials.py              # 演示账号 + 环境变量覆盖
├── pages/                          # 6 个 Page Object，只做动作与状态查询
│   ├── login_page.py
│   ├── inventory_page.py
│   ├── cart_page.py
│   ├── checkout_info_page.py
│   ├── checkout_overview_page.py
│   └── checkout_complete_page.py
├── tests/
│   ├── conftest.py                 # CLI 参数、fixture、失败附件与运行归档
│   ├── test_login.py
│   ├── test_cart.py
│   ├── test_inventory.py
│   └── test_checkout.py
├── tests_unit/
│   ├── test_config_loader.py       # 配置优先级、深度合并、校验、定位器
│   └── test_artifacts.py           # run_id 与归档逻辑
├── testdata/
│   ├── checkout_cases.yaml         # 结账必填校验参数化数据
│   └── login_cases.yaml            # 登录空字段参数化数据
├── docs/
│   ├── 需求规格说明书.md            # 范围、功能/非功能需求与验收标准
│   └── 需求追踪矩阵.md              # 20 条用例到需求、节点、标记与断言的映射
├── tools/
│   └── verify_traceability.py      # 校验 SRS / RTM / 收集结果 / 标记 / 需求覆盖
├── reports/                        # 运行产物（不入库）
│   └── runs/<run_id>/              # 按构建归档的报告、日志与失败产物
├── logs/                           # 运行日志（不入库）
├── .github/workflows/ui-tests.yml  # CI：Chrome/Firefox 矩阵
├── pytest.ini                      # UI 测试配置
├── pytest-unit.ini                 # 配置层单元测试配置
├── requirements.txt
├── .gitignore
└── README.md
```

### 3.2 分层调用关系

```text
pytest 用例（编排 + 业务断言）
   │
   ├── pages/*.py（用户动作、页面状态查询，不做断言）
   │      └── core/base_page.py（定位解析、显式等待、点击/输入/取文本）
   │             └── Selenium WebDriver
   │
   ├── tests/conftest.py
   │      ├── app_config ← core/config_loader.py ← config/*.yaml
   │      ├── driver     ← core/driver_factory.py
   │      ├── pages      ← pages/*.py + locators YAML
   │      └── 失败现场   → core/artifacts.py → reports/
   │
   └── testdata/*.yaml（参数化数据）
```

### 3.3 职责边界

| 层 | 负责 | 不负责 |
|---|---|---|
| `tests/` | 用例编排、业务结果断言、标记与参数化 | 直接写 XPath/CSS、直接管理浏览器 |
| `pages/` | 页面动作、页面状态查询、导航 | 断言、pytest 全局状态、报告逻辑 |
| `core/base_page.py` | 定位器解析、显式等待、通用交互 | 业务流程、重试大杂烩 |
| `core/driver_factory.py` | 浏览器创建与基础参数 | 用例数据、页面动作 |
| `config/*.yaml` | 环境、定位器、超时、非敏感数据 | 复杂流程与判断 |
| `tests/conftest.py` | 资源生命周期、CLI、失败附件 | 具体业务断言 |

---

## 4. 配置与测试数据

### 4.1 默认配置 `config/config.yaml`

```yaml
browser:
  name: auto          # auto | chrome | edge | firefox
  headless: true
  window_size: "1440,1000"
  page_load_strategy: normal
timeouts:
  implicit: 0         # 强制为 0，统一显式等待
  explicit: 10
  page_load: 30
artifacts:
  screenshot_on_failure: true
  save_page_source_on_failure: false
logging:
  level: INFO
```

- `browser.name=auto`：按 Chrome → Edge → Firefox 顺序探测本机已安装浏览器，CI 与本地可用同一份配置。
- `timeouts.implicit` 必须为 0：避免隐式等待与显式等待叠加造成超时不可预测。
- 首次运行较慢通常是 Selenium Manager 下载驱动；之后会复用缓存。

### 4.2 环境配置 `config/env/demo.yaml`

```yaml
base_url: "https://www.saucedemo.com"
```

新增环境只需增加 `config/env/<name>.yaml`，然后 `pytest --env=<name>`。

### 4.3 定位器配置

按页面拆分，示例 `config/locators/login.yaml`：

```yaml
username:
  by: css selector
  value: "[data-test='username']"
password:
  by: css selector
  value: "[data-test='password']"
login_button:
  by: css selector
  value: "[data-test='login-button']"
error_message:
  by: css selector
  value: "[data-test='error']"
```

商品行内按商品名动态定位，示例 `config/locators/inventory.yaml`：

```yaml
add_to_cart_by_name:
  by: xpath
  value: "//div[@data-test='inventory-item'][.//div[@data-test='inventory-item-name' and normalize-space()='{product}']]//button[starts-with(@data-test, 'add-to-cart')]"
```

`BasePage.locator(name, **params)` 会安全地填充 `{product}` 占位符。定位策略支持 `id / name / class name / css selector / xpath / link text / partial link text / tag name`，加载时统一校验。

### 4.4 配置优先级

```text
命令行参数 > 环境变量 > 环境 YAML > 默认配置
```

| 环境变量 | 作用 |
|---|---|
| `UI_BASE_URL` | 覆盖 base_url |
| `UI_BROWSER` | 覆盖 browser.name |
| `UI_HEADLESS` | `true/false` 覆盖无头设置 |

### 4.5 凭据管理

- `core/credentials.py` 内置 **SauceDemo 登录页公开展示的演示账号**，仅用于该公开演示站。
- 可用 `SAUCE_STANDARD_USERNAME`、`SAUCE_STANDARD_PASSWORD`、`SAUCE_LOCKED_*` 覆盖。
- 真实项目只允许从环境变量/CI Secret 注入，禁止把凭据写进 YAML 或代码。日志只记录用户名，不记录密码与输入内容。

---

## 5. 核心实现说明

### 5.1 配置加载（`core/config_loader.py`）

- `yaml.safe_load` 读取，拒绝空文件与非法根节点。
- `deep_merge` 递归合并，环境文件可只覆盖需要的子项。
- 启动即校验：`base_url` 协议、浏览器枚举、headless 类型、窗口尺寸、超时为正数、隐式等待为 0。
- 定位器文件在加载时逐条校验，缺少 `by/value` 或使用不支持的策略会立即失败，避免运行到一半才报错。

### 5.2 Driver Factory（`core/driver_factory.py`）

- 支持 `auto/chrome/edge/firefox`，Windows 下探测常见安装路径，类 Unix 下用 `shutil.which`。
- 无头参数：Chrome/Edge 使用 `--headless=new`，Firefox 使用 `-headless`。
- 统一设置窗口尺寸、页面加载超时、隐式等待为 0。
- 驱动由 Selenium Manager 解析，不手工维护 driver 路径。

### 5.3 BasePage（`core/base_page.py`）

只提供稳定通用能力：

- 定位器解析与占位符填充
- 显式等待：可见、可点击、存在、消失、文本、URL
- 交互：点击、输入（日志脱敏）、取文本、取多文本、存在性判断
- 导航：基于 `base_url` 拼接路径

页面对象不直接使用 `find_element`/`sleep`，所有同步都等待具体业务状态。

### 5.4 Page Object 示例

```python
# pages/inventory_page.py（节选）
def add_item_to_cart(self, product_name: str) -> "InventoryPage":
    self.click("add_to_cart_by_name", product=product_name)
    # 按钮变为 Remove，作为“加入成功”的业务状态信号
    self.wait_visible("remove_by_name", product=product_name)
    return self

def cart_badge_count(self) -> int:
    if not self.exists("cart_badge"):
        return 0
    return int(self.text("cart_badge"))
```

```python
# tests/test_cart.py（节选）
pages.login.open().login(accounts.standard.username, accounts.standard.password)
pages.inventory.wait_loaded()
pages.inventory.add_item_to_cart(BACKPACK)

assert pages.inventory.cart_badge_count() == 1
```

### 5.5 fixture 与浏览器生命周期（`tests/conftest.py`）

- `app_config`（session）：加载配置、应用 CLI 覆盖、初始化日志。
- `driver`（function）：每条用例新建浏览器，结束**无论成功失败**都 `quit()`。
- `pages`（function）：按页面装配 Page Object 与对应定位器。
- `accounts`（session）：演示账号。
- 失败时在 `quit()` 之前调用 `save_failure_artifacts()`，保存截图、元信息（URL/标题/环境/浏览器版本），可选页面源码。

---

## 6. 用例设计与覆盖矩阵

### 6.1 用例清单（20 条）

| # | 文件 | 用例 | 级别 | 标记 | 主要断言 |
|---|---|---|---|---|---|
| 1 | test_login.py | 标准账号登录成功 | P0 | smoke | 标题 Products、URL 进入 inventory |
| 2 | test_login.py | 错误密码登录 | P0 | smoke | 提示账号密码不匹配 |
| 3 | test_login.py | 锁定账号登录 | P1 | regression | 提示账号被锁定 |
| 4 | test_login.py | 空用户名登录 | P1 | regression | 提示 Username is required |
| 5 | test_login.py | 空密码登录 | P1 | regression | 提示 Password is required |
| 6 | test_inventory.py | 价格升序 + 名称降序 | P1 | regression | 排序结果符合规则 |
| 7 | test_inventory.py | 价格降序 | P1 | regression | 价格倒序排列 |
| 8 | test_inventory.py | 商品列表完整性 | P2 | regression | 6 个商品、名称非空且唯一、价格为正 |
| 9 | test_cart.py | 添加单个商品 | P0 | smoke | badge=1、商品/数量/价格正确 |
| 10 | test_cart.py | 移除单个商品 | P1 | regression | 商品行消失、badge=1 |
| 11 | test_cart.py | 添加多个商品 | P1 | regression | badge=3、商品列表与数量正确 |
| 12 | test_cart.py | 清空购物车 | P2 | regression | 商品行为空、badge 消失 |
| 13 | test_cart.py | 继续购物 | P2 | regression | 返回商品页且 badge 保留 |
| 14 | test_checkout.py | 单商品完整结账 | P0 | smoke | 概览商品/小计/总额、完成页文案 |
| 15-17 | test_checkout.py | 结账必填校验（3 组） | P1 | regression | 名/姓/邮编缺失时提示准确 |
| 18 | test_checkout.py | 多商品结账金额 | P1 | regression | 商品列表、小计=单价和、总额=小计+税 |
| 19 | test_checkout.py | 取消结账 | P1 | regression | 返回购物车且商品保留 |
| 20 | test_checkout.py | 下单后返回商品页 | P2 | regression | badge 清空、购物车为空 |

```bash
pytest -m smoke        # 4 条：1/2/9/14
pytest -m p0           # 4 条核心
pytest -m p1           # 12 条重要用例
pytest -m p2           # 4 条边界用例
pytest -m regression   # 全部 20 条
```

### 6.2 YAML 参数化数据

`testdata/checkout_cases.yaml`：

```yaml
- id: missing_first_name
  first_name: ""
  last_name: "Doe"
  postal_code: "100000"
  expected_error: "Error: First Name is required"
```

```python
@pytest.mark.parametrize("case", CHECKOUT_CASES, ids=[case["id"] for case in CHECKOUT_CASES])
def test_checkout_required_field_validation(pages, accounts, case):
    ...
    assert pages.checkout_info.error_message() == case["expected_error"]
```

`testdata/login_cases.yaml` 用 `empty_field` 指定置空字段，非空账号值由 `accounts` fixture 注入，避免在数据文件保存凭据：

```yaml
- id: empty_username
  empty_field: username
  expected_error: "Epic sadface: Username is required"
```

复杂分支、页面流转判断仍写 Python；YAML 只承载「输入 → 期望」结构简单的数据。

---

## 7. 执行与调试

### 7.1 常用命令

| 目的 | 命令 |
|---|---|
| 全量回归 | `pytest -v` |
| 冒烟 | `pytest -m smoke -v` |
| 单文件 | `pytest tests/test_checkout.py -v` |
| 单用例 | `pytest tests/test_cart.py::test_add_single_item_to_cart -v` |
| 有头观察 | `pytest --headed -v` |
| 指定浏览器 | `pytest --browser=chrome -v` |
| 指定环境 | `pytest --env=demo -v` |
| 配置层单元测试 | `pytest -c pytest-unit.ini -v` |
| 指定构建号归档 | `UI_RUN_ID=feature-x pytest -v` |
| 输出 HTML 报告 | 默认已写入 `reports/report.html` |

### 7.2 调试流程（推荐顺序）

1. **缩小范围**：先单跑失败用例，确认可复现。
2. **有头复现**：加 `--headed`，观察页面停留位置、错误提示、加载状态。
3. **看日志**：`logs/runs/<run_id>/ui-tests.log` 是本次运行日志，`logs/ui-tests.log` 是累计日志；包含导航、动作、排序、加购等关键节点，不含密码。
4. **看截图**：`reports/runs/<run_id>/screenshots/`，同时查看同名 `.json` 元信息中的 URL、标题、浏览器版本、`run_id`。
5. **看页面源码**：临时把 `artifacts.save_page_source_on_failure` 改为 `true`，复现后到 `reports/runs/<run_id>/page_source/` 分析 DOM。
6. **核定位器**：用浏览器 DevTools 确认 `data-test` / id 是否变化，只改对应页面 YAML，重跑单用例。
7. **判断归属**：站点慢/改版属于产品与用例问题，不要用 `sleep` 或盲目重试掩盖。

### 7.3 常见问题

| 现象 | 可能原因 | 处理 |
|---|---|---|
| `SessionNotCreated` / browser binary not found | 本机无对应浏览器或版本不匹配 | 安装浏览器，或 `--browser=edge`；企业代理下配置 `HTTPS_PROXY` |
| 首次运行卡住约 1 分钟 | Selenium Manager 下载驱动 | 等待完成；CI 预装浏览器并缓存驱动 |
| 等待标题超时 | 站点慢或页面结构变化 | 看截图/源码；必要时提高 `timeouts.explicit`，确认定位器 |
| 报告未生成 | 未通过 pytest 启动 | 用 `python -m pytest` 或激活虚拟环境后 `pytest` |
| 终端中文乱码 | Windows 控制台编码 | 运行日志已统一英文；中文文档请用支持 UTF-8 的终端查看 |
| 用例互相影响 | 共享浏览器会话 | 本项目每条用例独立 driver，勿改成 session 级 driver |

---

## 8. 失败诊断与产物

| 产物 | 路径 | 说明 |
|---|---|---|
| HTML 报告 | `reports/report.html` | 单文件，含用例状态、耗时、失败堆栈、日志 |
| 失败截图 | `reports/runs/<run_id>/screenshots/*.png` | 在 driver 退出前保存，文件名含时间戳与用例 ID |
| 失败元信息 | `reports/runs/<run_id>/*.json` | URL、标题、环境、浏览器、版本、时间、`run_id` |
| 页面源码 | `reports/runs/<run_id>/page_source/*.html` | 默认关闭，排查 DOM 时开启 |
| 运行日志 | `logs/runs/<run_id>/ui-tests.log` | UTF-8，单次运行日志；`logs/ui-tests.log` 为累计日志 |
| 构建归档 | `reports/runs/<run_id>/` | 报告、日志、失败产物与 `run.json` 汇总，`reports/runs/latest.txt` 指向最近一次 |

`run_id` 来源优先级：`UI_RUN_ID` 环境变量 > 本地时间戳（`%Y%m%d-%H%M%S`）。CI 用 `构建号-套件-浏览器` 命名，便于按构建下载产物。

失败截图可能包含页面数据，对外分享前需脱敏；`reports/`、`logs/` 已在 `.gitignore` 中排除。

---

## 9. CI 接入

已提供 `.github/workflows/ui-tests.yml`，三个 job：

| Job | 触发条件 | 内容 | 产物保留 |
|---|---|---|---|
| `unit` | push(main) / PR / 手动 / 定时 | `pytest -c pytest-unit.ini -v`（32 条配置层单测） | 无 |
| `smoke` | push(main) / PR / 手动 | Chrome、Firefox 矩阵，`pytest -m smoke -v` | 7 天 |
| `regression` | 定时（每日 18:00 UTC）/ 手动 | Chrome、Firefox 矩阵，全量 `pytest -v` | 14 天 |

```yaml
jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.13", cache: pip }
      - run: python -m pip install -r requirements.txt
      - run: python -m pytest -c pytest-unit.ini -v

  smoke:
    if: github.event_name != 'schedule'
    needs: unit
    strategy:
      fail-fast: false
      matrix: { browser: [chrome, firefox] }
    env:
      UI_BROWSER: ${{ matrix.browser }}
      UI_HEADLESS: "true"
      UI_RUN_ID: ${{ github.run_id }}-${{ github.run_attempt }}-smoke-${{ matrix.browser }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.13", cache: pip }
      - run: python -m pip install -r requirements.txt
      - run: python -m pytest -m smoke -v
      - name: Upload test artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: smoke-${{ matrix.browser }}-${{ github.run_id }}
          path: |
            reports/runs/
            logs/
          retention-days: 7
```

`regression` 与 `smoke` 结构相同，改为 `if: github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'`、执行 `python -m pytest -v`、`UI_RUN_ID` 前缀 `regression`、产物保留 14 天。

CI 约定：

- 单元测试先行，失败则 smoke/regression 不启动，避免浪费浏览器时长。
- PR 跑 smoke（双浏览器），定时与手动跑全量回归（双浏览器）。
- `UI_RUN_ID` 由构建号生成，`reports/runs/<run_id>/` 与 `logs/runs/<run_id>/` 一一对应，产物按构建下载。
- 凭据通过 Secret 注入，仓库只保存变量名。
- 串行优先；SauceDemo 为共享演示站，矩阵只并行不同浏览器，不提高单浏览器并发。
- 报告与截图作为构建产物归档，不提交仓库；失败截图可能含页面数据，产物保留期与访问权限需按团队规范控制。
- `concurrency` 以 ref + 事件分组并 `cancel-in-progress`，同一分支重复推送只保留最新运行。
- 测试失败时输出 `::error::` annotation，可直接在运行页或 API 看到失败用例与异常行。

托管运行记录（2026-11-17）：

| Run | 触发 | 结果 |
|---|---|---|
| #1 | push | unit、Firefox smoke 通过；Chrome smoke 因站点瞬时不可达失败 |
| #2 | push | unit 12s、Chrome smoke 49s、Firefox smoke 46s 通过 |
| #3 | push（文档） | 通过 |
| #4 | dispatch | 被 #5 的 `concurrency` 取消 |
| #5 | dispatch | unit 12s、Chrome regression 58s、Firefox regression 102s 通过 |

---

## 10. 从零落地的实施步骤

| 步骤 | 动作 | 本项目对应产物 | 状态 |
|---|---|---|---|
| 1 | 手工走通站点主流程，记录 URL/文案/字段 | 第 13 节定位器核对记录 | 完成 |
| 2 | 初始化 Python 项目与依赖 | `.venv`、`requirements.txt`、`.gitignore` | 完成 |
| 3 | 实现配置读取与校验 | `config/`、`core/config_loader.py` | 完成 |
| 4 | 实现 Driver Factory 与 driver fixture | `core/driver_factory.py`、`tests/conftest.py` | 完成 |
| 5 | 封装 BasePage | `core/base_page.py` | 完成 |
| 6 | 按页面实现 PO 与定位器 YAML | `pages/`、`config/locators/` | 完成 |
| 7 | 先跑 3 条核心用例，再扩负向与排序 | `tests/test_*.py` | 完成 |
| 8 | 失败截图、日志、HTML 报告，按构建归档 | `core/artifacts.py`、`reports/runs/`、`logs/runs/` | 完成 |
| 9 | 配置层单元测试 | `tests_unit/`、`pytest-unit.ini` | 完成（32 条） |
| 10 | 接入 CI 并保留扩展点 | `.github/workflows/ui-tests.yml` | 完成；托管 smoke 与全量 regression 均通过 |

### 新增一条用例的标准动作

1. 在对应页面的 `config/locators/*.yaml` 增加有业务含义的定位器。
2. 在 Page Object 中增加「用户动作」或「页面状态查询」方法。
3. 在测试文件中编排流程，仅对业务结果做断言。
4. 加标记（smoke / p0 / p1 / p2）。
5. 单条运行验证，再跑全量确认无状态串扰。
6. 若新增数据驱动，优先补到 `testdata/*.yaml`。

---

## 11. 工程约定与扩展路线

### 11.1 约定

- 等待具体业务状态，禁止 `sleep()`。
- 定位器优先 `data-test` / `id`，避免绝对 XPath 与布局层级。
- 用例只表达业务动作与预期；页面对象不写断言。
- 每条用例独立浏览器会话，不依赖上一条用例的购物车状态。
- 日志不记录密码与输入内容。
- 失败先修等待条件和定位器，不用重试掩盖不稳定。

### 11.2 下一步扩展

1. **补齐本机浏览器证据**：Chrome/Firefox 已在托管 CI 完成 20 条全量回归；本机仍仅 Edge 157 可运行。
2. **更多边界场景**：商品详情页加购、结账概览取消、排序结果在页面跳转后的保持情况。
3. **并行执行**：先确认账号与会话隔离，再引入 `pytest-xdist`，逐步提升并发。
4. **报告升级**：需要趋势与附件时切换 Allure；当前 pytest-html 足够首期闭环。
5. **Page Component**：页头、购物车 badge 等复用组件抽成组件对象，减少重复。
6. **测试数据治理**：需要后端造数时增加 fixture 级数据准备与清理。

---

## 12. 验收核对

- [x] 一条命令可选择环境并运行指定测试：`pytest --env=demo tests/test_login.py -v`
- [x] P0 用例本机稳定跑通：Edge 157 下 20 条连续 3 轮全部通过（2026-11-17）
- [ ] Chrome/Firefox 本机实跑：本机未安装 Chrome/Firefox，且 `winget` 安装被策略拦截；已在 CI 配置双浏览器矩阵，待托管环境首跑留证
- [x] 定位器、环境地址、业务数据与测试代码分离
- [x] 凭据可使用环境变量覆盖，仓库不保存真实凭据
- [x] 每条用例独立 WebDriver，结束可靠 `quit()`
- [x] 失败时生成截图、元信息、日志和 HTML 报告，并按 `UI_RUN_ID` 归档到 `reports/runs/<run_id>/`
- [x] 配置层单元测试 32 条通过，覆盖配置优先级、非法配置与归档逻辑
- [x] README 说明安装、运行、目录职责、报告位置与账号边界
- [x] 20 条用例与需求追踪矩阵逐条对齐：`python tools/verify_traceability.py` 23/23 检查通过
- [x] CI 托管 smoke：unit + Chrome/Firefox smoke 在 GitHub Actions 通过（2026-11-17，run #2/#3）
- [x] CI 全量 regression：dispatch run #5 通过，unit 12s、Chrome 58s、Firefox 102s

---

## 13. 附录

### 13.1 定位器核对记录（2026-11-16 真实 DOM）

| 页面 | 元素 | 定位器 |
|---|---|---|
| 登录 | 用户名 | `[data-test='username']` |
| 登录 | 密码 | `[data-test='password']` |
| 登录 | 登录按钮 | `[data-test='login-button']` |
| 登录 | 错误提示 | `[data-test='error']` |
| 商品 | 标题 | `[data-test='title']` |
| 商品 | 排序下拉 | `[data-test='product-sort-container']` |
| 商品 | 购物车链接 | `[data-test='shopping-cart-link']` |
| 商品 | 购物车角标 | `[data-test='shopping-cart-badge']` |
| 商品 | 商品名/价格 | `[data-test='inventory-item-name']` / `[data-test='inventory-item-price']` |
| 购物车 | 结算按钮 | `[data-test='checkout']` |
| 购物车 | 商品数量 | `[data-test='item-quantity']` |
| 结账信息 | 名/姓/邮编 | `[data-test='firstName']` / `lastName` / `postalCode` |
| 结账信息 | 继续按钮 | `[data-test='continue']` |
| 结账概览 | 小计/税/总额 | `[data-test='subtotal-label']` / `tax-label` / `total-label` |
| 结账概览 | 完成按钮 | `[data-test='finish']` |
| 完成页 | 完成标题 | `[data-test='complete-header']` |
| 完成页 | 返回商品 | `[data-test='back-to-products']` |

站点若改版，只需更新 `config/locators/` 对应文件；Page Object 与测试用例通常无需改动。

### 13.2 Page Object 速查

| 页面 | 主要方法 |
|---|---|
| LoginPage | `open()`、`login(u,p)`、`error_message()`、`dismiss_error()` |
| InventoryPage | `wait_loaded()`、`add_item_to_cart(name)`、`remove_item(name)`、`cart_badge_count()`、`open_cart()`、`sort_by(label)`、`product_names()`、`product_prices()`、`item_price(name)` |
| CartPage | `wait_loaded()`、`wait_empty()`、`product_names()`、`item_quantity(name)`、`item_price(name)`、`remove_item(name)`、`open_checkout()`、`continue_shopping()` |
| CheckoutInfoPage | `wait_loaded()`、`fill_customer(...)`、`submit_customer(...)`、`error_message()`、`cancel()` |
| CheckoutOverviewPage | `wait_loaded()`、`product_names()`、`subtotal_text()`、`tax_text()`、`total_text()`、`finish()`、`cancel()` |
| CheckoutCompletePage | `wait_loaded()`、`header_text()`、`message_text()`、`back_home()` |

### 13.3 已验证运行结果

```text
platform win32 -- Python 3.13.12, pytest-9.2.0
browser=edge 157.0.4341.60 headless=True
collected 20 items
20 passed in 116.72s
```

首次运行还会叠加 Selenium Manager 驱动解析时间；驱动缓存后全量约 2 分钟。
