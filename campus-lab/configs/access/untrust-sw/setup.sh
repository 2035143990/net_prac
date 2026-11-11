#!/bin/sh
set -e
ip link add br0 type bridge 2>/dev/null || true
ip link set br0 up
ip link set eth1 up
ip link set eth1 master br0 2>/dev/null || true
ip link set eth2 up
ip link set eth2 master br0 2>/dev/null || true
ip link set eth3 up
ip link set eth3 master br0 2>/dev/null || true
ip link set eth4 up
ip link set eth4 master br0 2>/dev/null || true
exit 0
