#!/usr/bin/env python3
"""Generate campus-lab containerlab topology and node configs.

Single source of truth: edit this file instead of generated configs.
Generation is deterministic except for configs/facts.json generated_at.
"""
import ipaddress
import json
import os
import shutil
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(BASE, "configs")

FRR_NODES = {}
ACCESS_NODES = {}
HOSTS = {}
HOST_META = {}
BRIDGES = []
FW_NODES = {}

CAPABILITIES = {"dhcp": True, "acl": True, "dnat": True, "lag": True, "report": True}

VLAN_PLAN = {
    50: {"name": "library", "subnet": "10.55.0.0/24", "gateway": "10.55.0.1", "region": "library"},
    61: {"name": "living", "subnet": "10.64.0.0/24", "gateway": "10.64.0.1", "region": "living"},
    70: {"name": "datacenter", "subnet": "10.60.0.0/24", "gateway": "10.60.0.1", "region": "datacenter"},
    80: {"name": "dmz", "subnet": "10.80.0.0/24", "gateway": "10.80.0.1", "region": "dmz"},
    90: {"name": "mgmt", "subnet": "10.70.0.0/24", "gateway": "10.70.0.1", "region": "mgmt"},
    101: {"name": "teaching-a", "subnet": "10.10.0.0/24", "gateway": "10.10.0.1", "region": "teaching"},
    102: {"name": "teaching-b", "subnet": "10.10.1.0/24", "gateway": "10.10.1.1", "region": "teaching"},
    201: {"name": "lab", "subnet": "10.20.0.0/24", "gateway": "10.20.0.1", "region": "lab"},
    301: {"name": "dorm-a", "subnet": "10.32.0.0/24", "gateway": "10.32.0.1", "region": "dorm"},
    500: {"name": "wireless-edu", "subnet": "10.50.0.0/24", "gateway": "10.50.0.1", "region": "teaching"},
    510: {"name": "wireless-dorm", "subnet": "10.51.0.0/24", "gateway": "10.51.0.1", "region": "dorm"},
}

DHCP_SERVER = "10.60.0.10"
DHCP_DNS = "10.60.0.10"
LEASE_BY_REGION = {"dorm": 43200, "teaching": 14400, "lab": 28800, "library": 28800, "living": 28800}
DHCP_POOLS = [
    {"vid": vid, "start": str(ipaddress.ip_network(VLAN_PLAN[vid]["subnet"])[100]),
     "end": str(ipaddress.ip_network(VLAN_PLAN[vid]["subnet"])[200]),
     "netmask": "255.255.255.0",
     "lease": LEASE_BY_REGION[VLAN_PLAN[vid]["region"]]}
    for vid in (50, 61, 101, 102, 201, 301, 500, 510)
]

ZONES = {
    "dorm_nets": ["10.32.0.0/24", "10.51.0.0/24"],
    "mgmt_nets": ["10.70.0.0/24"],
    "teaching_nets": ["10.10.0.0/16", "10.50.0.0/24"],
    "lab_nets": ["10.20.0.0/13"],
    "dc_nets": ["10.60.0.0/24"],
    "dmz_nets": ["10.80.0.0/24"],
    "internet_nets": ["203.0.113.0/24"],
    "dns_hosts": [DHCP_DNS + "/32"],
}

NAT_PUBLISH = {"address": "198.51.100.80", "ports": [80, 443], "target": "10.80.0.10"}
LAGS = {
    "core-lag0": {"mode": "802.3ad", "members": ["eth11", "eth14"],
                  "peers": {"core1": "core2", "core2": "core1"}},
    "dc-srv-lag0": {"mode": "active-backup", "members": ["eth1", "eth2"],
                    "peers": {"srv-dc1": "dc-sw"}},
}


def add_frr(name, loopback, ifs, trunks=None, static=None, ospf=True,
            default_originate=False, ospf_exclude=None, vrrp=None,
            bonds=None, acl=False, dhcp_relay=False):
    FRR_NODES[name] = dict(loopback=loopback, ifs=ifs or {}, trunks=trunks or {},
                           static=static or [], ospf=ospf,
                           default_originate=default_originate,
                           ospf_exclude=ospf_exclude or [],
                           vrrp=vrrp or [], bonds=bonds or {},
                           acl=acl, dhcp_relay=dhcp_relay)


# ---------------- Core ----------------
add_frr("core1", "10.255.0.1/32",
    ifs={
        "eth1": "10.0.10.1/30", "eth2": "10.0.20.1/30",
        "eth3": "10.0.30.1/30", "eth4": "10.0.40.1/30",
        "eth5": "10.0.50.1/30", "eth6": "10.0.10.9/30",
        "eth7": "10.0.20.9/30", "eth8": "10.0.30.9/30",
        "eth9": "10.0.40.9/30", "eth10": "10.0.50.9/30",
        "bond0": "10.0.0.1/30", "eth12": "10.0.100.1/24",
    },
    trunks={"eth13": [("70", "10.60.0.252/24"), ("90", "10.70.0.2/24")]},
    static=["0.0.0.0/0 10.0.100.254"],
    default_originate=True,
    ospf_exclude=["eth12"],
    bonds={"bond0": {"members": ["eth11", "eth14"], "mode": "802.3ad"}},
    acl=True,
    vrrp=[("eth12", 10, "10.0.100.253/24", 120),
          ("eth13.70", 9, "10.60.0.1/24", 120),
          ("eth13.90", 13, "10.70.0.1/24", 120)])

add_frr("core2", "10.255.0.2/32",
    ifs={
        "eth1": "10.0.10.5/30", "eth2": "10.0.20.5/30",
        "eth3": "10.0.30.5/30", "eth4": "10.0.40.5/30",
        "eth5": "10.0.50.5/30", "eth6": "10.0.10.13/30",
        "eth7": "10.0.20.13/30", "eth8": "10.0.30.13/30",
        "eth9": "10.0.40.13/30", "eth10": "10.0.50.13/30",
        "bond0": "10.0.0.2/30", "eth12": "10.0.100.2/24",
    },
    trunks={"eth13": [("70", "10.60.0.253/24"), ("90", "10.70.0.3/24")]},
    static=["0.0.0.0/0 10.0.100.254"],
    default_originate=True,
    ospf_exclude=["eth12"],
    bonds={"bond0": {"members": ["eth11", "eth14"], "mode": "802.3ad"}},
    acl=True,
    vrrp=[("eth12", 10, "10.0.100.253/24", 100),
          ("eth13.70", 9, "10.60.0.1/24", 100),
          ("eth13.90", 13, "10.70.0.1/24", 100)])

