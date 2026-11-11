#!/bin/sh
set -e
n=0; while [ ! -e /sys/class/net/eth1 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth2 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth3 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
ip link add br0 type bridge vlan_filtering 1 vlan_default_pvid 0 stp_state 1 2>/dev/null || true
ip link set br0 up
ip link set eth1 up
ip link set eth1 master br0 2>/dev/null || true
bridge vlan del dev eth1 vid 1 2>/dev/null || true
ip link set eth2 up
ip link set eth2 master br0 2>/dev/null || true
bridge vlan del dev eth2 vid 1 2>/dev/null || true
ip link set eth3 up
ip link set eth3 master br0 2>/dev/null || true
bridge vlan del dev eth3 vid 1 2>/dev/null || true
bridge vlan add dev eth1 vid 102
bridge vlan add dev eth2 vid 102
bridge vlan add dev eth3 vid 102 pvid untagged
exit 0
