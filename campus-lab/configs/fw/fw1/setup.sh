#!/bin/sh
set -e
ip link set eth1 up
ip link set eth2 up
ip link set eth3 up
ip addr replace 10.0.100.11/24 dev eth1
ip addr replace 10.90.1.11/24 dev eth2
ip addr replace 10.80.0.11/24 dev eth3
ip route replace default via 10.90.1.254
ip route replace 10.0.0.0/8 via 10.0.100.253
sysctl -w net.ipv4.ip_forward=1 >/dev/null
sysctl -w net.ipv4.conf.all.rp_filter=0 >/dev/null
nft delete table inet fw 2>/dev/null || true
nft -f /configs/fw.nft
keepalived -D -f /configs/keepalived.conf >/var/log/keepalived.log 2>&1 &
exit 0
