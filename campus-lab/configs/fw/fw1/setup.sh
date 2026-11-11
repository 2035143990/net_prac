#!/bin/sh
set -e
n=0; while [ ! -e /sys/class/net/eth1 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth2 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth3 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
ip link set eth1 up
ip link set eth2 up
ip link set eth3 up
ip addr replace 10.0.100.11/24 dev eth1
ip addr replace 10.90.1.11/24 dev eth2
ip addr replace 10.80.0.11/24 dev eth3
ip route replace default via 10.90.1.254
ip route replace 10.0.0.0/8 via 10.0.100.253
ip route replace 10.91.0.0/16 via 10.90.1.254
sysctl -w net.ipv4.ip_forward=1 >/dev/null
sysctl -w net.ipv4.conf.all.rp_filter=0 >/dev/null
nft delete table inet fw 2>/dev/null || true
nft -f /configs/fw.nft
pkill -x keepalived 2>/dev/null || true
sleep 1
cp /configs/keepalived.conf /etc/keepalived.conf 2>/dev/null || true
chmod 0644 /etc/keepalived.conf 2>/dev/null || true
keepalived -D -f /etc/keepalived.conf >/var/log/keepalived.log 2>&1 &
exit 0
