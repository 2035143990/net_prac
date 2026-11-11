#!/bin/sh
set -u
log=/var/log/frr/services.log
: > "$log"
i=0; ready=0
while [ $i -lt 60 ] && [ $ready -eq 0 ]; do
  ready=1
  for dev in eth3.201; do
    ip -4 addr show dev "$dev" 2>/dev/null | grep -q 'inet ' || ready=0
  done
  i=$((i+1))
  [ $ready -eq 1 ] || sleep 0.5
done
if [ $ready -eq 0 ]; then echo 'SVI not ready' >> "$log"; exit 0; fi
if [ -f /configs/acl.nft ]; then
  nft delete table inet zone 2>/dev/null || true
  nft -f /configs/acl.nft >> "$log" 2>&1 || echo 'acl load failed' >> "$log"
fi
i=0; routed=0
while [ $i -lt 240 ]; do ip route get 10.60.0.10 >/dev/null 2>&1 && routed=1 && break; i=$((i+1)); sleep 0.5; done
[ $routed -eq 1 ] || echo 'route to 10.60.0.10 not ready' >> "$log"
if [ -f /configs/dhcp-relay.conf ]; then
  if [ $routed -eq 1 ]; then
    dnsmasq -C /configs/dhcp-relay.conf >> "$log" 2>&1 && echo 'dhcp relay started' >> "$log" || echo 'dhcp relay failed' >> "$log"
  else
    (
      while true; do
        if ip route get 10.60.0.10 >/dev/null 2>&1; then
          dnsmasq -C /configs/dhcp-relay.conf >> "$log" 2>&1 && echo 'dhcp relay started late' >> "$log" && break
        fi
        sleep 2
      done
    ) &
    echo 'dhcp relay deferred' >> "$log"
  fi
fi
exit 0
