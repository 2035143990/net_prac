#!/bin/sh
n=0; while [ ! -e /sys/class/net/eth1 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth2 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth3 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth4 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth5 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth6 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth7 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth8 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth9 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth10 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth12 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth13 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth11 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth14 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
modprobe bonding 2>/dev/null || true
ip link add bond0 type bond mode 802.3ad miimon 100 lacp_rate fast 2>/dev/null || ip link add bond0 type bond mode active-backup miimon 100 2>/dev/null || true
echo layer3+4 > /sys/class/net/bond0/bonding/xmit_hash_policy 2>/dev/null || true
ip link set eth11 down 2>/dev/null || true
ip link set eth11 master bond0 2>/dev/null || true
ip link set eth11 up 2>/dev/null || true
ip link set eth14 down 2>/dev/null || true
ip link set eth14 master bond0 2>/dev/null || true
ip link set eth14 up 2>/dev/null || true
ip link set bond0 up 2>/dev/null || true
ip route del default 2>/dev/null || true
for i in $(ls /sys/class/net | grep '^eth'); do ip link set "$i" up 2>/dev/null || true; done
ip link set eth13 up 2>/dev/null || true
ip link add link eth13 name eth13.70 type vlan id 70 2>/dev/null || true
ip link set eth13.70 up
ip link add link eth13 name eth13.90 type vlan id 90 2>/dev/null || true
ip link set eth13.90 up
nft delete table inet zone 2>/dev/null || true
nft -f /configs/acl.nft 2>/dev/null || true
cp /configs/keepalived.conf /etc/keepalived.conf 2>/dev/null || true
chmod 0644 /etc/keepalived.conf 2>/dev/null || true
exit 0
