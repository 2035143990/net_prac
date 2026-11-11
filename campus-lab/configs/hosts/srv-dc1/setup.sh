#!/bin/sh
set -e
n=0; while [ ! -e /sys/class/net/eth1 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth2 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
ip link set eth1 down 2>/dev/null || true
ip link set eth2 down 2>/dev/null || true
ip link add bond0 type bond mode active-backup miimon 100 primary eth1 2>/dev/null || true
if ip link show bond0 >/dev/null 2>&1; then
  ip link set eth1 master bond0 2>/dev/null || true
  ip link set eth2 master bond0 2>/dev/null || true
  ip link set eth1 up 2>/dev/null || true
  ip link set eth2 up 2>/dev/null || true
  ip link set bond0 up
  ip addr replace 10.60.0.10/24 dev bond0
else
  ip link set eth1 up
  ip addr replace 10.60.0.10/24 dev eth1
fi
ip route replace default via 10.60.0.1
dnsmasq -C /configs/dnsmasq.conf >/var/log/dnsmasq.log 2>&1 &
exit 0
