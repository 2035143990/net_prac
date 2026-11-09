#!/usr/bin/env python3
"""Check course report facts block and section coverage against facts.json.

另含 C 组的两项一致性检查：
- 报告 4.2 的 VLAN 表与 tools/c_address_plan.py 的地址规划逐行一致；
- 报告中的 DHCP 池数量与 tools/c_dhcp_plan.py 一致（仿真 8 个池）。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTS_PATH = ROOT / "campus-lab" / "configs" / "facts.json"
REPORT_PATH = ROOT / "docs" / "course-report-draft.md"
REQUIRED_SECTIONS = [str(i) for i in range(1, 9)]
REQUIRED_CASES = ["DHCP", "ISO", "NAT", "LAG", "FAIL"]
REQUIRED_LABELS = ["摘要", "关键词", "参考文献"]

sys.path.insert(0, str(ROOT / "tools"))


def expected_block(facts: dict) -> dict[str, str]:
    return {
        "nodes": str(facts["nodes"]["total"]),
        "links": str(facts["links"]),
        "vlans": ",".join(str(v) for v in sorted(facts["vlans"])),
        "mgmt_vlan": str(facts["mgmt_vlan"]),
        "dhcp_pools": str(len(facts["dhcp"]["pools"])),
        "nat_publish": ",".join(item["public"] for item in facts["nat"]["publish"]),
        "lags": ",".join(item["name"] for item in facts["lags"]),
    }


def check_vlan_table(text: str) -> list[str]:
    """报告 4.2 的 VLAN 表必须与地址规划同源（按 VLAN 号比对网段与网关）。"""
    import c_address_plan as cap

    errors: list[str] = []
    section = re.search(r"^### 4\.2 .*?(?=^### 4\.3 )", text, re.MULTILINE | re.DOTALL)
    if not section:
        return ["missing section: 4.2"]

    rows = re.findall(r"^\|\s*(\d+)\s*\|[^|\n]*\|\s*(\d+\.\d+\.\d+\.\d+/\d+)\s*\|"
                      r"\s*(\d+\.\d+\.\d+\.\d+)\s*\|", section.group(0), re.MULTILINE)
    if not rows:
        return ["4.2 未找到 VLAN 表行（格式：| VLAN | 用途 | 网段 | 网关 VIP |）"]

    plan = {r.vlan: r for r in cap.all_rows()}
    for vlan_s, subnet, gateway in rows:
        vlan = int(vlan_s)
        r = plan.get(vlan)
        if r is None:
            errors.append(f"4.2 VLAN {vlan} 不在地址规划中")
            continue
        if str(r.subnet) != subnet:
            errors.append(f"4.2 VLAN {vlan} 网段 {subnet} 与规划 {r.subnet} 不一致")
        if r.gateway != gateway:
            errors.append(f"4.2 VLAN {vlan} 网关 {gateway} 与规划 {r.gateway} 不一致")
    return errors


def check_dhcp_count(text: str, facts: dict) -> list[str]:
    """报告 4.2 声明的 DHCP 池数量必须与 facts.json 一致。"""
    errors: list[str] = []
    claimed = re.search(r"DHCP 共\s*(\d+)\s*个动态池", text)
    if not claimed:
        return ["4.2 未声明 DHCP 动态池数量（格式：DHCP 共 N 个动态池）"]
    actual = len(facts["dhcp"]["pools"])
    if int(claimed.group(1)) != actual:
        errors.append(f"4.2 声明 {claimed.group(1)} 个动态池，仿真实际 {actual} 个")
    return errors


def main() -> int:
    if not FACTS_PATH.exists():
        print(f"missing facts: {FACTS_PATH}")
        return 2
    if not REPORT_PATH.exists():
        print(f"missing report: {REPORT_PATH}")
        return 2
    facts = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    text = REPORT_PATH.read_text(encoding="utf-8")

    block = re.search(r"<!-- facts:begin -->(.*?)<!-- facts:end -->", text, re.DOTALL)
    if not block:
        print("missing facts block")
        return 1
    actual: dict[str, str] = {}
    for line in block.group(1).strip().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            actual[key.strip()] = value.strip()
    expected = expected_block(facts)

    errors = []
    for key, value in expected.items():
        if key not in actual:
            errors.append(f"facts missing key: {key}")
        elif actual[key] != value:
            errors.append(f"facts mismatch {key}: report={actual[key]} facts={value}")
    for key in actual:
        if key not in expected:
            errors.append(f"facts unknown key: {key}")

    headings = set(re.findall(r"^## (\d+) ", text, re.MULTILINE))
    for section in REQUIRED_SECTIONS:
        if section not in headings:
            errors.append(f"missing section: {section}")

    for label in REQUIRED_LABELS:
        if label not in text:
            errors.append(f"missing required label: {label}")

    for prefix in REQUIRED_CASES:
        if not re.search(rf"\b{prefix}-\d{{2}}\b", text):
            errors.append(f"missing test case reference: {prefix}-xx")

    for ref in re.findall(r"!\[[^\]]*\]\((figures/[^)]+)\)", text):
        if not (REPORT_PATH.parent / ref).exists():
            errors.append(f"missing figure: {ref}")

    errors.extend(check_vlan_table(text))
    errors.extend(check_dhcp_count(text, facts))

    if errors:
        for error in errors:
            print("FAIL", error)
        return 1
    print("report check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())