# ---------------- Teaching ----------------
add_frr("agg-t1", "10.255.0.11/32",
    ifs={"eth1": "10.0.10.2/30", "eth2": "10.0.10.6/30"},
    trunks={"eth3": [("101", "10.10.0.252/24"), ("500", "10.50.0.252/24")],
            "eth4": [("102", "10.10.1.252/24")]},
    acl=True, dhcp_relay=True,
    vrrp=[("eth3.101", 1, "10.10.0.1/24", 120),
          ("eth3.500", 3, "10.50.0.1/24", 120),
          ("eth4.102", 2, "10.10.1.1/24", 120)])

add_frr("agg-t2", "10.255.0.12/32",
    ifs={"eth1": "10.0.10.10/30", "eth2": "10.0.10.14/30"},
    trunks={"eth3": [("101", "10.10.0.253/24"), ("500", "10.50.0.253/24")],
            "eth4": [("102", "10.10.1.253/24")]},
    acl=True, dhcp_relay=True,
    vrrp=[("eth3.101", 1, "10.10.0.1/24", 100),
          ("eth3.500", 3, "10.50.0.1/24", 100),
          ("eth4.102", 2, "10.10.1.1/24", 100)])

# ---------------- Dorm ----------------
add_frr("agg-d1", "10.255.0.21/32",
    ifs={"eth1": "10.0.20.2/30", "eth2": "10.0.20.6/30"},
    trunks={"eth3": [("301", "10.32.0.252/24"), ("510", "10.51.0.252/24")]},
    acl=True, dhcp_relay=True,
    vrrp=[("eth3.301", 4, "10.32.0.1/24", 120),
          ("eth3.510", 5, "10.51.0.1/24", 120)])

add_frr("agg-d2", "10.255.0.22/32",
    ifs={"eth1": "10.0.20.10/30", "eth2": "10.0.20.14/30"},
    trunks={"eth3": [("301", "10.32.0.253/24"), ("510", "10.51.0.253/24")]},
    acl=True, dhcp_relay=True,
    vrrp=[("eth3.301", 4, "10.32.0.1/24", 100),
          ("eth3.510", 5, "10.51.0.1/24", 100)])

# ---------------- Lab ----------------
add_frr("agg-l1", "10.255.0.31/32",
    ifs={"eth1": "10.0.30.2/30", "eth2": "10.0.30.6/30"},
    trunks={"eth3": [("201", "10.20.0.252/24")]},
    acl=True, dhcp_relay=True,
    vrrp=[("eth3.201", 6, "10.20.0.1/24", 120)])

add_frr("agg-l2", "10.255.0.32/32",
    ifs={"eth1": "10.0.30.10/30", "eth2": "10.0.30.14/30"},
    trunks={"eth3": [("201", "10.20.0.253/24")]},
    acl=True, dhcp_relay=True,
    vrrp=[("eth3.201", 6, "10.20.0.1/24", 100)])

# ---------------- Library ----------------
add_frr("agg-lib1", "10.255.0.41/32",
    ifs={"eth1": "10.0.40.2/30", "eth2": "10.0.40.6/30"},
    trunks={"eth3": [("50", "10.55.0.252/24")]},
    acl=True, dhcp_relay=True,
    vrrp=[("eth3.50", 7, "10.55.0.1/24", 120)])

add_frr("agg-lib2", "10.255.0.42/32",
    ifs={"eth1": "10.0.40.10/30", "eth2": "10.0.40.14/30"},
    trunks={"eth3": [("50", "10.55.0.253/24")]},
    acl=True, dhcp_relay=True,
    vrrp=[("eth3.50", 7, "10.55.0.1/24", 100)])

# ---------------- Living ----------------
add_frr("agg-life1", "10.255.0.51/32",
    ifs={"eth1": "10.0.50.2/30", "eth2": "10.0.50.6/30"},
    trunks={"eth3": [("61", "10.64.0.252/24")]},
    acl=True, dhcp_relay=True,
    vrrp=[("eth3.61", 8, "10.64.0.1/24", 120)])

add_frr("agg-life2", "10.255.0.52/32",
    ifs={"eth1": "10.0.50.10/30", "eth2": "10.0.50.14/30"},
    trunks={"eth3": [("61", "10.64.0.253/24")]},
    acl=True, dhcp_relay=True,
    vrrp=[("eth3.61", 8, "10.64.0.1/24", 100)])

# ---------------- Edge routers ----------------
add_frr("r1", "10.255.0.101/32",
    ifs={"eth1": "10.90.1.1/24", "eth2": "203.0.113.1/24"},
    static=["0.0.0.0/0 203.0.113.100", "10.0.0.0/8 10.90.1.253",
            "198.51.100.0/24 10.90.1.253"],
    ospf=False,
    vrrp=[("eth1", 11, "10.90.1.254/24", 120),
          ("eth2", 12, "203.0.113.254/24", 120)])

add_frr("r2", "10.255.0.102/32",
    ifs={"eth1": "10.90.1.2/24", "eth2": "203.0.113.2/24"},
    static=["0.0.0.0/0 203.0.113.100", "10.0.0.0/8 10.90.1.253",
            "198.51.100.0/24 10.90.1.253"],
    ospf=False,
    vrrp=[("eth1", 11, "10.90.1.254/24", 100),
          ("eth2", 12, "203.0.113.254/24", 100)])

# ---------------- Access switches ----------------
for _name, _node in FRR_NODES.items():
    if _name.startswith("agg-") and "eth1" in _node["ifs"] and "eth2" in _node["ifs"]:
        _gw1 = str(ipaddress.ip_interface(_node["ifs"]["eth1"]).network[1])
        _gw2 = str(ipaddress.ip_interface(_node["ifs"]["eth2"]).network[1])
        _node["static"] = [f"10.70.0.0/24 {_gw1} 1", f"10.70.0.0/24 {_gw2} 2"]

