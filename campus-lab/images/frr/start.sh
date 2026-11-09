#!/bin/sh
set -e
mkdir -p /var/run/frr /var/log/frr
chown -R frr:frr /var/run/frr /var/log/frr 2>/dev/null || true
sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1 || true
sysctl -w net.ipv4.conf.all.rp_filter=0 >/dev/null 2>&1 || true
sysctl -w net.ipv4.igmp_max_memberships=200 >/dev/null 2>&1 || true
sysctl -w net.ipv4.igmp_max_msf=200 >/dev/null 2>&1 || true
if [ -f /configs/prestart.sh ]; then
  sh /configs/prestart.sh
fi
/usr/lib/frr/frrinit.sh start >/var/log/frr/start.log 2>&1 || true
sleep 3
if [ -f /configs/acl.nft ]; then
  nft delete table inet zone 2>/dev/null || true
  nft -f /configs/acl.nft >/var/log/frr/acl.log 2>&1 || true
fi
if [ -f /configs/keepalived.conf ]; then
  keepalived -D -f /configs/keepalived.conf >/var/log/keepalived.log 2>&1 || true
fi
if [ -f /configs/start-services.sh ]; then
  sh /configs/start-services.sh || true
fi
exec sleep infinity