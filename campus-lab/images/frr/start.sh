#!/bin/sh
# FRR 路由节点启动入口。
#
# 原因同 images/l2/start.sh：containerlab 的 exec 只在 deploy 时跑一次，
# 容器 restart 后 OSPF/VRRP/静态路由、ACL 规则都会丢失。
#
# 挂载点约定：
#   /configs/prestart.sh      接口/静态路由/默认路由准备（由 gen.py 生成）
#   /configs/keepalived.conf  VRRP 配置
#   /configs/acl.nft          nftables 访问控制
#   /configs/start-services.sh DHCP Relay 等附加服务
#   /configs/rates/*.rates    本节点的链路速率台账（由 gen.py 生成）
#   /configs/apply-rates.sh   链路速率施加脚本
set -e

# 传入命令参数时直接执行该命令，不进入常驻模式。
# build-images.sh 用 `docker run --rm <image> dnsmasq --version` 校验镜像内
# 工具版本，若入口忽略参数会永远 sleep，校验脚本将挂死。
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

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

# 施加链路速率（containerlab 不支持原生带宽参数，用 tc/netem 实际限速）。
# 放在最后：此时接口已 up、静态路由已就绪，限速才能覆盖全部流量。
if [ -f /configs/apply-rates.sh ]; then
  RATES_FILE="/configs/rates/$(cat /etc/hostname 2>/dev/null).rates"
  if [ -f "$RATES_FILE" ]; then
    sh /configs/apply-rates.sh "$RATES_FILE" || true
  fi
fi

exec sleep infinity