ACCESS_NODES = {
    "acc-ta":  {"trunks": {"eth1": [101, 500], "eth2": [101, 500]},
                "access": {"eth3": 101, "eth4": 101, "eth5": 500,
                           "eth6": 101, "eth7": 500}},
    "acc-tb":  {"trunks": {"eth1": [102], "eth2": [102]},
                "access": {"eth3": 102}},
    "acc-d1":  {"trunks": {"eth1": [301, 510], "eth2": [301, 510]},
                "access": {"eth3": 301, "eth4": 510, "eth5": 301}},
    "acc-la":  {"trunks": {"eth1": [201], "eth2": [201]},
                "access": {"eth3": 201}},
    "acc-lib": {"trunks": {"eth1": [50], "eth2": [50]},
                "access": {"eth3": 50}},
    "acc-life":{"trunks": {"eth1": [61], "eth2": [61]},
                "access": {"eth3": 61}},
    "dc-sw":   {"trunks": {"eth1": [70, 90], "eth2": [70, 90]},
                "access": {"eth3": 70, "eth4": 70, "eth5": 90, "eth6": 70}},
}

# ---------------- Hosts ----------------
HOSTS = {
    "pc-ta1":  ("10.10.0.11/24", "10.10.0.1"),
    "pc-ta2":  ("10.10.0.12/24", "10.10.0.1"),
    "pc-tb1":  ("10.10.1.11/24", "10.10.1.1"),
    "pc-d1":   ("10.32.0.11/24", "10.32.0.1"),
    "pc-la1":  ("10.20.0.11/24", "10.20.0.1"),
    "pc-lib":  ("10.55.0.11/24", "10.55.0.1"),
    "pc-life": ("10.64.0.11/24", "10.64.0.1"),
    "ap-ta":   ("10.50.0.11/24", "10.50.0.1"),
    "ap-d1":   ("10.51.0.11/24", "10.51.0.1"),
    "srv-dc1": ("10.60.0.10/24", "10.60.0.1"),
    "srv-dc2": ("10.60.0.11/24", "10.60.0.1"),
    "srv-dmz": ("10.80.0.10/24", "10.80.0.1"),
    "internet":("203.0.113.100/24", "203.0.113.254"),
    "mgmt-pc": ("10.70.0.10/24", "10.70.0.1"),
    "pc-dyn1": ("dhcp", ""),
    "pc-dyn2": ("dhcp", ""),
    "pc-dyn3": ("dhcp", ""),
}

HOST_META = {
    "pc-dyn1": {"mode": "dhcp", "mac": "02:00:00:00:01:01"},
    "pc-dyn2": {"mode": "dhcp", "mac": "02:00:00:00:01:02"},
    "pc-dyn3": {"mode": "dhcp", "mac": "02:00:00:00:01:03"},
    "srv-dc1": {"mode": "static", "services": ["dhcp", "dns"],
                "bond": {"mode": "active-backup", "members": ["eth1", "eth2"],
                         "primary": "eth1"}},
    "srv-dmz": {"mode": "static", "services": ["http", "https"]},
}

# ---------------- Firewalls ----------------
FW_NODES = {
    "fw1": {"ips": {"eth1": "10.0.100.11/24", "eth2": "10.90.1.11/24",
                    "eth3": "10.80.0.11/24"}, "prio": 120, "state": "MASTER"},
    "fw2": {"ips": {"eth1": "10.0.100.12/24", "eth2": "10.90.1.12/24",
                    "eth3": "10.80.0.12/24"}, "prio": 100, "state": "BACKUP"},
}

# ---------------- Links ----------------
LINKS = [
    # core <-> aggregation
    ("core1","eth1","agg-t1","eth1"), ("core1","eth6","agg-t2","eth1"),
    ("core2","eth1","agg-t1","eth2"), ("core2","eth6","agg-t2","eth2"),
    ("core1","eth2","agg-d1","eth1"), ("core1","eth7","agg-d2","eth1"),
    ("core2","eth2","agg-d1","eth2"), ("core2","eth7","agg-d2","eth2"),
    ("core1","eth3","agg-l1","eth1"), ("core1","eth8","agg-l2","eth1"),
    ("core2","eth3","agg-l1","eth2"), ("core2","eth8","agg-l2","eth2"),
    ("core1","eth4","agg-lib1","eth1"), ("core1","eth9","agg-lib2","eth1"),
    ("core2","eth4","agg-lib1","eth2"), ("core2","eth9","agg-lib2","eth2"),
    ("core1","eth5","agg-life1","eth1"), ("core1","eth10","agg-life2","eth1"),
    ("core2","eth5","agg-life1","eth2"), ("core2","eth10","agg-life2","eth2"),
    # core-core bond members
    ("core1","eth11","core2","eth11"),
    ("core1","eth14","core2","eth14"),
    # core trust / dc
    ("core1","eth12","trust-sw","eth1"),
    ("core2","eth12","trust-sw","eth2"),
    ("core1","eth13","dc-sw","eth1"),
    ("core2","eth13","dc-sw","eth2"),
    # aggregation <-> access
    ("agg-t1","eth3","acc-ta","eth1"), ("agg-t2","eth3","acc-ta","eth2"),
    ("agg-t1","eth4","acc-tb","eth1"), ("agg-t2","eth4","acc-tb","eth2"),
    ("agg-d1","eth3","acc-d1","eth1"), ("agg-d2","eth3","acc-d1","eth2"),
    ("agg-l1","eth3","acc-la","eth1"), ("agg-l2","eth3","acc-la","eth2"),
    ("agg-lib1","eth3","acc-lib","eth1"), ("agg-lib2","eth3","acc-lib","eth2"),
    ("agg-life1","eth3","acc-life","eth1"), ("agg-life2","eth3","acc-life","eth2"),
    # access <-> hosts
    ("acc-ta","eth3","pc-ta1","eth1"), ("acc-ta","eth4","pc-ta2","eth1"),
    ("acc-ta","eth5","ap-ta","eth1"),
    ("acc-ta","eth6","pc-dyn1","eth1"), ("acc-ta","eth7","pc-dyn3","eth1"),
    ("acc-tb","eth3","pc-tb1","eth1"),
    ("acc-d1","eth3","pc-d1","eth1"), ("acc-d1","eth4","ap-d1","eth1"),
    ("acc-d1","eth5","pc-dyn2","eth1"),
    ("acc-la","eth3","pc-la1","eth1"),
    ("acc-lib","eth3","pc-lib","eth1"),
    ("acc-life","eth3","pc-life","eth1"),
    ("dc-sw","eth3","srv-dc1","eth1"), ("dc-sw","eth6","srv-dc1","eth2"),
    ("dc-sw","eth4","srv-dc2","eth1"),
    ("dc-sw","eth5","mgmt-pc","eth1"),
    # egress
    ("fw1","eth1","trust-sw","eth3"), ("fw2","eth1","trust-sw","eth4"),
    ("fw1","eth2","untrust-sw","eth3"), ("fw2","eth2","untrust-sw","eth4"),
    ("r1","eth1","untrust-sw","eth1"), ("r2","eth1","untrust-sw","eth2"),
    ("fw1","eth3","dmz-sw","eth1"), ("fw2","eth3","dmz-sw","eth2"),
    ("srv-dmz","eth1","dmz-sw","eth3"),
    ("r1","eth2","inet-sw","eth1"), ("r2","eth2","inet-sw","eth2"),
    ("internet","eth1","inet-sw","eth3"),
]

