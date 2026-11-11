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
  # keepalived 拒绝加载带可执行位的配置文件。该文件来自 /mnt/d 的 bind mount，
  # 权限为 0777，必须先复制到容器本地文件系统并去掉可执行位。
  cp /configs/keepalived.conf /etc/keepalived.conf 2>/dev/null || true
  chmod 0644 /etc/keepalived.conf 2>/dev/null || true
  # 先清理可能残留的旧实例：容器重启后旧实例若仍在，会与新实例同时
  # 把 VIP 装到内核上，形成 VRRP 双主、ARP 冲突、流量黑洞。
  pkill -x keepalived 2>/dev/null || true
  sleep 1
  keepalived -D -f /etc/keepalived.conf >/var/log/keepalived.log 2>&1 || true
fi
if [ -f /configs/start-services.sh ]; then
  sh /configs/start-services.sh || true
fi
exec sleep infinity
