#!/bin/sh
set -e
n=0; while [ ! -e /sys/class/net/eth1 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth2 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth3 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
ip link add br0 type bridge stp_state 1 2>/dev/null || true
ip link set br0 up
ip link set eth1 up
ip link set eth1 master br0 2>/dev/null || true
ip link set eth2 up
ip link set eth2 master br0 2>/dev/null || true
ip link set eth3 up
ip link set eth3 master br0 2>/dev/null || true
exit 0