BRIDGES = {
    "trust-sw": ["eth1", "eth2", "eth3", "eth4"],
    "untrust-sw": ["eth1", "eth2", "eth3", "eth4"],
    "dmz-sw": ["eth1", "eth2", "eth3"],
    "inet-sw": ["eth1", "eth2", "eth3"],
}

DAEMONS = """zebra=yes
bgpd=no
ospfd=yes
ospf6d=no
ripd=no
ripngd=no
isisd=no
pimd=no
ldpd=no
nhrpd=no
eigrpd=no
babeld=no
sharpd=no
pbrd=no
bfdd=no
fabricd=no
vrrpd=no
staticd=yes
vtysh_enable=yes
watchfrr_enable=yes
"""

FW_NFT = """table inet fw {
  set mgmt_nets {
    type ipv4_addr
    flags interval
    elements = { 10.70.0.0/24 }
  }
  chain prerouting {
    type nat hook prerouting priority -100; policy accept;
    iifname "eth2" ip daddr 198.51.100.80 tcp dport 80 counter dnat to 10.80.0.10:80 comment "nat.dnat80"
    iifname "eth2" ip daddr 198.51.100.80 tcp dport 443 counter dnat to 10.80.0.10:443 comment "nat.dnat443"
  }
  chain forward {
    type filter hook forward priority 0; policy drop;
    ct state established,related counter accept comment "fw.established"
    iifname "eth1" ip daddr @mgmt_nets counter drop comment "iso.mgmt_guard"
    ct status dnat tcp dport { 80, 443 } counter accept comment "nat.allow"
    iifname "eth1" oifname "eth2" counter accept comment "fw.trust2untrust"
    iifname "eth1" oifname "eth3" counter accept comment "fw.trust2dmz"
    iifname "eth2" oifname "eth3" counter drop comment "nat.private_direct_drop"
    iifname "eth2" oifname "eth1" counter drop comment "fw.untrust2trust_drop"
    iifname "eth3" oifname "eth1" counter drop comment "fw.dmz2trust_drop"
    iifname "eth3" oifname "eth2" counter drop comment "fw.dmz2untrust_drop"
  }
  chain postrouting {
    type nat hook postrouting priority 100; policy accept;
    iifname "eth3" oifname "eth2" ct status dnat counter accept comment "nat.dnat_return"
    iifname "eth1" oifname "eth2" counter masquerade comment "nat.snat"
  }
}
"""


def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def net(ip):
    return str(ipaddress.ip_interface(ip).network)


def all_ips(node):
    out = {"lo": node["loopback"]}
    out.update(node["ifs"])
    for parent, subs in node["trunks"].items():
        for vid, ip in subs:
            out[f"{parent}.{vid}"] = ip
    return out


def sanitize(s):
    return s.replace(".", "_").replace("-", "_")


def valid_ip(value):
    try:
        ipaddress.ip_interface(value)
        return True
    except ValueError:
        return False


def validate_design():
    errors = []
    if len(VLAN_PLAN) != len(set(VLAN_PLAN)):
        errors.append("VLAN 编号重复")
    subnets = {}
    for vid, plan in VLAN_PLAN.items():
        network = ipaddress.ip_network(plan["subnet"])
        if network in subnets:
            errors.append(f"VLAN {vid} 与 VLAN {subnets[network]} 网段重复")
        subnets[network] = vid
        if ipaddress.ip_address(plan["gateway"]) not in network:
            errors.append(f"VLAN {vid} 网关 {plan['gateway']} 不在 {network}")
        if vid not in (50, 61, 70, 80, 90, 101, 102, 201, 301, 500, 510):
            errors.append(f"VLAN {vid} 不在规划集合")
    ranges = []
    for pool in DHCP_POOLS:
        plan = VLAN_PLAN.get(pool["vid"])
        if not plan:
            errors.append(f"DHCP 池引用未知 VLAN {pool['vid']}")
            continue
        network = ipaddress.ip_network(plan["subnet"])
        start = ipaddress.ip_address(pool["start"])
        end = ipaddress.ip_address(pool["end"])
        if start not in network or end not in network:
            errors.append(f"VLAN {pool['vid']} 池地址不在网段内")
        if int(start) > int(end):
            errors.append(f"VLAN {pool['vid']} 池起止地址颠倒")
        for reserved in range(1, 12):
            if int(start) <= int(network[reserved]) <= int(end):
                errors.append(f"VLAN {pool['vid']} 池包含保留地址 {network[reserved]}")
        for other, other_network in ranges:
            if network != other_network and network.overlaps(other_network):
                errors.append(f"VLAN {pool['vid']} 池与 VLAN {other} 重叠")
        ranges.append((pool["vid"], network))
        if pool["lease"] != LEASE_BY_REGION[plan["region"]]:
            errors.append(f"VLAN {pool['vid']} 租期与区域不匹配")
    publish = NAT_PUBLISH
    if publish["address"] in ("203.0.113.100", "203.0.113.254", "10.90.1.253"):
        errors.append("NAT 发布地址与现有地址冲突")
    for port in publish["ports"]:
        if port not in (80, 443):
            errors.append(f"DMZ 发布端口 {port} 不在白名单")
    for lag, cfg in LAGS.items():
        for host, peer in cfg["peers"].items():
            if host not in FRR_NODES and host not in HOSTS:
                errors.append(f"{lag} 成员 {host} 不存在")
    static_ips = {}
    for name, (ip, _gw) in HOSTS.items():
        if ip == "dhcp":
            continue
        if ip in static_ips:
            errors.append(f"{name} 与 {static_ips[ip]} 静态地址重复 {ip}")
        static_ips[ip] = name
        if not valid_ip(ip):
            errors.append(f"{name} 地址 {ip} 非法")
    for name, meta in HOST_META.items():
        if meta.get("mode") == "dhcp" and not meta.get("mac"):
            errors.append(f"{name} 动态终端缺少固定 MAC")
    if errors:
        print("design validation failed:")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)


