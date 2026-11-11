#!/usr/bin/env python3
"""Check course report facts block and section coverage against facts.json.

另含 C 组的两项一致性检查：
- 报告 4.2 的 VLAN 表与 tools/c_address_plan.py 的地址规划逐行一致；
- 报告中的 DHCP 池数量与 tools/c_dhcp_plan.py 一致（仿真 8 个池）。
"""
from __future__ import annotations

import ipaddress
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTS_PATH = ROOT / "campus-lab" / "configs" / "facts.json"
REPORT_PATH = ROOT / "docs" / "course-report-draft.md"
REQUIRED_SECTIONS = [str(i) for i in range(1, 9)]
REQUIRED_CASES = ["DHCP", "ISO", "NAT", "LAG", "FAIL", "WIRELESS", "RATE"]
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


DHCP_RANGE_RE = re.compile(r"^\s*dhcp-range=set:v(\d+),([\d.]+),([\d.]+),[\d.]+,(\d+)\s*$")


def check_dhcp_example(text: str, facts: dict) -> list[str]:
    """7.2 的 dnsmasq 配置示例必须与 facts.json 的池定义一致。"""
    errors: list[str] = []
    section = re.search(r"^#### 7\.2\.4 .*?(?=^#### 7\.2\.5 )",
                        text, re.MULTILINE | re.DOTALL)
    if not section:
        return ["missing section: 7.2.4"]

    pools = {p["vid"]: p for p in facts["dhcp"]["pools"]}
    found = 0
    for line in section.group(0).splitlines():
        m = DHCP_RANGE_RE.match(line)
        if not m:
            continue
        found += 1
        vid, start, end, lease = int(m.group(1)), m.group(2), m.group(3), int(m.group(4))
        pool = pools.get(vid)
        if pool is None:
            errors.append(f"7.2 配置示例中的 VLAN {vid} 不在仿真池定义中")
            continue
        if (pool["start"], pool["end"], pool["lease"]) != (start, end, lease):
            errors.append(
                f"7.2 VLAN {vid} 示例与仿真不一致："
                f"示例 {start}-{end}/{lease}s，仿真 "
                f"{pool['start']}-{pool['end']}/{pool['lease']}s")

    if found == 0:
        errors.append("7.2.4 未找到 dhcp-range 配置示例")
    return errors


def check_relay_example(text: str, facts: dict) -> list[str]:
    """7.2 的 Relay 示例必须指向真实的 DHCP 服务器，且 giaddr 在已规划的 SVI 网段内。"""
    import c_address_plan as cap

    section = re.search(r"^#### 7\.2\.4 .*?(?=^#### 7\.2\.5 )",
                        text, re.MULTILINE | re.DOTALL)
    if not section:
        return []
    server = facts["dhcp"]["server"]
    pairs = re.findall(r"dhcp-relay=([\d.]+),([\d.]+)", section.group(0))
    if not pairs:
        return ["7.2.4 未找到 dhcp-relay 配置示例"]

    errors: list[str] = []
    planned = [r.subnet for r in cap.all_rows()]
    for giaddr, target in pairs:
        if target != server:
            errors.append(f"7.2 Relay 目标 {target} 与实际服务器 {server} 不一致")
        if not any(ipaddress.ip_address(giaddr) in net for net in planned):
            errors.append(f"7.2 Relay giaddr {giaddr} 不在任何已规划网段内")
    return errors


def check_dns_section(text: str) -> list[str]:
    """5.3.6 的 DNS 服务器表必须与 c_dns_plan 一致。"""
    import c_dns_plan as dns

    section = re.search(r"^#### 5\.3\.6 .*?(?=^#### 5\.3\.7 )",
                        text, re.MULTILINE | re.DOTALL)
    if not section:
        return ["missing section: 5.3.6"]
    servers = {s.name: s for s in dns.build_servers()}
    errors: list[str] = []
    rows = re.findall(r"^\|\s*(srv-[a-z0-9]+)\s*\|[^|\n]*\|\s*([\d.]+)\s*\|",
                      section.group(0), re.MULTILINE)
    if len(rows) != len(servers):
        errors.append(f"5.3.6 列出 {len(rows)} 台 DNS，设计为 {len(servers)} 台")
    for name, ip in rows:
        server = servers.get(name)
        if server is None:
            errors.append(f"5.3.6 中的 {name} 不在 DNS 设计中")
        elif server.ip != ip:
            errors.append(f"5.3.6 {name} 地址 {ip} 与设计 {server.ip} 不一致")
    return errors


def check_auth_section(text: str) -> list[str]:
    """5.3.7 的认证表必须与 c_8021x_plan 一致（场景数与无线 VLAN）。"""
    import c_8021x_plan as auth

    section = re.search(r"^#### 5\.3\.7 .*?(?=^### 5\.4 )",
                        text, re.MULTILINE | re.DOTALL)
    if not section:
        return ["missing section: 5.3.7"]
    errors: list[str] = []
    rules = auth.build_rules()
    for r in rules:
        # 每个设计场景必须在报告表格中出现（按场景名精确匹配单元格）
        if not re.search(rf"^\|\s*{re.escape(r.scenario)}\s*\|", section.group(0), re.MULTILINE):
            errors.append(f"5.3.7 缺少认证场景「{r.scenario}」")
        if r.ssid != "—" and f"| {r.ssid} |" not in section.group(0):
            errors.append(f"5.3.7 缺少 SSID {r.ssid}")
    for vlan in ("500", "510", "999"):
        if vlan not in section.group(0):
            errors.append(f"5.3.7 缺少 VLAN {vlan}")
    return errors


def check_pool_table(text: str, facts: dict) -> list[str]:
    """7.2.4 的完整池定义表必须与 facts.json 的 8 个池逐条一致。"""
    section = re.search(r"^#### 7\.2\.4 .*?(?=^#### 7\.2\.5 )",
                        text, re.MULTILINE | re.DOTALL)
    if not section:
        return []
    pools = {p["vid"]: p for p in facts["dhcp"]["pools"]}
    rows = re.findall(
        r"^\|\s*v(\d+)\s*\|\s*\d+\s*\|\s*([\d.]+)[–-]([\d.]+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)\s*\|",
        section.group(0), re.MULTILINE)
    if len(rows) != len(pools):
        return [f"7.2.4 完整池表 {len(rows)} 行，仿真实际 {len(pools)} 个池"]
    errors: list[str] = []
    for vid_s, start, end, lease, gw in rows:
        vid = int(vid_s)
        p = pools.get(vid)
        if p is None:
            errors.append(f"7.2.4 池 v{vid} 不在仿真定义中")
            continue
        if (p["start"], p["end"], p["lease"], p["gateway"]) != (start, end, int(lease), gw):
            errors.append(f"7.2.4 池 v{vid} 与仿真定义不一致")
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
    errors.extend(check_dhcp_example(text, facts))
    errors.extend(check_relay_example(text, facts))
    errors.extend(check_dns_section(text))
    errors.extend(check_auth_section(text))
    errors.extend(check_pool_table(text, facts))

    if errors:
        for error in errors:
            print("FAIL", error)
        return 1
    print("report check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())