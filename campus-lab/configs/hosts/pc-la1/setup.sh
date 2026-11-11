#!/bin/sh
set -e
n=0; while [ ! -e /sys/class/net/eth1 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth2 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
ip link set eth1 up
ip addr replace 10.20.0.11/24 dev eth1
ip route replace default via 10.20.0.1
exit 0
