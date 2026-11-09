#!/usr/bin/env python3
"""C 组：DHCP 地址池（scope）设计。

依据《奉贤校区校园网设计方案》与 campus-lab 仿真工程的既有约定：

- 每个业务 VLAN 一个地址池，地址池落在该 VLAN 的 /24 子网内；
- 动态范围统一 .100-200，.1-.11 保留给网关、服务器、AP、静态终端；
- 租期按区域区分：宿舍 12 小时、教学 4 小时、实验 8 小时、图书馆/生活区 8 小时；
- 网关由本 VLAN 的 VRRP 虚拟地址下发，DNS 统一下发数据中心 10.60.0.10；
- 子网与网关来自 tools/c_address_plan.py，保证地址表与地址池同源。

本脚本只依赖标准库：

    python3 tools/c_dhcp_plan.py            # 汇总与冲突检查
    python3 tools/c_dhcp_plan.py --md       # 输出 Markdown 地址池表
    python3 tools/c_dhcp_plan.py --csv      # 输出 CSV
    python3 tools/c_dhcp_plan.py --relay    # 输出每台汇聚的 Relay 地址清单

退出码：0 检查通过，1 存在冲突。
"""
from __future__ import annotations

import argparse
import csv
import io
import ipaddress
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import c_address_plan as cap  # noqa: E402

# ---------------------------------------------------------------- 设计参数
DHCP_SERVER = "10.60.0.10"          # 与 campus-lab/gen.py 的 DHCP_SERVER 一致
DHCP_DNS = "10.60.0.10"             # 与 campus-lab/gen.py 的 DHCP_DNS 一致
DYNAMIC_START = 100
DYNAMIC_END = 200
RESERVED_TOP = 11                   # .1-.11 保留：网关 .1、汇聚 .252/.253、服务器、AP

# 租期（秒），与 campus-lab/gen.py 的 LEASE_BY_REGION 一致
LEASE_BY_REGION = {
    "宿舍区": 43200,     # 12 小时：宿舍终端在线时间长
    "教学区": 14400,     # 4 小时：教室终端流动性高
    "实验区": 28800,     # 8 小时
    "图书馆": 28800,
    "生活区": 28800,
}

# 不参与动态分配的功能网段（固定地址或由其他机制管理）
EXCLUDED = {
    "数据中心": "服务器使用静态地址，DHCP 服务器本身就在该网段",
    "网络中心": "管理网不得由 DHCP 动态分配",
    "出口": "DMZ 服务器使用静态地址",
}

# 地址池数量：48 个子网扣除数据中心、管理网、DMZ 3 个静态网段后为 45 个；
# 生活区三栋楼共用 10.64.0.0/24，只保留 VLAN 61 一个池（VLAN 62/63 不单独建池）。
EXPECTED_POOLS = 45


@dataclass(frozen=True)
class Pool:
    name: str            # 池名，如 v101
    vlan: int
    region: str
    subnet: ipaddress.IPv4Network
    gateway: str
    start: ipaddress.IPv4Address
    end: ipaddress.IPv4Address
    lease: int
    scope: str           # 覆盖范围说明（单栋楼 / 整区）

    def as_dict(self) -> dict:
        return {
            "池名": self.name,
            "VLAN": self.vlan,
            "区域": self.region,
            "覆盖范围": self.scope,
            "子网": str(self.subnet),
            "网关（VRRP）": self.gateway,
            "DHCP 服务器": DHCP_SERVER,
            "DNS": DHCP_DNS,
            "动态范围": f"{self.start} - {self.end}",
            "可用地址数": int(self.end) - int(self.start) + 1,
            "保留段": f".1-.{RESERVED_TOP}",
            "租期": self.lease,
            "租期（小时）": self.lease / 3600,
        }


# ---------------------------------------------------------------- 生成地址池
def _pool_name(vlan: int) -> str:
    return f"v{vlan}"


# 无线池的租期跟随其服务区域（与 campus-lab/gen.py 的 region 字段一致）
WIRELESS_LEASE_REGION = {
    500: "教学区",   # 教学、图书馆、信息楼无线
    510: "宿舍区",   # 宿舍、实验区无线
}


def _lease_region(row: cap.Row) -> str:
    if row.region == "无线":
        return WIRELESS_LEASE_REGION.get(row.vlan, "教学区")
    return row.region


