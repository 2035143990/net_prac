#!/usr/bin/env python3
"""Generate campus-lab containerlab topology and node configs."""
import os
import ipaddress
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(BASE, "configs")

FRR_NODES = {}
ACCESS_NODES = {}
HOSTS = {}
BRIDGES = []
FW_NODES = {}

def add_frr(name, loopback, ifs, trunks=None, static=None, ospf=True,
            default_originate=False, ospf_exclude=None, vrrp=None):
    FRR_NODES[name] = dict(loopback=loopback, ifs=ifs or {}, trunks=trunks or {},
                           static=static or [], ospf=ospf,
                           default_originate=default_originate,
                           ospf_exclude=ospf_exclude or [],
                           vrrp=vrrp or [])

# ---------------- Core ----------------
add_frr("core1", "10.255.0.1/32",
    ifs={
        "eth1": "10.0.10.1/30", "eth2": "10.0.20.1/30",
        "eth3": "10.0.30.1/30", "eth4": "10.0.40.1/30",
        "eth5": "10.0.50.1/30", "eth6": "10.0.10.9/30",
        "eth7": "10.0.20.9/30", "eth8": "10.0.30.9/30",
        "eth9": "10.0.40.9/30", "eth10": "10.0.50.9/30",
        "eth11": "10.0.0.1/30", "eth12": "10.0.100.1/24",
        "eth14": "10.0.0.5/30",
    },
    trunks={"eth13": [("70", "10.60.0.252/24")]},
    static=["0.0.0.0/0 10.0.100.254"],
    default_originate=True,
    ospf_exclude=["eth12"],
    vrrp=[("eth12", 10, "10.0.100.253/24", 120),
          ("eth13.70", 9, "10.60.0.1/24", 120)])

add_frr("core2", "10.255.0.2/32",
    ifs={
        "eth1": "10.0.10.5/30", "eth2": "10.0.20.5/30",
        "eth3": "10.0.30.5/30", "eth4": "10.0.40.5/30",
        "eth5": "10.0.50.5/30", "eth6": "10.0.10.13/30",
        "eth7": "10.0.20.13/30", "eth8": "10.0.30.13/30",
        "eth9": "10.0.40.13/30", "eth10": "10.0.50.13/30",
        "eth11": "10.0.0.2/30", "eth12": "10.0.100.2/24",
        "eth14": "10.0.0.6/30",
    },
    trunks={"eth13": [("70", "10.60.0.253/24")]},
    static=["0.0.0.0/0 10.0.100.254"],
    default_originate=True,
    ospf_exclude=["eth12"],
    vrrp=[("eth12", 10, "10.0.100.253/24", 100),
          ("eth13.70", 9, "10.60.0.1/24", 100)])

# ---------------- Teaching ----------------
add_frr("agg-t1", "10.255.0.11/32",
    ifs={"eth1": "10.0.10.2/30", "eth2": "10.0.10.6/30"},
    trunks={"eth3": [("101", "10.10.0.252/24"), ("500", "10.50.0.252/24")],
            "eth4": [("102", "10.10.1.252/24")]},
    vrrp=[("eth3.101", 1, "10.10.0.1/24", 120),
          ("eth3.500", 3, "10.50.0.1/24", 120),
          ("eth4.102", 2, "10.10.1.1/24", 120)])

add_frr("agg-t2", "10.255.0.12/32",
    ifs={"eth1": "10.0.10.10/30", "eth2": "10.0.10.14/30"},
    trunks={"eth3": [("101", "10.10.0.253/24"), ("500", "10.50.0.253/24")],
            "eth4": [("102", "10.10.1.253/24")]},
    vrrp=[("eth3.101", 1, "10.10.0.1/24", 100),
          ("eth3.500", 3, "10.50.0.1/24", 100),
          ("eth4.102", 2, "10.10.1.1/24", 100)])

# ---------------- Dorm ----------------
add_frr("agg-d1", "10.255.0.21/32",
    ifs={"eth1": "10.0.20.2/30", "eth2": "10.0.20.6/30"},
    trunks={"eth3": [("301", "10.32.0.252/24"), ("510", "10.51.0.252/24")]},
    vrrp=[("eth3.301", 4, "10.32.0.1/24", 120),
          ("eth3.510", 5, "10.51.0.1/24", 120)])

add_frr("agg-d2", "10.255.0.22/32",
    ifs={"eth1": "10.0.20.10/30", "eth2": "10.0.20.14/30"},
    trunks={"eth3": [("301", "10.32.0.253/24"), ("510", "10.51.0.253/24")]},
    vrrp=[("eth3.301", 4, "10.32.0.1/24", 100),
          ("eth3.510", 5, "10.51.0.1/24", 100)])

