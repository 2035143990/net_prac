#!/usr/bin/env python3
"""C 组：802.1X / Portal 认证与 RADIUS 动态 VLAN 设计。

依据《奉贤校区校园网设计方案》6.3 / 6.5 / 6.6 与 8.2 实验七：

- 有线接入使用 802.1X（EAP），无线 SSID 按角色分别使用 802.1X 或 Portal；
- 认证服务器为 RADIUS，主备 2 台，部署在数据中心；
- 认证通过后由 RADIUS 下发 VLAN（动态 VLAN），未认证终端进入隔离 VLAN；
- 认证前后的 VLAN 变化是实验七的验收证据。

VLAN 与网段：

- 有线认证通过后进入该楼栋的业务 VLAN（101-105 / 201-208 / 301-328 / 50 / 61-63）；
- 无线认证通过后进入 500（教学/图书馆/信息楼）或 510（宿舍/实验）；
- 未认证 / 认证失败 / 访客终端进入隔离 VLAN 999（10.71.0.0/24），
  只能访问 DHCP、DNS 与认证服务器，不能访问任何业务网段。

本设计不修改仿真工程（仿真目前未建模 802.1X），
差距会在输出中显式列出。

用法：

    python3 tools/c_8021x_plan.py           # 汇总与一致性检查
    python3 tools/c_8021x_plan.py --md      # 输出 Markdown
    python3 tools/c_8021x_plan.py --rules   # 输出 RADIUS 返回属性表

退出码：0 检查通过，1 存在不一致。
"""
from __future__ import annotations

import argparse
import ipaddress
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import c_address_plan as cap  # noqa: E402

# ---------------------------------------------------------------- 基础参数
# 与仿真/其余设计保持一致
DHCP_SERVER = "10.60.0.10"
DNS_SERVER = "10.60.0.10"

# 认证隔离 VLAN（设计方案 5.2 的 VLAN 999），网段取空闲的 10.71.0.0/24
ISOLATION_VLAN = 999
ISOLATION_SUBNET = "10.71.0.0/24"
ISOLATION_GATEWAY = "10.71.0.1"

# RADIUS 服务器（主备，数据中心）
RADIUS_SERVERS = [
    ("radius1", "10.60.0.21"),
    ("radius2", "10.60.0.22"),
]
RADIUS_SHARED_SECRET = "REDACTED-placeholder"   # 实际密钥不入库，由运维单独保管

# 认证方法：按终端类型
AUTH_METHODS = {
    "有线-教职工": "802.1X（PEAP-MSCHAPv2，域账号）",
    "有线-学生": "802.1X（EAP-TLS 或 PEAP），失败后回落 Portal",
    "无线-教职工": "802.1X（ECUST-EDU）",
    "无线-学生": "802.1X（ECUST-STU，支持漫游）",
    "无线-访客": "Portal（ECUST-GUEST，临时账号，限时限速）",
    "有线-访客": "Portal（临时账号）",
}


@dataclass(frozen=True)
class AuthRule:
    scenario: str            # 认证场景
    ssid: str                # 无线 SSID；有线为 "—"
    method: str              # 认证方式
    pre_vlan: int            # 认证前 VLAN
    pre_subnet: str
    post_vlan: str           # 认证后 VLAN（可能是具体值或范围说明）
    post_subnet: str
    radius_attrs: tuple[str, ...]   # RADIUS 下发的属性

    def as_dict(self) -> dict:
        return {
            "场景": self.scenario,
            "SSID": self.ssid,
            "认证方式": self.method,
            "认证前 VLAN": self.pre_vlan,
            "认证前网段": self.pre_subnet,
            "认证后 VLAN": self.post_vlan,
            "认证后网段": self.post_subnet,
            "RADIUS 下发属性": "; ".join(self.radius_attrs) or "—",
        }


def build_rules() -> list[AuthRule]:
    """认证流程：接入端口初始在隔离 VLAN，认证通过后由 RADIUS 下发业务 VLAN。"""
    iso = ISOLATION_SUBNET
    common = (f"Tunnel-Type=VLAN", "Tunnel-Medium-Type=IEEE-802",
              "Egress-VLAN-Name")
    return [
        AuthRule("有线-教职工", "—", AUTH_METHODS["有线-教职工"],
                 ISOLATION_VLAN, iso, "对应楼栋业务 VLAN", "对应楼栋 /24",
                 common + ("Filter-Id=teacher",)),
        AuthRule("有线-学生", "—", AUTH_METHODS["有线-学生"],
                 ISOLATION_VLAN, iso, "对应楼栋业务 VLAN", "对应楼栋 /24",
                 common + ("Filter-Id=student",)),
        AuthRule("无线-教职工", "ECUST-EDU", AUTH_METHODS["无线-教职工"],
                 ISOLATION_VLAN, iso, "500", "10.50.0.0/24",
                 common + ("Egress-VLAN-ID=500", "Filter-Id=teacher")),
        AuthRule("无线-学生", "ECUST-STU", AUTH_METHODS["无线-学生"],
                 ISOLATION_VLAN, iso, "510", "10.51.0.0/24",
                 common + ("Egress-VLAN-ID=510", "Filter-Id=student",
                           "Session-Timeout=86400")),
        AuthRule("无线-访客", "ECUST-GUEST", AUTH_METHODS["无线-访客"],
                 ISOLATION_VLAN, iso, f"{ISOLATION_VLAN}（限时）", iso,
                 common + ("Egress-VLAN-ID=999", "Session-Timeout=28800",
                           "Filter-Id=guest", "Mikrotik-Rate-Limit=10M/10M")),
        AuthRule("有线-访客", "—", AUTH_METHODS["有线-访客"],
                 ISOLATION_VLAN, iso, f"{ISOLATION_VLAN}（限时）", iso,
                 common + ("Egress-VLAN-ID=999", "Session-Timeout=7200",
                           "Filter-Id=guest")),
    ]


