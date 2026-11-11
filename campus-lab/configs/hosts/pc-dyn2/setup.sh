#!/bin/sh
set -e
ip link set eth1 down
ip link set eth1 address 02:00:00:00:01:02
ip link set eth1 up
chmod +x /configs/udhcpc.sh
udhcpc -i eth1 -s /configs/udhcpc.sh -b -t 60 -T 3 >/var/log/udhcpc.log 2>&1 &
exit 0