# ---------------- Lab ----------------
add_frr("agg-l1", "10.255.0.31/32",
    ifs={"eth1": "10.0.30.2/30", "eth2": "10.0.30.6/30"},
    trunks={"eth3": [("201", "10.20.0.252/24")]},
    vrrp=[("eth3.201", 6, "10.20.0.1/24", 120)])

add_frr("agg-l2", "10.255.0.32/32",
    ifs={"eth1": "10.0.30.10/30", "eth2": "10.0.30.14/30"},
    trunks={"eth3": [("201", "10.20.0.253/24")]},
    vrrp=[("eth3.201", 6, "10.20.0.1/24", 100)])

# ---------------- Library ----------------
add_frr("agg-lib1", "10.255.0.41/32",
    ifs={"eth1": "10.0.40.2/30", "eth2": "10.0.40.6/30"},
    trunks={"eth3": [("50", "10.55.0.252/24")]},
    vrrp=[("eth3.50", 7, "10.55.0.1/24", 120)])

add_frr("agg-lib2", "10.255.0.42/32",
    ifs={"eth1": "10.0.40.10/30", "eth2": "10.0.40.14/30"},
    trunks={"eth3": [("50", "10.55.0.253/24")]},
    vrrp=[("eth3.50", 7, "10.55.0.1/24", 100)])

# ---------------- Living ----------------
add_frr("agg-life1", "10.255.0.51/32",
    ifs={"eth1": "10.0.50.2/30", "eth2": "10.0.50.6/30"},
    trunks={"eth3": [("61", "10.64.0.252/24")]},
    vrrp=[("eth3.61", 8, "10.64.0.1/24", 120)])

add_frr("agg-life2", "10.255.0.52/32",
    ifs={"eth1": "10.0.50.10/30", "eth2": "10.0.50.14/30"},
    trunks={"eth3": [("61", "10.64.0.253/24")]},
    vrrp=[("eth3.61", 8, "10.64.0.1/24", 100)])

# ---------------- Edge routers ----------------
add_frr("r1", "10.255.0.101/32",
    ifs={"eth1": "10.90.1.1/24", "eth2": "203.0.113.1/24"},
    static=["0.0.0.0/0 203.0.113.100", "10.0.0.0/8 10.90.1.253"],
    ospf=False,
    vrrp=[("eth1", 11, "10.90.1.254/24", 120),
          ("eth2", 12, "203.0.113.254/24", 120)])

add_frr("r2", "10.255.0.102/32",
    ifs={"eth1": "10.90.1.2/24", "eth2": "203.0.113.2/24"},
    static=["0.0.0.0/0 203.0.113.100", "10.0.0.0/8 10.90.1.253"],
    ospf=False,
    vrrp=[("eth1", 11, "10.90.1.254/24", 100),
          ("eth2", 12, "203.0.113.254/24", 100)])

