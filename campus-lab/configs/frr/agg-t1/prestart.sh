#!/bin/sh
n=0; while [ ! -e /sys/class/net/eth1 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth2 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth3 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth4 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
ip route del default 2>/dev/null || true
for i in $(ls /sys/class/net | grep '^eth'); do ip link set "$i" up 2>/dev/null || true; done
ip link set eth3 up 2>/dev/null || true
ip link add link eth3 name eth3.101 type vlan id 101 2>/dev/null || true
ip link set eth3.101 up
ip link add link eth3 name eth3.500 type vlan id 500 2>/dev/null || true
ip link set eth3.500 up
ip link set eth4 up 2>/dev/null || true
ip link add link eth4 name eth4.102 type vlan id 102 2>/dev/null || true
ip link set eth4.102 up
nft delete table inet zone 2>/dev/null || true
nft -f /configs/acl.nft 2>/dev/null || true
exit 0
