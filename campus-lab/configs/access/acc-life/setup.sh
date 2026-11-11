#!/bin/sh
set -e
ip link add br0 type bridge vlan_filtering 1 vlan_default_pvid 0 2>/dev/null || true
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
bridge vlan add dev eth1 vid 61
bridge vlan add dev eth2 vid 61
bridge vlan add dev eth3 vid 61 pvid untagged
exit 0