def gen_frr(node_name, node):
    lines = [
        "frr version 10.6",
        "frr defaults traditional",
        f"hostname {node_name}",
        "log file /var/log/frr/frr.log",
        "service integrated-vtysh-config",
        "!",
        "interface lo",
        f" ip address {node['loopback']}",
        "!",
    ]
    for ifname, ip in node["ifs"].items():
        lines += [f"interface {ifname}", f" ip address {ip}", "!"]
    for parent, subs in node["trunks"].items():
        for vid, ip in subs:
            lines += [f"interface {parent}.{vid}", f" ip address {ip}", "!"]
    if node["ospf"]:
        rid = node["loopback"].split("/")[0]
        lines += ["router ospf", f" ospf router-id {rid}"]
        seen = set()
        for ifname, ip in all_ips(node).items():
            if ifname in node["ospf_exclude"]:
                continue
            network = net(ip)
            if network in seen:
                continue
            seen.add(network)
            lines.append(f" network {network} area 0")
        for ifname, ip in all_ips(node).items():
            if ipaddress.ip_interface(ip).network.prefixlen != 30 and ifname not in node["ospf_exclude"]:
                lines.append(f" passive-interface {ifname}")
        lines.append(" maximum-paths 4")
        if node["default_originate"]:
            lines.append(" default-information originate")
        lines.append("!")
    for route in node["static"]:
        lines.append(f"ip route {route}")
    if node["static"]:
        lines.append("!")
    lines += ["line vty", "!", ""]
    return "\n".join(lines)


def gen_prestart(node):
    lines = ["#!/bin/sh"]
    expected = [name for name in node["ifs"].keys() if name not in node["bonds"]] + list(node["trunks"].keys())
    for cfg in node["bonds"].values():
        expected += cfg["members"]
    for ifname in expected:
        lines.append(
            f"n=0; while [ ! -e /sys/class/net/{ifname} ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done"
        )
    if node["bonds"]:
        lines.append("modprobe bonding 2>/dev/null || true")
        for bond, cfg in node["bonds"].items():
            if cfg["mode"] == "802.3ad":
                lines.append(
                    f"ip link add {bond} type bond mode 802.3ad miimon 100 lacp_rate fast 2>/dev/null || "
                    f"ip link add {bond} type bond mode active-backup miimon 100 2>/dev/null || true"
                )
                lines.append(
                    f"echo layer3+4 > /sys/class/net/{bond}/bonding/xmit_hash_policy 2>/dev/null || true"
                )
            else:
                lines.append(
                    f"ip link add {bond} type bond mode {cfg['mode']} miimon 100 primary {cfg.get('primary', '')} 2>/dev/null || true"
                )
            for member in cfg["members"]:
                lines.append(f"ip link set {member} down 2>/dev/null || true")
                lines.append(f"ip link set {member} master {bond} 2>/dev/null || true")
                lines.append(f"ip link set {member} up 2>/dev/null || true")
            lines.append(f"ip link set {bond} up 2>/dev/null || true")
    lines.append("ip route del default 2>/dev/null || true")
    lines.append("for i in $(ls /sys/class/net | grep '^eth'); do ip link set \"$i\" up 2>/dev/null || true; done")
    for parent, subs in node["trunks"].items():
        lines.append(f"ip link set {parent} up 2>/dev/null || true")
        for vid, ip in subs:
            lines.append(f"ip link add link {parent} name {parent}.{vid} type vlan id {vid} 2>/dev/null || true")
            lines.append(f"ip link set {parent}.{vid} up")
    if node["acl"]:
        lines.append("nft delete table inet zone 2>/dev/null || true")
        lines.append("nft -f /configs/acl.nft 2>/dev/null || true")
    lines.append("exit 0")
    return "\n".join(lines) + "\n"


def gen_keepalived(node_name, node):
    lines = []
    for ifname, vrid, vip, prio in node["vrrp"]:
        state = "MASTER" if prio >= 120 else "BACKUP"
        name = f"VI_{sanitize(ifname)}_{vrid}"
        lines += [
            f"vrrp_instance {name} {{",
            f"    state {state}",
            f"    interface {ifname}",
            f"    virtual_router_id {vrid}",
            f"    priority {prio}",
            "    advert_int 1",
            "    virtual_ipaddress {",
            f"        {vip}",
            "    }",
            "}",
            "",
        ]
    return "\n".join(lines)


def gen_access(node_name, cfg):
    ports = list(cfg["trunks"].keys()) + list(cfg["access"].keys())
    lines = ["#!/bin/sh", "set -e",
             "ip link add br0 type bridge vlan_filtering 1 vlan_default_pvid 0 2>/dev/null || true",
             "ip link set br0 up"]
    for p in ports:
        lines += [f"ip link set {p} up",
                  f"ip link set {p} master br0 2>/dev/null || true",
                  f"bridge vlan del dev {p} vid 1 2>/dev/null || true"]
    for p, vids in cfg["trunks"].items():
        for v in vids:
            lines.append(f"bridge vlan add dev {p} vid {v}")
    for p, v in cfg["access"].items():
        lines.append(f"bridge vlan add dev {p} vid {v} pvid untagged")
    lines += ["exit 0", ""]
    return "\n".join(lines)


def gen_udhcpc_script():
    return """#!/bin/sh
case "$1" in
  deconfig)
    ip addr flush dev "$interface" 2>/dev/null || true
    ip link set "$interface" up
    ;;
  bound|renew)
    ip link set "$interface" up
    ip addr replace "$ip/${mask:-255.255.255.0}" dev "$interface"
    set -- $router
    [ -n "$1" ] && ip route replace default via "$1"
    {
      echo "ip=$ip"
      echo "subnet=$mask"
      echo "router=$router"
      echo "dns=$dns"
      echo "lease=$lease"
      echo "server=$serverid"
    } > /tmp/dhcp.env
    ;;
esac
exit 0
"""


