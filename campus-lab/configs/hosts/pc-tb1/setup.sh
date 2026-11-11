#!/bin/sh
set -e
ip link set eth1 up
ip addr replace 10.11.0.11/24 dev eth1
ip route replace default via 10.11.0.1
exit 0
