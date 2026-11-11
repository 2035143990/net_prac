#!/bin/sh
case "$1" in
  deconfig)
    ip addr flush dev "$interface" 2>/dev/null || true
    ip link set "$interface" up
    ;;
  bound|renew)
    ip link set "$interface" up
    ip addr replace "$ip/${mask:-255.255.255.0}" dev "$interface"
    set -- $router
    [ -n "$1" ] && ip route replace default via "$1"
    {
      echo "ip=$ip"
      echo "subnet=$mask"
      echo "router=$router"
      echo "dns=$dns"
      echo "lease=$lease"
      echo "server=$serverid"
    } > /tmp/dhcp.env
    ;;
esac
exit 0