def gen_host(name, ip, gw):
    meta = HOST_META.get(name, {"mode": "static"})
    lines = ["#!/bin/sh", "set -e"]
    if meta.get("mode") == "dhcp":
        lines += [
            "ip link set eth1 down",
            f"ip link set eth1 address {meta['mac']}",
            "ip link set eth1 up",
            "chmod +x /configs/udhcpc.sh",
            "udhcpc -i eth1 -s /configs/udhcpc.sh -b -t 60 -T 3 >/var/log/udhcpc.log 2>&1 &",
            "exit 0",
            "",
        ]
        return "\n".join(lines)
    if name == "srv-dc1":
        bond = meta.get("bond", {})
        lines += [
            "ip link set eth1 down 2>/dev/null || true",
            "ip link set eth2 down 2>/dev/null || true",
            f"ip link add bond0 type bond mode {bond.get('mode', 'active-backup')} miimon 100 "
            f"primary {bond.get('primary', 'eth1')} 2>/dev/null || true",
            "if ip link show bond0 >/dev/null 2>&1; then",
            "  ip link set eth1 master bond0 2>/dev/null || true",
            "  ip link set eth2 master bond0 2>/dev/null || true",
            "  ip link set eth1 up 2>/dev/null || true",
            "  ip link set eth2 up 2>/dev/null || true",
            "  ip link set bond0 up",
            f"  ip addr replace {ip} dev bond0",
            "else",
            "  ip link set eth1 up",
            f"  ip addr replace {ip} dev eth1",
            "fi",
            f"ip route replace default via {gw}",
            "dnsmasq -C /configs/dnsmasq.conf >/var/log/dnsmasq.log 2>&1 &",
            "exit 0",
            "",
        ]
        return "\n".join(lines)
    lines += ["ip link set eth1 up",
              f"ip addr replace {ip} dev eth1",
              f"ip route replace default via {gw}"]
    if name == "srv-dmz":
        lines += [
            "mkdir -p /www", "echo 'DMZ server OK' > /www/index.html",
            "cat > /www/serve80.sh <<'EOF'",
            "while true; do",
            "  printf 'HTTP/1.1 200 OK\\r\\nContent-Type: text/plain\\r\\nContent-Length: 13\\r\\nConnection: close\\r\\n\\r\\nDMZ server OK' | nc -l -p 80 -w 2",
            "done",
            "EOF",
            "cat > /www/serve443.sh <<'EOF'",
            "while true; do",
            "  printf 'HTTP/1.1 200 OK\\r\\nContent-Type: text/plain\\r\\nContent-Length: 13\\r\\nConnection: close\\r\\n\\r\\nDMZ server OK' | nc -l -p 443 -w 2",
            "done",
            "EOF",
            "sh /www/serve80.sh >/var/log/dmz-http.log 2>&1 &",
            "sh /www/serve443.sh >/var/log/dmz-https.log 2>&1 &",
        ]
    lines += ["exit 0", ""]
    return "\n".join(lines)


def gen_dhcp_server():
    lines = [
        "port=53",
        "domain-needed",
        "bogus-priv",
        "no-resolv",
        "server=223.5.5.5",
        "listen-address=10.60.0.10",
        "bind-dynamic",
        "except-interface=eth0",
        "dhcp-authoritative",
        "dhcp-leasefile=/var/log/dhcp.leases",
        "log-facility=/var/log/dnsmasq.log",
        "",
    ]
    for pool in DHCP_POOLS:
        plan = VLAN_PLAN[pool["vid"]]
        tag = f"v{pool['vid']}"
        lines += [
            f"dhcp-range=set:{tag},{pool['start']},{pool['end']},{pool['netmask']},{pool['lease']}",
            f"dhcp-option=tag:{tag},1,{pool['netmask']}",
            f"dhcp-option=tag:{tag},3,{plan['gateway']}",
            f"dhcp-option=tag:{tag},6,{DHCP_DNS}",
        ]
    return "\n".join(lines) + "\n"


def gen_dhcp_relay(node):
    lines = [
        "port=0",
        "no-resolv",
        "no-hosts",
        "log-facility=/var/log/dhcp-relay.log",
    ]
    for parent, subs in node["trunks"].items():
        for vid, ip in subs:
            if int(vid) not in [pool["vid"] for pool in DHCP_POOLS]:
                continue
            local = ip.split("/")[0]
            lines.append(f"dhcp-relay={local},{DHCP_SERVER}")
    return "\n".join(lines) + "\n"


def gen_start_services(node):
    svis = []
    for parent, subs in node["trunks"].items():
        for vid, _ip in subs:
            svis.append(f"{parent}.{vid}")
    dev_list = " ".join(svis)
    lines = [
        "#!/bin/sh",
        "set -u",
        "log=/var/log/frr/services.log",
        ": > \"$log\"",
        "i=0; ready=0",
        f"while [ $i -lt 60 ] && [ $ready -eq 0 ]; do",
        "  ready=1",
        f"  for dev in {dev_list}; do",
        "    ip -4 addr show dev \"$dev\" 2>/dev/null | grep -q 'inet ' || ready=0",
        "  done",
        "  i=$((i+1))",
        "  [ $ready -eq 1 ] || sleep 0.5",
        "done",
        "if [ $ready -eq 0 ]; then echo 'SVI not ready' >> \"$log\"; exit 0; fi",
        "if [ -f /configs/acl.nft ]; then",
        "  nft delete table inet zone 2>/dev/null || true",
        "  nft -f /configs/acl.nft >> \"$log\" 2>&1 || echo 'acl load failed' >> \"$log\"",
        "fi",
        "i=0; routed=0",
        f"while [ $i -lt 240 ]; do ip route get {DHCP_SERVER} >/dev/null 2>&1 && routed=1 && break; i=$((i+1)); sleep 0.5; done",
        f"[ $routed -eq 1 ] || echo 'route to {DHCP_SERVER} not ready' >> \"$log\"",
        "if [ -f /configs/dhcp-relay.conf ]; then",
        "  if [ $routed -eq 1 ]; then",
        "    dnsmasq -C /configs/dhcp-relay.conf >> \"$log\" 2>&1 && echo 'dhcp relay started' >> \"$log\" || echo 'dhcp relay failed' >> \"$log\"",
        "  else",
        "    (",
        "      while true; do",
        f"        if ip route get {DHCP_SERVER} >/dev/null 2>&1; then",
        "          dnsmasq -C /configs/dhcp-relay.conf >> \"$log\" 2>&1 && echo 'dhcp relay started late' >> \"$log\" && break",
        "        fi",
        "        sleep 2",
        "      done",
        "    ) &",
        "    echo 'dhcp relay deferred' >> \"$log\"",
        "  fi",
        "fi",
        "exit 0",
        "",
    ]
    return "\n".join(lines)