def build_pools() -> list[Pool]:
    """每个参与动态分配的子网一个池；无线池覆盖整个区域。

    生活区三栋楼共用 10.64.0.0/24，只生成一个池（v61），
    以生活区汇聚的网关 10.64.0.1 下发，避免同一子网出现三份地址池。
    """
    pools: list[Pool] = []
    living_done = False
    for row in cap.all_rows():
        if row.region in EXCLUDED:
            continue
        if row.region == "生活区":
            if living_done:
                continue
            living_done = True
            scope = "食堂1、食堂2、体育馆（共用 10.64.0.0/24）"
        elif row.region == "无线":
            scope = f"{row.building}（{row.subnet} 范围内全部 AP）"
        else:
            scope = row.building
        subnet = row.subnet
        start, end = subnet[DYNAMIC_START], subnet[DYNAMIC_END]
        lease_region = _lease_region(row)
        pools.append(Pool(
            name=_pool_name(row.vlan),
            vlan=row.vlan,
            region=row.region,
            subnet=subnet,
            gateway=row.gateway,
            start=start,
            end=end,
            lease=LEASE_BY_REGION[lease_region],
            scope=scope,
        ))
    return pools


# ---------------------------------------------------------------- 检查
def check(pools: list[Pool], rows: list[cap.Row]) -> list[str]:
    errors: list[str] = []

    # 1. 池数量与预期一致
    if len(pools) != EXPECTED_POOLS:
        errors.append(f"地址池 {len(pools)} 个，期望 {EXPECTED_POOLS}")

    # 2. 池名唯一（VLAN 唯一 ⇒ 池名唯一）
    seen: dict[str, int] = {}
    for p in pools:
        if p.name in seen:
            errors.append(f"池名重复：{p.name}（VLAN {seen[p.name]} 与 {p.vlan}）")
        seen[p.name] = p.vlan

    # 3. 每个池的网段必须来自地址规划表
    planning = {r.vlan: r.subnet for r in rows}
    for p in pools:
        if p.vlan not in planning:
            errors.append(f"{p.name} 的 VLAN {p.vlan} 不在地址规划中")
        elif planning[p.vlan] != p.subnet:
            errors.append(f"{p.name} 网段 {p.subnet} 与地址规划 {planning[p.vlan]} 不一致")

    # 4. 网关与地址规划一致
    gateways = {r.vlan: r.gateway for r in rows}
    for p in pools:
        if p.vlan in gateways and gateways[p.vlan] != p.gateway:
            errors.append(f"{p.name} 网关 {p.gateway} 与规划的 {gateways[p.vlan]} 不一致")

    # 5. 动态范围在子网内、不覆盖保留段、不越界
    for p in pools:
        if p.start not in p.subnet or p.end not in p.subnet:
            errors.append(f"{p.name} 动态范围 {p.start}-{p.end} 不在 {p.subnet} 内")
            continue
        if int(p.start) > int(p.end):
            errors.append(f"{p.name} 动态范围起止颠倒")
        reserved_last = p.subnet[RESERVED_TOP]
        if int(p.start) <= int(reserved_last):
            errors.append(f"{p.name} 动态范围覆盖保留段 .1-.{RESERVED_TOP}")
        if int(p.end) >= int(p.subnet.broadcast_address):
            errors.append(f"{p.name} 动态范围覆盖广播地址")

    # 6. 租期按区域取值（无线池跟随其服务区域）
    for p in pools:
        expected_lease = LEASE_BY_REGION.get(p.region)
        if expected_lease is None and p.region == "无线":
            expected_lease = LEASE_BY_REGION[WIRELESS_LEASE_REGION.get(p.vlan, "教学区")]
        if expected_lease is not None and p.lease != expected_lease:
            errors.append(f"{p.name} 租期 {p.lease} 与区域约定的 {expected_lease} 不一致")

    # 7. 池之间不得重叠；生活区三栋楼共用 10.64.0.0/24 属有意设计，
    #    但共用子网的多个 VLAN 只能有一份动态地址池（由生活区汇聚统一网关分配）。
    seen_living: set[ipaddress.IPv4Network] = set()
    for i, a in enumerate(pools):
        for b in pools[i + 1:]:
            if not a.subnet.overlaps(b.subnet):
                continue
            if a.subnet == b.subnet == cap.LIVING_AREA_BASE:
                errors.append(
                    f"生活区共用子网出现多个地址池：{a.name} 与 {b.name}，"
                    "应只保留一个池")
                continue
            errors.append(f"池网段重叠：{a.name} {a.subnet} 与 {b.name} {b.subnet}")

    # 8. DHCP 服务器与 DNS 地址可达性前提：服务器地址不在任何动态范围里
    for p in pools:
        if p.subnet == ipaddress.ip_network(f"{DHCP_SERVER}/24", strict=False):
            errors.append(f"{p.name} 的动态范围会与 DHCP 服务器 {DHCP_SERVER} 冲突")

    # 9. 与 campus-lab 已生成的 dnsmasq 配置逐条比对（若存在）。
    #    这是"设计 vs 实现"的一致性检查：不一致会出现在 errors 里，
    #    必须由 A 决定是改设计还是改 gen.py，不能在这一步静默放过。
    live = _simulation_ranges()
    if live:
        errors.extend(_compare_with_simulation(pools, live))

    return errors


