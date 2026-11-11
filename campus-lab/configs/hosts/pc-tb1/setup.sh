#!/bin/sh
set -e
ip link set eth1 up
ip addr replace 10.10.1.11/24 dev eth1
ip route replace default via 10.10.1.1
exit 0