def gen_acl(node_name, node):
    sets = []
    for name, elements in ZONES.items():
        values = ", ".join(elements)
        sets += [
            f"  set {name} {{",
            "    type ipv4_addr",
            "    flags interval",
            f"    elements = {{ {values} }}",
            "  }",
        ]
    dorm_svis = []
    for parent, subs in node["trunks"].items():
        for vid, _ip in subs:
            if int(vid) in (301, 510):
                dorm_svis.append(f"{parent}.{vid}")
    lines = ["table inet zone {"] + sets + ["  chain forward {",
             "    type filter hook forward priority 0; policy accept;",
             "    ct state established,related counter accept comment \"zone.established\"",
             "    udp dport { 67, 68 } counter accept comment \"iso.dhcp\""]
    if dorm_svis:
        names = ", ".join(f'"{name}"' for name in dorm_svis)
        lines.append(
            f"    iifname {{ {names} }} ip saddr != @dorm_nets counter drop comment \"iso.src_guard\""
        )
        lines.append("    ip saddr @dorm_nets jump dorm_filter")
    lines += [
        "    ip saddr @mgmt_nets ip daddr @internet_nets counter drop comment \"iso.mgmt2inet\"",
        "    ip saddr @mgmt_nets counter accept comment \"iso.mgmt2biz\"",
    ]
    if node_name in ("core1", "core2"):
        lines.append("    ip daddr @mgmt_nets ip saddr != @mgmt_nets counter drop comment \"iso.mgmt_guard\"")
    lines += [
        "  }",
        "  chain dorm_filter {",
        "    ip daddr @dorm_nets counter accept comment \"iso.dorm_internal\"",
        "    ip daddr @dns_hosts udp dport 53 counter accept comment \"iso.dorm_dns\"",
        "    ip daddr @dns_hosts tcp dport 53 counter accept comment \"iso.dorm_dns\"",
        "    ip daddr @internet_nets counter accept comment \"iso.dorm2inet\"",
        "    ip daddr @dmz_nets tcp dport { 80, 443 } counter accept comment \"iso.dorm2dmz\"",
        "    ip daddr @mgmt_nets counter drop comment \"iso.dorm2mgmt\"",
        "    ip daddr @teaching_nets counter drop comment \"iso.dorm2teaching\"",
        "    ip daddr @lab_nets counter drop comment \"iso.dorm2lab\"",
        "    ip daddr @dc_nets counter drop comment \"iso.dorm2dc\"",
        "    counter drop comment \"iso.dorm_default\"",
        "  }",
        "}",
        "",
    ]
    return "\n".join(lines)


def gen_fw(name, cfg):
    lines = ["#!/bin/sh", "set -e",
             "ip link set eth1 up", "ip link set eth2 up", "ip link set eth3 up"]
    for ifname, ip in cfg["ips"].items():
        lines.append(f"ip addr replace {ip} dev {ifname}")
    lines.append("ip addr add 198.51.100.80/32 dev eth2 2>/dev/null || true")
    lines += ["ip route replace default via 10.90.1.254",
              "ip route replace 10.0.0.0/8 via 10.0.100.253",
              "sysctl -w net.ipv4.ip_forward=1 >/dev/null",
              "sysctl -w net.ipv4.conf.all.rp_filter=0 >/dev/null",
              "nft delete table inet fw 2>/dev/null || true",
              "nft -f /configs/fw.nft",
              "keepalived -D -f /configs/keepalived.conf >/var/log/keepalived.log 2>&1 &",
              "exit 0", ""]
    return "\n".join(lines)


def gen_fw_keepalived(cfg):
    lines = []
    instances = [("VI_TRUST", "eth1", 20, "10.0.100.254/24"),
                 ("VI_UNTRUST", "eth2", 21, "10.90.1.253/24"),
                 ("VI_DMZ", "eth3", 22, "10.80.0.1/24")]
    for name, ifname, vrid, vip in instances:
        lines += [f"vrrp_instance {name} {{",
                  f"    state {cfg['state']}",
                  f"    interface {ifname}",
                  f"    virtual_router_id {vrid}",
                  f"    priority {cfg['prio']}",
                  "    advert_int 1",
                  "    virtual_ipaddress {",
                  f"        {vip}",
                  "    }",
                  "}", ""]
    return "\n".join(lines)