# ---------------------------------------------------------------- 检查
def check(rules: list[AuthRule]) -> list[str]:
    errors: list[str] = []

    # 1. 隔离 VLAN 网段必须空闲，且不与地址规划表交叠
    iso_net = ipaddress.ip_network(ISOLATION_SUBNET)
    for row in cap.all_rows():
        if row.subnet.overlaps(iso_net):
            errors.append(f"隔离 VLAN 网段 {ISOLATION_SUBNET} 与 {row.building} {row.subnet} 交叠")
    if ISOLATION_VLAN in {r.vlan for r in cap.all_rows()}:
        errors.append(f"VLAN {ISOLATION_VLAN} 已在地址规划中使用")

    # 2. 隔离网关必须在隔离网段内且为 .1
    gw = ipaddress.ip_address(ISOLATION_GATEWAY)
    if gw not in iso_net:
        errors.append(f"隔离网关 {ISOLATION_GATEWAY} 不在 {ISOLATION_SUBNET}")
    elif gw != iso_net[1]:
        errors.append(f"隔离网关应为 {iso_net[1]}")

    # 3. RADIUS 服务器地址在数据中心网段内、不在 DHCP 动态范围、不重复
    dc = next(r.subnet for r in cap.all_rows() if r.building == "数据中心服务器")
    seen: set[str] = set()
    for name, ip in RADIUS_SERVERS:
        addr = ipaddress.ip_address(ip)
        if addr not in dc:
            errors.append(f"{name} {ip} 不在数据中心 {dc}")
        if ip in seen:
            errors.append(f"RADIUS 地址重复 {ip}")
        seen.add(ip)
        if 100 <= int(ip.split(".")[-1]) <= 200:
            errors.append(f"{name} {ip} 落在 DHCP 动态范围 .100-.200")

    # 4. RADIUS 主备齐全
    if len(RADIUS_SERVERS) < 2:
        errors.append("RADIUS 应为双机主备，当前不足 2 台")

    # 5. 每个场景都必须从不认证状态出发（认证前为隔离 VLAN）
    for r in rules:
        if r.pre_vlan != ISOLATION_VLAN:
            errors.append(f"{r.scenario} 认证前 VLAN 应为隔离 VLAN {ISOLATION_VLAN}")

    # 6. 认证后不得仍停留在隔离 VLAN（访客例外，属于限时隔离准入）
    for r in rules:
        if "访客" not in r.scenario and str(ISOLATION_VLAN) in r.post_vlan:
            errors.append(f"{r.scenario} 认证后不应仍在隔离 VLAN")

    # 7. 认证后 VLAN 必须存在于地址规划
    planning_vlans = {r.vlan for r in cap.all_rows()}
    for r in rules:
        if r.post_vlan.isdigit():
            if int(r.post_vlan) not in planning_vlans:
                errors.append(f"{r.scenario} 认证后 VLAN {r.post_vlan} 不在地址规划中")

    # 8. 无线认证后 VLAN 必须与设计稿 6.5 的 SSID 表一致
    expected_ssid_vlan = {"ECUST-EDU": "500", "ECUST-STU": "510"}
    for r in rules:
        if r.ssid in expected_ssid_vlan:
            if r.post_vlan != expected_ssid_vlan[r.ssid]:
                errors.append(
                    f"SSID {r.ssid} 认证后应进入 VLAN {expected_ssid_vlan[r.ssid]}，实际 {r.post_vlan}")

    # 9. 每个场景必须下发 VLAN 类属性
    for r in rules:
        if not any("VLAN" in a for a in r.radius_attrs):
            errors.append(f"{r.scenario} 未下发 VLAN 属性，动态 VLAN 不成立")

    return errors


def simulation_gaps() -> list[str]:
    return [
        "仿真未建模 802.1X / RADIUS：gen.py 中没有 dot1x、radius 或 ACL 认证动作",
        "VLAN 999 隔离网段未在 campus-lab 中生成，实验七需要新增隔离 VLAN 与其 ACL",
        "实验七为加分项，风险表已标注“时间紧时后补”",
    ]


FIELDS = ["场景", "SSID", "认证方式", "认证前 VLAN", "认证前网段",
          "认证后 VLAN", "认证后网段", "RADIUS 下发属性"]


def to_markdown(rules: list[AuthRule]) -> str:
    out = ["| " + " | ".join(FIELDS) + " |",
           "| " + " | ".join(["---"] * len(FIELDS)) + " |"]
    for r in rules:
        d = r.as_dict()
        out.append("| " + " | ".join(str(d[f]) for f in FIELDS) + " |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成 802.1X/RADIUS 认证设计并检查")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--md", action="store_true", help="输出 Markdown 认证规则表")
    group.add_argument("--rules", action="store_true", help="输出 RADIUS 属性表")
    args = parser.parse_args(argv)

    rules = build_rules()
    errors = check(rules)

    if args.md:
        sys.stdout.write(to_markdown(rules))
    elif args.rules:
        for r in rules:
            print(f"[{r.scenario}] {r.method}")
            for a in r.radius_attrs:
                print(f"    {a}")
    else:
        print(f"认证场景 {len(rules)} 个，RADIUS {len(RADIUS_SERVERS)} 台")
        print(f"隔离 VLAN {ISOLATION_VLAN}：{ISOLATION_SUBNET}，网关 {ISOLATION_GATEWAY}")
        print("\n仿真差距：")
        for g in simulation_gaps():
            print(f"  - {g}")

    if errors:
        print("\n检查失败：", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    if not (args.md or args.rules):
        print("\n检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