SIM_DNSMASQ = (Path(__file__).resolve().parents[1]
               / "campus-lab" / "configs" / "hosts" / "srv-dc1" / "dnsmasq.conf")


def _simulation_ranges() -> dict[str, tuple[str, str, int]]:
    """读取 campus-lab 生成的 dnsmasq 配置，返回 {池名: (start, end, lease)}。"""
    import re
    if not SIM_DNSMASQ.exists():
        return {}
    out: dict[str, tuple[str, str, int]] = {}
    pattern = re.compile(r"^dhcp-range=set:(v\d+),([\d.]+),([\d.]+),[\d.]+,(\d+)$")
    for line in SIM_DNSMASQ.read_text(encoding="utf-8").splitlines():
        m = pattern.match(line.strip())
        if m:
            out[m.group(1)] = (m.group(2), m.group(3), int(m.group(4)))
    return out


def _compare_with_simulation(pools: list[Pool],
                             live: dict[str, tuple[str, str, int]]) -> list[str]:
    errors: list[str] = []
    by_name = {p.name: p for p in pools}
    for name, (start, end, lease) in sorted(live.items()):
        p = by_name.get(name)
        if p is None:
            errors.append(f"仿真存在地址池 {name}，设计中没有")
            continue
        if str(p.start) != start or str(p.end) != end:
            errors.append(
                f"{name} 动态范围不一致：仿真 {start}-{end}，设计 {p.start}-{p.end}")
        if p.lease != lease:
            errors.append(f"{name} 租期不一致：仿真 {lease}，设计 {p.lease}")
    return errors


def capacity_summary(pools: list[Pool]) -> str:
    lines = [f"地址池 {len(pools)} 个，动态地址合计 {sum(p.as_dict()['可用地址数'] for p in pools)} 个"]
    by_lease: dict[int, list[Pool]] = {}
    for p in pools:
        by_lease.setdefault(p.lease, []).append(p)
    for lease, ps in sorted(by_lease.items()):
        lines.append(f"  租期 {lease}s（{lease // 3600}h）：{len(ps)} 个池")
    return "\n".join(lines)


FIELDS = ["池名", "VLAN", "区域", "覆盖范围", "子网", "网关（VRRP）", "DHCP 服务器",
          "DNS", "动态范围", "可用地址数", "保留段", "租期", "租期（小时）"]


def to_markdown(pools: list[Pool]) -> str:
    out = ["| " + " | ".join(FIELDS) + " |",
           "| " + " | ".join(["---"] * len(FIELDS)) + " |"]
    for p in pools:
        d = p.as_dict()
        out.append("| " + " | ".join(str(d[f]) for f in FIELDS) + " |")
    return "\n".join(out) + "\n"


def to_csv(pools: list[Pool]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(p.as_dict() for p in pools)
    return buf.getvalue()


def relay_summary(pools: list[Pool]) -> str:
    """每台区域汇聚需要配置的 Relay giaddr 与目标服务器。

    汇聚与 VLAN 的对应关系与 campus-lab/gen.py 一致：
    agg-t1: 101/500/102, agg-d1: 301/510, agg-l1: 201,
    agg-lib1: 50, agg-life1: 61
    """
    relays = {
        "agg-t1 / agg-t2": [101, 102, 500],
        "agg-d1 / agg-d2": [301, 510],
        "agg-l1 / agg-l2": [201],
        "agg-lib1 / agg-lib2": [50],
        "agg-life1 / agg-life2": [61],
    }
    by_vlan = {}
    for p in pools:
        by_vlan.setdefault(p.vlan, []).append(p)
    lines = [f"DHCP Relay 目标服务器：{DHCP_SERVER}", ""]
    for agg, vlans in relays.items():
        lines.append(f"{agg}")
        for v in vlans:
            for p in by_vlan.get(v, []):
                # dnsmasq relay 的 giaddr 使用汇聚 SVI 真实地址（.252/.253），
                # 服务器按 giaddr 所在网段选择地址池。
                lines.append(f"  VLAN {v}: giaddr {p.subnet[252]} → {DHCP_SERVER}")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成 DHCP 地址池设计并检查")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--md", action="store_true", help="输出 Markdown 地址池表")
    group.add_argument("--csv", action="store_true", help="输出 CSV")
    group.add_argument("--relay", action="store_true", help="输出 Relay 配置清单")
    args = parser.parse_args(argv)

    rows = cap.all_rows()
    pools = build_pools()
    errors = check(pools, rows)

    if args.md:
        sys.stdout.write(to_markdown(pools))
    elif args.csv:
        sys.stdout.write(to_csv(pools))
    elif args.relay:
        sys.stdout.write(relay_summary(pools))
    else:
        print(capacity_summary(pools))

    if errors:
        print("\n检查失败：", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    if not (args.md or args.csv or args.relay):
        print("检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
