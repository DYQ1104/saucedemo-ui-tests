"""交叉校验需求规格说明书、需求追踪矩阵、pytest 收集结果与用例标记。

用法（项目根目录）：
    python tools/verify_traceability.py
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
SRS_PATH = ROOT / "docs" / "需求规格说明书.md"
RTM_PATH = ROOT / "docs" / "需求追踪矩阵.md"
README_PATH = ROOT / "README.md"
TEST_DIR = ROOT / "tests"
UNIT_TEST_DIR = ROOT / "tests_unit"
UNIT_INI = ROOT / "pytest-unit.ini"
CORE_DIR = ROOT / "core"
PAGES_DIR = ROOT / "pages"

EXPECTED_MARKER_COUNTS = {"smoke": 4, "p0": 4, "p1": 16, "p2": 6, "regression": 26}

passes: list[str] = []
failures: list[str] = []


def check(condition: bool, ok: str, fail: str) -> None:
    (passes if condition else failures).append(ok if condition else fail)


def parse_srs_cases(text: str) -> list[dict[str, str]]:
    block = text.split("### 7.1", 1)[1].split("### 7.2", 1)[0]
    pattern = re.compile(
        r"^\|\s*(TC-\d{3})\s*\|\s*([^|]+?)\s*\|\s*(P\d)\s*\|\s*([^|]+?)\s*"
        r"\|\s*`([^`]+)`\s*\|\s*$"
    )
    cases = []
    for line in block.splitlines():
        match = pattern.match(line.strip())
        if match:
            cases.append(
                {
                    "id": match.group(1),
                    "scenario": match.group(2),
                    "priority": match.group(3),
                    "marker": match.group(4),
                    "test": match.group(5),
                }
            )
    return cases


def parse_rtm_rows(text: str) -> list[dict[str, str]]:
    rows = []
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 7 or not re.fullmatch(r"TC-\d{3}", cells[0]):
            continue
        node = cells[3].strip("`").replace("\\", "/")
        rows.append(
            {
                "id": cells[0],
                "scenario": cells[1],
                "requirements": cells[2].strip("`"),
                "node": node,
                "markers": {m.strip().lower() for m in cells[4].split("/") if m.strip()},
                "assertions": cells[5],
                "result": cells[6],
            }
        )
    return rows


def collect_items() -> list[str]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        "-o",
        "addopts=",
        "-p",
        "no:cacheprovider",
        str(TEST_DIR),
    ]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    if result.returncode != 0:
        failures.append(f"pytest 收集失败：{result.stdout.strip()} {result.stderr.strip()}")
        return []
    items = []
    for line in result.stdout.splitlines():
        line = line.strip().replace("\\", "/")
        if line.startswith("tests/") and "::" in line:
            items.append(line)
    return items


def collect_unit_items() -> list[str]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-c",
        str(UNIT_INI),
        "--collect-only",
        "-q",
        "-o",
        "addopts=",
        "-p",
        "no:cacheprovider",
        str(UNIT_TEST_DIR),
    ]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    if result.returncode != 0:
        failures.append(f"配置层单元测试收集失败：{result.stdout.strip()} {result.stderr.strip()}")
        return []
    return [
        line.strip().replace("\\", "/")
        for line in result.stdout.splitlines()
        if line.strip().startswith("tests_unit/") and "::" in line
    ]


def extract_marks(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Attribute):
        if isinstance(node.value, ast.Attribute) and node.value.attr == "mark":
            return {node.attr}
        return set()
    if isinstance(node, (ast.List, ast.Tuple)):
        marks: set[str] = set()
        for element in node.elts:
            marks |= extract_marks(element)
        return marks
    return set()


def inspect_test_markers() -> dict[tuple[str, str], set[str]]:
    markers: dict[tuple[str, str], set[str]] = {}
    for path in sorted(TEST_DIR.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        module_marks: set[str] = set()
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in node.targets):
                module_marks |= extract_marks(node.value)
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                continue
            marks = set(module_marks)
            for decorator in node.decorator_list:
                marks |= extract_marks(decorator)
            marks.discard("parametrize")
            markers[(path.relative_to(ROOT).as_posix(), node.name)] = marks
    return markers


def expand_requirement_ids(text: str) -> set[str]:
    ids: set[str] = set()
    for prefix, start, end in re.findall(r"FR-([A-Z]+)-(\d+)\s*~\s*(\d+)", text):
        for number in range(int(start), int(end) + 1):
            ids.add(f"FR-{prefix}-{number:02d}")
    for prefix, number in re.findall(r"FR-([A-Z]+)-(\d+)", text):
        ids.add(f"FR-{prefix}-{int(number):02d}")
    for start, end in re.findall(r"NFR-(\d+)\s*~\s*(\d+)", text):
        for number in range(int(start), int(end) + 1):
            ids.add(f"NFR-{number:02d}")
    for number in re.findall(r"NFR-(\d+)", text):
        ids.add(f"NFR-{int(number):02d}")
    return ids


def count_readme_cases(text: str) -> int:
    block = text.split("### 6.1", 1)[1].split("```bash", 1)[0]
    total = 0
    for line in block.splitlines():
        match = re.match(r"^\|\s*(\d+)(?:\s*-\s*(\d+))?\s*\|", line)
        if match:
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else start
            total += end - start + 1
    return total


def main() -> int:
    for path in (SRS_PATH, RTM_PATH, README_PATH):
        if not path.is_file():
            print(f"[FAIL] 缺少文档：{path.relative_to(ROOT)}")
            return 1

    srs_text = SRS_PATH.read_text(encoding="utf-8")
    rtm_text = RTM_PATH.read_text(encoding="utf-8")
    readme_text = README_PATH.read_text(encoding="utf-8")

    srs_cases = parse_srs_cases(srs_text)
    rtm_rows = parse_rtm_rows(rtm_text)
    items = collect_items()
    test_markers = inspect_test_markers()

    # 1. SRS 用例表
    expected_ids = [f"TC-{number:03d}" for number in range(1, 27)]
    srs_ids = [case["id"] for case in srs_cases]
    check(len(srs_cases) == 26, "SRS 用例表共 26 条", f"SRS 用例表为 {len(srs_cases)} 条，应为 26 条")
    check(srs_ids == expected_ids, "SRS 用例编号 TC-001 ~ TC-026 连续无缺号", f"SRS 用例编号异常：{srs_ids}")

    # 2. RTM 与 SRS 对齐
    rtm_ids = [row["id"] for row in rtm_rows]
    check(len(rtm_rows) == 26, "RTM 逐条矩阵共 26 行", f"RTM 逐条矩阵为 {len(rtm_rows)} 行，应为 26 行")
    check(rtm_ids == srs_ids, "RTM 用例编号与 SRS 完全一致", "RTM 与 SRS 的用例编号或顺序不一致")
    mismatched_scenarios = [
        f"{srs['id']}: {srs['scenario']} != {rtm['scenario']}"
        for srs, rtm in zip(srs_cases, rtm_rows, strict=False)
        if srs["scenario"] != rtm["scenario"]
    ]
    check(not mismatched_scenarios, "RTM 场景描述与 SRS 一致", f"场景描述不一致：{mismatched_scenarios}")

    # 3. 测试节点与 pytest 收集结果对齐
    rtm_nodes = [row["node"] for row in rtm_rows]
    check(len(items) == 26, f"pytest 实际收集 26 条（当前 {len(items)} 条）", f"pytest 实际收集 {len(items)} 条，应为 26 条")
    check(
        sorted(rtm_nodes) == sorted(items),
        "RTM 测试节点与 pytest 收集结果完全一致",
        "RTM 与收集结果存在差异："
        f"缺少 {sorted(set(rtm_nodes) - set(items))}，多出 {sorted(set(items) - set(rtm_nodes))}",
    )
    check(len(set(rtm_nodes)) == len(rtm_nodes), "RTM 无重复测试节点", "RTM 存在重复测试节点")
    node_mismatches = [
        f"{srs['id']} -> {srs['test']} != {row['node']}"
        for srs, row in zip(srs_cases, rtm_rows, strict=False)
        if not row["node"].endswith(srs["test"])
    ]
    check(not node_mismatches, "SRS 测试函数名与 RTM 节点一一对应", f"测试函数名不一致：{node_mismatches}")

    # 4. 标记：AST 实际标记 vs RTM / SRS 优先级
    marker_problems = []
    for srs, row in zip(srs_cases, rtm_rows, strict=False):
        module, rest = row["node"].split("::", 1)
        function = rest.split("[", 1)[0]
        actual = test_markers.get((module, function))
        if actual is None:
            marker_problems.append(f"{row['id']}: 未找到 {module}::{function}")
            continue
        expected = set(row["markers"]) | {srs["priority"].lower()}
        missing = expected - actual
        if missing:
            marker_problems.append(f"{row['id']}: 缺少标记 {sorted(missing)}，实际 {sorted(actual)}")
    check(not marker_problems, "26 条用例的优先级与标记均与源码一致", f"标记不一致：{marker_problems}")

    marker_counts = {name: 0 for name in EXPECTED_MARKER_COUNTS}
    for item in items:
        module, rest = item.split("::", 1)
        function = rest.split("[", 1)[0]
        for mark in test_markers.get((module, function), set()):
            marker_counts[mark] = marker_counts.get(mark, 0) + 1
    check(
        marker_counts == EXPECTED_MARKER_COUNTS,
        f"执行集数量一致：{marker_counts}",
        f"执行集数量不一致：{marker_counts} != {EXPECTED_MARKER_COUNTS}",
    )

    # 5. YAML 参数化数据与参数化用例 ID 对齐
    login_cases = yaml.safe_load((ROOT / "testdata" / "login_cases.yaml").read_text(encoding="utf-8"))
    checkout_cases = yaml.safe_load((ROOT / "testdata" / "checkout_cases.yaml").read_text(encoding="utf-8"))
    login_ids = [case["id"] for case in login_cases]
    checkout_ids = [case["id"] for case in checkout_cases]
    check(
        login_ids == ["empty_username", "empty_password"],
        "登录参数化数据为 empty_username / empty_password",
        f"登录参数化数据异常：{login_ids}",
    )
    check(
        checkout_ids == ["missing_first_name", "missing_last_name", "missing_postal_code"],
        "结账参数化数据覆盖名 / 姓 / 邮编缺失",
        f"结账参数化数据异常：{checkout_ids}",
    )
    yaml_nodes = [item for item in items if "[" in item]
    expected_yaml_nodes = {
        *[f"tests/test_login.py::test_login_with_empty_field_shows_error[{case_id}]" for case_id in login_ids],
        *[
            f"tests/test_checkout.py::test_checkout_required_field_validation[{case_id}]"
            for case_id in checkout_ids
        ],
    }
    check(
        set(yaml_nodes) == expected_yaml_nodes,
        "YAML 参数化展开为 5 条独立用例",
        f"YAML 参数化节点不一致：{sorted(set(yaml_nodes) ^ expected_yaml_nodes)}",
    )

    # 6. 配置层单元测试
    unit_items = collect_unit_items()
    check(
        len(unit_items) == 32,
        "配置层单元测试收集 32 条",
        f"配置层单元测试收集 {len(unit_items)} 条，应为 32 条",
    )
    unit_names = {item.split("::")[-1].split("[", 1)[0] for item in unit_items}
    required_unit_tests = {
        "test_environment_variables_override_files",
        "test_cli_overrides_win_over_environment",
        "test_invalid_config_is_rejected",
        "test_archive_run_copies_report_log_and_metadata",
    }
    check(
        required_unit_tests <= unit_names,
        "配置优先级、非法配置与运行归档均有单元测试",
        f"缺少单元测试：{sorted(required_unit_tests - unit_names)}",
    )

    # 7. README 用例矩阵数量
    readme_count = count_readme_cases(readme_text)
    check(readme_count == 26, "README 用例矩阵覆盖 26 条（15-17 展开为 3 条）", f"README 用例矩阵为 {readme_count} 条")

    # 8. 需求覆盖：SRS 定义的需求 ID 必须全部出现在 RTM
    defined_ids: set[str] = set()
    for line in srs_text.splitlines():
        match = re.match(r"^\|\s*(FR-[A-Z]+-\d+|NFR-\d+)\s*\|", line)
        if match:
            defined_ids.add(match.group(1))
    covered_ids = expand_requirement_ids(rtm_text)
    check(
        defined_ids <= covered_ids,
        f"SRS 定义的 {len(defined_ids)} 个 FR/NFR 均被 RTM 覆盖",
        f"RTM 未覆盖需求：{sorted(defined_ids - covered_ids)}",
    )
    check(
        all(f"FR-COV-{number:02d}" in covered_ids for number in range(1, 6)),
        "FR-COV-01 ~ 05 均有对应用例",
        "FR-COV 用例覆盖不完整",
    )
    missing_br = [f"BR-{number:02d}" for number in range(1, 6) if f"BR-{number:02d}" not in rtm_text]
    check(not missing_br, "BR-01 ~ 05 均在 RTM 中建立映射", f"RTM 缺少业务需求：{missing_br}")
    empty_req_rows = [
        row["id"]
        for row in rtm_rows
        if not re.search(r"(?:BR|FR|NFR)-[A-Z0-9-]*\d", row["requirements"])
    ]
    check(not empty_req_rows, "每条用例至少关联一个需求编号", f"以下用例未关联需求：{empty_req_rows}")

    # 9. 分层约束：页面/核心层无断言，测试层无定位器字面量
    assertion_files = []
    for folder in (CORE_DIR, PAGES_DIR):
        for path in sorted(folder.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            if any(isinstance(node, ast.Assert) for node in ast.walk(tree)):
                assertion_files.append(path.relative_to(ROOT).as_posix())
    check(not assertion_files, "core/ 与 pages/ 无断言（断言只在测试层）", f"以下非测试文件含断言：{assertion_files}")

    locator_tokens = ("find_element", "find_elements", "By.", "xpath", "css selector")
    locator_files = []
    for path in sorted(TEST_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        if any(token in source for token in locator_tokens):
            locator_files.append(path.relative_to(ROOT).as_posix())
    check(not locator_files, "tests/ 无定位器字面量与 find_element 调用", f"测试层出现定位器细节：{locator_files}")

    for message in passes:
        print(f"[PASS] {message}")
    for message in failures:
        print(f"[FAIL] {message}")
    total = len(passes) + len(failures)
    print(f"\n检查项 {total}：通过 {len(passes)}，失败 {len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
