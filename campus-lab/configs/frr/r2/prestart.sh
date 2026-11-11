#!/bin/sh
n=0; while [ ! -e /sys/class/net/eth1 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth2 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
ip route del default 2>/dev/null || true
for i in $(ls /sys/class/net | grep '^eth'); do ip link set "$i" up 2>/dev/null || true; done
exit 0
