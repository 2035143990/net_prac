#!/usr/bin/env python3
"""C 组：DNS 规划（内外分设）。

依据《奉贤校区校园网设计方案》6.4 / 7.5：

- DNS 内外分设：
  * 内部 DNS：部署在数据中心，承担校内域名的权威解析 + 校内终端递归解析；
  * 外部 DNS：部署在 DMZ，承担对外域名的权威解析，外网可查但不暴露内部记录；
- 主备 2 台（数据中心 2 + DMZ 2，共 4 台）；
- 校内终端由 DHCP 下发内部 DNS 地址；对外发布域由外部 DNS 响应；
- 仿真工程当前只有一台 srv-dc1 提供 DNS（10.60.0.10），
  DMZ 侧与备用节点未建模，属于"设计覆盖、仿真未实现"，本工具会显式标出。

用法：

    python3 tools/c_dns_plan.py            # 汇总与一致性检查
    python3 tools/c_dns_plan.py --md       # 输出 Markdown 规划表
    python3 tools/c_dns_plan.py --csv      # 输出 CSV

退出码：0 检查通过，1 存在不一致。
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

# ---------------------------------------------------------------- 基础参数
# 与 campus-lab/gen.py 保持一致
DHCP_DNS = "10.60.0.10"          # 仿真中 DHCP 下发的 DNS
DC_SUBNET = "10.60.0.0/24"       # 数据中心
DMZ_SUBNET = "10.80.0.0/24"      # DMZ
# 已被仿真或其他设计占用的地址，DNS 不得使用
RESERVED_IN_DMZ = {
    "10.80.0.1",    # DMZ 网关（防火墙 VRRP VIP）
    "10.80.0.10",   # srv-dmz（Web/HTTPS 发布服务器）
    "10.80.0.11",   # fw1 eth3
    "10.80.0.12",   # fw2 eth3
}
RESERVED_IN_DC = {
    "10.60.0.1",    # 数据中心网关（核心 VRRP VIP）
    "10.60.0.252",  # core1 eth13.70
    "10.60.0.253",  # core2 eth13.70
}
UPSTREAM_DNS = ["223.5.5.5", "223.6.6.6"]   # 上游公网 DNS（仿真中用 223.5.5.5）

# 校内域名与对外域名
INTERNAL_ZONE = "ecust.edu.cn"
PUBLIC_ZONE = "ecust.edu.cn"
# 需要对外发布的记录（外网只解析这些，内部记录不对外）
PUBLIC_RECORDS = [
    ("www", "198.51.100.80"),       # 通过 DNAT 发布到 DMZ 10.80.0.10
    ("mail", "198.51.100.80"),
]


@dataclass(frozen=True)
class DnsServer:
    name: str            # srv-dc1 / srv-dc2 / srv-dmz1 / srv-dmz2
    role: str            # 内部主 / 内部备 / 外部主 / 外部备
    zone: str            # 内部 / 外部
    ip: str
    subnet: str
    forwards_to: tuple[str, ...]
    authoritative_for: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "服务器": self.name,
            "角色": self.role,
            "Zone": self.zone,
            "IP": self.ip,
            "网段": self.subnet,
            "权威解析": ", ".join(self.authoritative_for) or "—",
            "转发目标": ", ".join(self.forwards_to) or "—",
        }


# ---------------------------------------------------------------- 设计
def build_servers() -> list[DnsServer]:
    """按设计方案 7.5 的“DNS（内外分设）4 台：数据中心 2 + DMZ 2”生成。"""
    dc = ipaddress.ip_network(DC_SUBNET)
    dmz = ipaddress.ip_network(DMZ_SUBNET)
    return [
        # 内部 DNS 主节点 = 仿真中的 srv-dc1（DHCP + DNS 同机），
        # 地址必须与 gen.py 的 DHCP_DNS 一致，否则 DHCP 下发的 DNS 会失效。
        DnsServer("srv-dc1", "内部主", "内部", str(dc[10]), DC_SUBNET,
                  tuple(UPSTREAM_DNS), (INTERNAL_ZONE,)),
        # 内部 DNS 备节点使用已建模但当前未承载服务的 srv-dc2。
        DnsServer("srv-dc2", "内部备", "内部", str(dc[11]), DC_SUBNET,
                  tuple(UPSTREAM_DNS), (INTERNAL_ZONE,)),
        DnsServer("srv-dmz1", "外部主", "外部", str(dmz[21]), DMZ_SUBNET,
                  ("内部 DNS srv-dc1",), (PUBLIC_ZONE,)),
        DnsServer("srv-dmz2", "外部备", "外部", str(dmz[22]), DMZ_SUBNET,
                  ("内部 DNS srv-dc2",), (PUBLIC_ZONE,)),
    ]


# ---------------------------------------------------------------- 检查
def check(servers: list[DnsServer]) -> list[str]:
    errors: list[str] = []

    if len(servers) != 4:
        errors.append(f"DNS 服务器 {len(servers)} 台，设计方案要求 4 台（内外各 2）")

    ips: dict[str, str] = {}
    for s in servers:
        # 1. 地址在各自网段内
        net = ipaddress.ip_network(s.subnet)
        if ipaddress.ip_address(s.ip) not in net:
            errors.append(f"{s.name} 的 {s.ip} 不在 {s.subnet} 内")
        # 2. 地址唯一
        if s.ip in ips:
            errors.append(f"{s.name} 与 {ips[s.ip]} 地址重复（{s.ip}）")
        ips[s.ip] = s.name
        # 3. 不得占用已分配地址、网关与 DHCP 动态范围
        reserved = RESERVED_IN_DC if s.subnet == DC_SUBNET else RESERVED_IN_DMZ
        if s.ip in reserved:
            errors.append(f"{s.name} 的 {s.ip} 已被现有设备占用")
        if ipaddress.ip_address(s.ip) == net[1]:
            errors.append(f"{s.name} 的 {s.ip} 与网关冲突")
        if 100 <= int(s.ip.split(".")[-1]) <= 200:
            errors.append(f"{s.name} 的 {s.ip} 落在 DHCP 动态范围 .100-.200 内")

    # 4. 内外分区：数据中心内只有内部 DNS，DMZ 内只有外部 DNS
    for s in servers:
        if s.zone == "内部" and s.subnet != DC_SUBNET:
            errors.append(f"{s.name} 为内部 DNS，应部署在数据中心 {DC_SUBNET}")
        if s.zone == "外部" and s.subnet != DMZ_SUBNET:
            errors.append(f"{s.name} 为外部 DNS，应部署在 DMZ {DMZ_SUBNET}")

    # 5. 每个 Zone 都有主备各一台
    for zone in ("内部", "外部"):
        roles = sorted(s.role for s in servers if s.zone == zone)
        if roles != ["外部主", "外部备"] and roles != ["内部主", "内部备"]:
            errors.append(f"{zone} DNS 角色应为（主、备），实际 {roles}")

    # 6. 内部 DNS 必须能递归到上游，外部 DNS 不得直接暴露内部递归
    for s in servers:
        if s.zone == "内部" and not any(x[0].isdigit() for x in s.forwards_to):
            errors.append(f"{s.name} 为内部 DNS，应配置公网上游递归")
        if s.zone == "外部" and any(x[0].isdigit() for x in s.forwards_to):
            errors.append(f"{s.name} 为外部 DNS，不应直接使用公网上游递归")

    # 7. DHCP 下发的 DNS 必须是内部 DNS 主节点的地址
    internal_primary = [s for s in servers if s.role == "内部主"]
    if internal_primary and internal_primary[0].ip != DHCP_DNS:
        errors.append(
            f"DHCP 下发 DNS {DHCP_DNS} 与内部主 DNS {internal_primary[0].ip} 不一致")

    return errors


def simulation_gaps(servers: list[DnsServer]) -> list[str]:
    """对比仿真工程中实际存在的 DNS 实现，列出设计覆盖但仿真未实现的部分。"""
    gaps: list[str] = []
    sim_dns = [s for s in servers if s.ip == DHCP_DNS]
    if sim_dns:
        gaps.append(
            f"仿真仅实现 {sim_dns[0].name}（{sim_dns[0].ip}）一台内部 DNS；"
            "内部备、外部主/备 4 台中的其余 3 台尚未建模")
    gaps.append("仿真对外域名解析未建模：DMZ 侧无权威 DNS，外网查询 www/mail 未经外部 DNS")
    gaps.append("仿真 DHCP 下发的 DNS 与内部主节点一致，主节点故障时无备节点接管")
    return gaps


FIELDS = ["服务器", "角色", "Zone", "IP", "网段", "权威解析", "转发目标"]


def to_markdown(servers: list[DnsServer]) -> str:
    out = ["| " + " | ".join(FIELDS) + " |",
           "| " + " | ".join(["---"] * len(FIELDS)) + " |"]
    for s in servers:
        d = s.as_dict()
        out.append("| " + " | ".join(str(d[f]) for f in FIELDS) + " |")
    return "\n".join(out) + "\n"


def to_csv(servers: list[DnsServer]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(s.as_dict() for s in servers)
    return buf.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成 DNS 规划并检查")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--md", action="store_true", help="输出 Markdown 规划表")
    group.add_argument("--csv", action="store_true", help="输出 CSV")
    args = parser.parse_args(argv)

    servers = build_servers()
    errors = check(servers)

    if args.md:
        sys.stdout.write(to_markdown(servers))
    elif args.csv:
        sys.stdout.write(to_csv(servers))
    else:
        print(f"DNS 服务器 {len(servers)} 台：")
        for s in servers:
            print(f"  {s.name:<10} {s.role:<4} {s.zone}  {s.ip:<14} {s.subnet}")
        print(f"\n校内域名：{INTERNAL_ZONE}（内部权威）")
        print(f"对外记录：{', '.join(f'{n}.{PUBLIC_ZONE}→{ip}' for n, ip in PUBLIC_RECORDS)}")
        print("\n仿真差距：")
        for g in simulation_gaps(servers):
            print(f"  - {g}")

    if errors:
        print("\n检查失败：", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    if not (args.md or args.csv):
        print("\n检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
