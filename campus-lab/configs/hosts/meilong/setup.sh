#!/bin/sh
set -e
n=0; while [ ! -e /sys/class/net/eth1 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth2 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
ip link set eth1 up
ip addr replace 10.91.1.2/30 dev eth1
ip route replace default via 10.91.1.1
ip link set eth2 up
ip addr replace 10.91.0.1/24 dev eth2
ip route replace 10.0.0.0/8 via 10.91.1.1
sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1 || true
exit 0
