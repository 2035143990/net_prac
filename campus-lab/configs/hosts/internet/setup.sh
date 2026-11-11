#!/bin/sh
set -e
ip link set eth1 up
ip addr replace 203.0.113.100/24 dev eth1
ip route replace default via 203.0.113.254
ip route replace 198.51.100.80/32 via 203.0.113.254
exit 0