def gen_facts():
    counts = {
        "frr": len(FRR_NODES),
        "l2": len(ACCESS_NODES),
        "host": len(HOSTS),
        "fw": len(FW_NODES),
        "bridge": len(BRIDGES),
    }
    counts["total"] = sum(counts.values())
    vlans = [v for v in sorted(VLAN_PLAN) if v != 90]
    subnets = {}
    for vid in vlans:
        plan = VLAN_PLAN[vid]
        subnets[str(vid)] = {
            "name": plan["name"],
            "subnet": plan["subnet"],
            "gateway": plan["gateway"],
            "region": plan["region"],
        }
    relays = [name for name, node in FRR_NODES.items() if node.get("dhcp_relay")]
    facts = {
        "nodes": counts,
        "links": len(LINKS),
        "vlans": vlans,
        "mgmt_vlan": 90,
        "subnets": subnets,
        "dhcp": {
            "server": DHCP_SERVER,
            "dns": DHCP_DNS,
            "pools": [dict(pool, subnet=VLAN_PLAN[pool["vid"]]["subnet"],
                           gateway=VLAN_PLAN[pool["vid"]]["gateway"])
                      for pool in DHCP_POOLS],
            "relays": relays,
        },
        "nat": {
            "publish": [
                {"public": f"{NAT_PUBLISH['address']}:{port}",
                 "private": f"{NAT_PUBLISH['target']}:{port}",
                 "type": "dnat"}
                for port in NAT_PUBLISH["ports"]
            ]
        },
        "lags": [
            {"name": name, "mode": cfg["mode"], "members": cfg["members"],
             "peers": cfg["peers"]}
            for name, cfg in LAGS.items()
        ],
        "capabilities": CAPABILITIES,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return json.dumps(facts, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


# ---------------- Draw.io layout levels ----------------
GRAPH_LEVELS = {
    "internet": 0,
    "inet-sw": 1,
    "r1": 2, "r2": 2,
    "untrust-sw": 3,
    "fw1": 4, "fw2": 4,
    "trust-sw": 5, "dmz-sw": 5,
    "core1": 6, "core2": 6,
    "agg-t1": 7, "agg-t2": 7,
    "agg-d1": 7, "agg-d2": 7,
    "agg-l1": 7, "agg-l2": 7,
    "agg-lib1": 7, "agg-lib2": 7,
    "agg-life1": 7, "agg-life2": 7,
    "acc-ta": 8, "acc-tb": 8, "acc-d1": 8,
    "acc-la": 8, "acc-lib": 8, "acc-life": 8, "dc-sw": 8,
    "pc-dyn1": 9, "pc-dyn2": 9, "pc-dyn3": 9, "mgmt-pc": 9,
}
for _name in HOSTS:
    GRAPH_LEVELS.setdefault(_name, 9)


def graph_label_lines(name):
    level = GRAPH_LEVELS.get(name)
    if level is None:
        return []
    return ["      labels:", f"        graph-level: {level}"]


validate_design()

# ---------------- Generate configs ----------------
shutil.rmtree(CFG, ignore_errors=True)
w(os.path.join(CFG, "frr", "daemons"), DAEMONS)

for name, node in FRR_NODES.items():
    d = os.path.join(CFG, "frr", name)
    w(os.path.join(d, "frr.conf"), gen_frr(name, node))
    w(os.path.join(d, "prestart.sh"), gen_prestart(node))
    w(os.path.join(d, "keepalived.conf"), gen_keepalived(name, node))
    if node["acl"]:
        w(os.path.join(d, "acl.nft"), gen_acl(name, node))
    if node["dhcp_relay"]:
        w(os.path.join(d, "dhcp-relay.conf"), gen_dhcp_relay(node))
        w(os.path.join(d, "start-services.sh"), gen_start_services(node))

for name, cfg in ACCESS_NODES.items():
    d = os.path.join(CFG, "access", name)
    w(os.path.join(d, "setup.sh"), gen_access(name, cfg))

for name, ports in BRIDGES.items():
    lines = ["#!/bin/sh", "set -e",
             "ip link add br0 type bridge 2>/dev/null || true",
             "ip link set br0 up"]
    for p in ports:
        lines += [f"ip link set {p} up",
                  f"ip link set {p} master br0 2>/dev/null || true"]
    lines += ["exit 0", ""]
    w(os.path.join(CFG, "access", name, "setup.sh"), "\n".join(lines))

for name, (ip, gw) in HOSTS.items():
    d = os.path.join(CFG, "hosts", name)
    w(os.path.join(d, "setup.sh"), gen_host(name, ip, gw))
    if HOST_META.get(name, {}).get("mode") == "dhcp":
        w(os.path.join(d, "udhcpc.sh"), gen_udhcpc_script())
    if name == "srv-dc1":
        w(os.path.join(d, "dnsmasq.conf"), gen_dhcp_server())

w(os.path.join(CFG, "fw", "fw.nft"), FW_NFT)
for name, cfg in FW_NODES.items():
    d = os.path.join(CFG, "fw", name)
    w(os.path.join(d, "setup.sh"), gen_fw(name, cfg))
    w(os.path.join(d, "keepalived.conf"), gen_fw_keepalived(cfg))

w(os.path.join(CFG, "facts.json"), gen_facts())

# ---------------- Generate topology ----------------
y = []
y.append("name: campus-lab")
y.append("mgmt:")
y.append("  network: campus_mgmt")
y.append("  ipv4-subnet: 172.31.100.0/24")
y.append("topology:")
y.append("  nodes:")

for name in FRR_NODES:
    node = FRR_NODES[name]
    y += [f"    {name}:",
          "      kind: linux",
          "      image: campus-frr:latest",
          "      binds:",
          "        - ./configs/frr/daemons:/etc/frr/daemons",
          f"        - ./configs/frr/{name}/frr.conf:/etc/frr/frr.conf",
          f"        - ./configs/frr/{name}/prestart.sh:/configs/prestart.sh",
          f"        - ./configs/frr/{name}/keepalived.conf:/configs/keepalived.conf"]
    if node["acl"]:
        y.append(f"        - ./configs/frr/{name}/acl.nft:/configs/acl.nft")
    if node["dhcp_relay"]:
        y.append(f"        - ./configs/frr/{name}/dhcp-relay.conf:/configs/dhcp-relay.conf")
        y.append(f"        - ./configs/frr/{name}/start-services.sh:/configs/start-services.sh")
    y += graph_label_lines(name)

for name in ACCESS_NODES:
    y += [f"    {name}:",
          "      kind: linux",
          "      image: campus-l2:latest",
          "      binds:",
          f"        - ./configs/access/{name}/setup.sh:/setup.sh",
          "      exec:",
          "        - sh /setup.sh"]
    y += graph_label_lines(name)

for name in FW_NODES:
    y += [f"    {name}:",
          "      kind: linux",
          "      image: campus-fw:latest",
          "      cmd: sleep infinity",
          "      binds:",
          f"        - ./configs/fw/{name}/setup.sh:/setup.sh",
          f"        - ./configs/fw/{name}/keepalived.conf:/configs/keepalived.conf",
          "        - ./configs/fw/fw.nft:/configs/fw.nft",
          "      exec:",
          "        - sh /setup.sh"]
    y += graph_label_lines(name)

for name in HOSTS:
    y += [f"    {name}:",
          "      kind: linux",
          "      image: campus-host:latest",
          "      cmd: sleep infinity",
          "      binds:",
          f"        - ./configs/hosts/{name}/setup.sh:/setup.sh"]
    meta = HOST_META.get(name, {})
    if meta.get("mode") == "dhcp":
        y.append(f"        - ./configs/hosts/{name}/udhcpc.sh:/configs/udhcpc.sh")
    if name == "srv-dc1":
        y.append(f"        - ./configs/hosts/{name}/dnsmasq.conf:/configs/dnsmasq.conf")
    y += ["      exec:",
          "        - sh /setup.sh"]
    y += graph_label_lines(name)

for name in BRIDGES:
    y += [f"    {name}:",
          "      kind: linux",
          "      image: campus-l2:latest",
          "      binds:",
          f"        - ./configs/access/{name}/setup.sh:/setup.sh",
          "      exec:",
          "        - sh /setup.sh"]
    y += graph_label_lines(name)

y.append("  links:")
for a, ai, b, bi in LINKS:
    y.append(f'    - endpoints: ["{a}:{ai}", "{b}:{bi}"]')

w(os.path.join(BASE, "campus-lab.clab.yml"), "\n".join(y) + "\n")
print("generated", len(FRR_NODES), "frr,", len(ACCESS_NODES), "l2,", len(HOSTS), "hosts,", len(FW_NODES), "fw,", len(BRIDGES), "bridges")
print("total nodes:", len(FRR_NODES)+len(ACCESS_NODES)+len(HOSTS)+len(FW_NODES)+len(BRIDGES))
print("links:", len(LINKS))