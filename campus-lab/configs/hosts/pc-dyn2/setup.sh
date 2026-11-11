#!/bin/sh
set -e
n=0; while [ ! -e /sys/class/net/eth1 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth2 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
ip link set eth1 down
ip link set eth1 address 02:00:00:00:01:02
ip link set eth1 up
chmod +x /configs/udhcpc.sh
udhcpc -i eth1 -s /configs/udhcpc.sh -b -t 60 -T 3 >/var/log/udhcpc.log 2>&1 &
exit 0