# ---------------- Access switches ----------------
ACCESS_NODES = {
    "acc-ta":  {"trunks": {"eth1": [101, 500], "eth2": [101, 500]},
                "access": {"eth3": 101, "eth4": 101, "eth5": 500}},
    "acc-tb":  {"trunks": {"eth1": [102], "eth2": [102]},
                "access": {"eth3": 102}},
    "acc-d1":  {"trunks": {"eth1": [301, 510], "eth2": [301, 510]},
                "access": {"eth3": 301, "eth4": 510}},
    "acc-la":  {"trunks": {"eth1": [201], "eth2": [201]},
                "access": {"eth3": 201}},
    "acc-lib": {"trunks": {"eth1": [50], "eth2": [50]},
                "access": {"eth3": 50}},
    "acc-life":{"trunks": {"eth1": [61], "eth2": [61]},
                "access": {"eth3": 61}},
    "dc-sw":   {"trunks": {"eth1": [70], "eth2": [70]},
                "access": {"eth3": 70, "eth4": 70}},
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
    # core-core (2 x 10G representation)
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
    ("acc-tb","eth3","pc-tb1","eth1"),
    ("acc-d1","eth3","pc-d1","eth1"), ("acc-d1","eth4","ap-d1","eth1"),
    ("acc-la","eth3","pc-la1","eth1"),
    ("acc-lib","eth3","pc-lib","eth1"),
    ("acc-life","eth3","pc-life","eth1"),
    ("dc-sw","eth3","srv-dc1","eth1"), ("dc-sw","eth4","srv-dc2","eth1"),
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
        for ifname, ip in all_ips(node).items():
            if ifname in node["ospf_exclude"]:
                continue
            lines.append(f" network {net(ip)} area 0")
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
    expected = list(node["ifs"].keys()) + list(node["trunks"].keys())
    for ifname in expected:
        lines.append(f"n=0; while [ ! -e /sys/class/net/{ifname} ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done")
    lines.append("ip route del default 2>/dev/null || true")
    lines.append("for i in $(ls /sys/class/net | grep '^eth'); do ip link set \"$i\" up 2>/dev/null || true; done")
    for parent, subs in node["trunks"].items():
        lines.append(f"ip link set {parent} up 2>/dev/null || true")
        for vid, ip in subs:
            lines.append(f"ip link add link {parent} name {parent}.{vid} type vlan id {vid} 2>/dev/null || true")
            lines.append(f"ip link set {parent}.{vid} up")
    lines.append("exit 0")
    return "\n".join(lines) + "\n"

def sanitize(s):
    return s.replace(".", "_").replace("-", "_")

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

def gen_host(name, ip, gw):
    lines = ["#!/bin/sh", "set -e",
             "ip link set eth1 up",
             f"ip addr replace {ip} dev eth1",
             f"ip route replace default via {gw}"]
    if name == "srv-dmz":
        # the Alpine base image has no httpd applet; serve the DMZ page with busybox nc.
        lines += [
            "mkdir -p /www", "echo 'DMZ server OK' > /www/index.html",
            "cat > /www/serve.sh <<'EOF'",
            "while true; do",
            "  printf 'HTTP/1.1 200 OK\\r\\nContent-Type: text/plain\\r\\nContent-Length: 13\\r\\nConnection: close\\r\\n\\r\\nDMZ server OK' | nc -l -p 80 -w 2",
            "done",
            "EOF",
            "sh /www/serve.sh >/var/log/dmz-http.log 2>&1 &",
        ]
    lines += ["exit 0", ""]
    return "\n".join(lines)

FW_NFT = """table inet fw {
  chain forward {
    type filter hook forward priority 0; policy drop;
    ct state established,related counter accept
    iifname "eth1" oifname "eth2" counter accept
    iifname "eth1" oifname "eth3" counter accept
    iifname "eth2" oifname "eth3" tcp dport { 80, 443 } counter accept
    iifname "eth2" oifname "eth1" counter drop
    iifname "eth3" oifname "eth1" counter drop
    iifname "eth3" oifname "eth2" counter drop
  }
  chain postrouting {
    type nat hook postrouting priority 100; policy accept;
    oifname "eth2" counter masquerade
  }
}
"""

def gen_fw(name, cfg):
    lines = ["#!/bin/sh", "set -e",
             "ip link set eth1 up", "ip link set eth2 up", "ip link set eth3 up"]
    for ifname, ip in cfg["ips"].items():
        lines.append(f"ip addr replace {ip} dev {ifname}")
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

# ---------------- Generate configs ----------------
shutil.rmtree(CFG, ignore_errors=True)
w(os.path.join(CFG, "frr", "daemons"), DAEMONS)

for name, node in FRR_NODES.items():
    d = os.path.join(CFG, "frr", name)
    w(os.path.join(d, "frr.conf"), gen_frr(name, node))
    w(os.path.join(d, "prestart.sh"), gen_prestart(node))
    w(os.path.join(d, "keepalived.conf"), gen_keepalived(name, node))

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

w(os.path.join(CFG, "fw", "fw.nft"), FW_NFT)
for name, cfg in FW_NODES.items():
    d = os.path.join(CFG, "fw", name)
    w(os.path.join(d, "setup.sh"), gen_fw(name, cfg))
    w(os.path.join(d, "keepalived.conf"), gen_fw_keepalived(cfg))


# ---------------- Draw.io layout levels ----------------
# Lower level = higher row in the vertical diagram. Grouping nodes into
# explicit levels keeps the diagram from packing unrelated layers together.
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
}
for _name in HOSTS:
    GRAPH_LEVELS.setdefault(_name, 9)


def graph_label_lines(name):
    level = GRAPH_LEVELS.get(name)
    if level is None:
        return []
    return ["      labels:", f"        graph-level: {level}"]

# ---------------- Generate topology ----------------
y = []
y.append("name: campus-lab")
y.append("mgmt:")
y.append("  network: campus_mgmt")
y.append("  ipv4-subnet: 172.31.100.0/24")
y.append("topology:")
y.append("  nodes:")

for name in FRR_NODES:
    y += [f"    {name}:",
          "      kind: linux",
          "      image: campus-frr:latest",
          "      binds:",
          "        - ./configs/frr/daemons:/etc/frr/daemons",
          f"        - ./configs/frr/{name}/frr.conf:/etc/frr/frr.conf",
          f"        - ./configs/frr/{name}/prestart.sh:/configs/prestart.sh",
          f"        - ./configs/frr/{name}/keepalived.conf:/configs/keepalived.conf"]
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
          "      image: alpine:3.24",
          "      cmd: sleep infinity",
          "      binds:",
          f"        - ./configs/hosts/{name}/setup.sh:/setup.sh",
          "      exec:",
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
