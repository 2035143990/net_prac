# 奉贤校区校园网 Containerlab 仿真

基于《奉贤校区校园网设计方案》构建的可运行校园网拓扑：双核心、分区域双汇聚、VLAN 接入、OSPF 动态路由、VRRP 网关冗余、DHCP 集中地址服务与区域 Relay、宿舍区访问控制、Trust/Untrust/DMZ 三区防火墙、源 NAT 与 DMZ 目的 NAT、核心与服务器链路聚合。

拓扑共 **44 个容器、66 条链路**，部署后可直接进行层二/层三转发、跨区域访问、地址自动配置、Internet 访问、DMZ 发布和故障切换实验。节点数、链路数、VLAN 与地址池以 `configs/facts.json` 为准，本文数字由 `gen.py` 生成口径同步。

## 1. 目录结构

```text
campus-lab/
├─ campus-lab.clab.yml     # 由 gen.py 生成的 Containerlab 拓扑
├─ gen.py                  # 拓扑与全部节点配置的生成器（单一事实源）
├─ gen-drawio.sh           # 生成分层 draw.io 拓扑图并优化可读性
├─ drawio-postprocess.py   # draw.io 后处理，替换条数异常时非零退出
├─ build-images.sh         # 一键构建四个本地镜像并检查 dnsmasq 版本
├─ run-clab.sh             # macOS 下无 TTY 运行 containerlab 的包装脚本
├─ images/
│  ├─ frr/                 # Alpine + FRRouting + keepalived + nftables + dnsmasq
│  ├─ l2/                  # Alpine + iproute2 二层/三层交换机镜像
│  ├─ fw/                  # Alpine + nftables + keepalived + conntrack-tools
│  └─ host/                # Alpine + iproute2 + dnsmasq 终端/服务器镜像
├─ configs/
│  ├─ frr/                 # 14 台 FRR 节点的 frr.conf / prestart / keepalived
│  │                       # 汇聚节点另有 acl.nft、dhcp-relay.conf、start-services.sh
│  ├─ access/              # 7 台接入/汇聚二层交换机的 VLAN 脚本
│  ├─ fw/                  # fw1/fw2 启动脚本、nftables 规则、VRRP
│  ├─ hosts/               # 17 台终端/服务器的地址、DHCP 客户端、dnsmasq 配置
│  └─ facts.json           # 生成期事实快照，测试与报告读取
├─ tests/
│  ├─ lib.sh               # 断言、编号、JSONL 结果库
│  ├─ cases.tsv            # 64 条用例清单
│  ├─ run-all.sh           # 统一 runner，退出码 0/1/2
│  ├─ connectivity.sh      # CONN-01~10
│  ├─ routing.sh           # ROUTE-01~08
│  ├─ security.sh          # SEC-01~06
│  ├─ dhcp.sh              # DHCP-01~08
│  ├─ iso.sh               # ISO-01~12
│  ├─ nat.sh               # NAT-01~07
│  ├─ lag.sh               # LAG-01~07
│  └─ failover.sh          # FAIL-01~06
├─ ../docs/course-report-draft.md
├─ ../tools/report_check.py
└─ README.md
```

说明：`configs/`、`campus-lab.clab.yml` 与 `configs/facts.json` 均由 `gen.py` 生成。修改设计时请改 `gen.py` 后重新生成，不要直接手改生成物。`facts.json` 含 `generated_at`，幂等比对时应排除该文件。

## 2. 节点与冗余设计

| 层次 | 节点 | 说明 |
| --- | --- | --- |
| 核心 | `core1` `core2` | FRR，OSPF Area 0，核心间 `bond0` 802.3ad 聚合；Trust、VLAN 70、VLAN 90 提供 VRRP VIP |
| 教学区汇聚 | `agg-t1` `agg-t2` | 上联双核心，下联 `acc-ta` / `acc-tb`，VRRP 网关，DHCP Relay，区域 ACL |
| 宿舍区汇聚 | `agg-d1` `agg-d2` | 上联双核心，下联 `acc-d1`，VRRP 网关，DHCP Relay，宿舍专用 ACL |
| 实验区汇聚 | `agg-l1` `agg-l2` | 上联双核心，下联 `acc-la`，VRRP 网关，DHCP Relay，区域 ACL |
| 图书馆汇聚 | `agg-lib1` `agg-lib2` | 上联双核心，下联 `acc-lib`，VRRP 网关，DHCP Relay |
| 生活区汇聚 | `agg-life1` `agg-life2` | 上联双核心，下联 `acc-life`，VRRP 网关，DHCP Relay |
| 接入/二层 | `acc-ta` `acc-tb` `acc-d1` `acc-la` `acc-lib` `acc-life` `dc-sw` | Linux VLAN-filtering bridge，Trunk + Access 端口 |
| 边界防火墙 | `fw1` `fw2` | nftables 三区策略、SNAT、DMZ DNAT、VRRP 双机热备 |
| 出口路由 | `r1` `r2` | 连接 Untrust 与模拟 Internet，静态路由 + VRRP |
| 传输二层 | `trust-sw` `untrust-sw` `dmz-sw` `inet-sw` | Trust / Untrust / DMZ / Internet 汇聚二层转发 |
| 终端 | `pc-*` `ap-*` `srv-*` `mgmt-pc` `internet` | 17 台 Alpine 终端/服务器，3 台动态终端 |

路由：核心、汇聚之间运行 OSPF（Area 0），核心向 OSPF 注入默认路由；`r1/r2` 使用静态路由，并配置经对端出口路由器的浮动默认路由（管理距离 200），作为主 Internet 链路故障时的备份路径。核心间聚合后只有一条逻辑邻居，`core1/core2` 的 OSPF Full 邻居数为 **11**。

安全：`fw1/fw2` 上 Trust 可访问 Untrust/DMZ；Untrust 仅可通过发布地址 `198.51.100.80` 的 DNAT 访问 DMZ 的 TCP 80/443；Untrust→Trust、DMZ→Trust 默认丢弃；Trust→Untrust 出方向做源 NAT。宿舍区 10.32.0.0/24 与 10.51.0.0/24 在 `agg-d1/agg-d2` 上通过 nftables 阻断到管理网、教学区（含有线/无线）、实验区、图书馆、数据中心、生活区及校内/出口互联和环回网段的访问，仅放行宿舍互访、DNS、Internet 与 DMZ 发布服务；`core1/core2` 另外阻断所有用户区域到管理网、校内/出口互联和环回网段的访问，并阻断教学/实验区到宿舍区的访问；管理网 10.70.0.0/24 不允许主动访问 Untrust，且仅运维可达。ACL 首条规则为 `ct state established,related accept`；由于双汇聚/双核心节点之间未部署 conntrack 状态同步，ACL 还显式放行受限区域发出的 ICMP echo-reply 以及 TCP 非纯 SYN 报文（含 ACK、SYN-ACK），避免非对称路径误伤回程流量。

## 3. VLAN 与地址规划

### 3.1 业务 VLAN

| VLAN | 用途 | 网段 | 网关 VIP | 代表终端 |
| --- | --- | --- | --- | --- |
| 101 | 教学区有线 | 10.10.0.0/24 | 10.10.0.1 | `pc-ta1` 10.10.0.11 / `pc-dyn1` 动态 |
| 102 | 教学区有线 | 10.10.1.0/24 | 10.10.1.1 | `pc-tb1` 10.10.1.11 |
| 500 | 教学区无线 | 10.50.0.0/24 | 10.50.0.1 | `ap-ta` 10.50.0.11 / `pc-dyn3` 动态 |
| 201 | 实验区 | 10.20.0.0/24 | 10.20.0.1 | `pc-la1` 10.20.0.11 |
| 301 | 宿舍区有线 | 10.32.0.0/24 | 10.32.0.1 | `pc-d1` 10.32.0.11 / `pc-dyn2` 动态 |
| 510 | 宿舍区无线 | 10.51.0.0/24 | 10.51.0.1 | `ap-d1` 10.51.0.11 |
| 50 | 图书馆 | 10.55.0.0/24 | 10.55.0.1 | `pc-lib` 10.55.0.11 |
| 61 | 生活区 | 10.64.0.0/24 | 10.64.0.1 | `pc-life` 10.64.0.11 |
| 70 | 数据中心 | 10.60.0.0/24 | 10.60.0.1 | `srv-dc1` 10.60.0.10 / `srv-dc2` 10.60.0.11 |
| 80 | DMZ | 10.80.0.0/24 | 10.80.0.1 | `srv-dmz` 10.80.0.10 |
| 90 | 管理网 | 10.70.0.0/24 | 10.70.0.1 | `mgmt-pc` 10.70.0.10 |

每个业务 VLAN 由对应汇聚对提供 VRRP 虚拟网关；数据中心 VLAN 70 与管理 VLAN 90 由 `core1/core2` 直接提供网关。

### 3.2 互联与出口地址

| 链路 | 网段 | 主要地址 |
| --- | --- | --- |
| 核心聚合互联 | 10.0.0.0/30 | core1 10.0.0.1，core2 10.0.0.2（bond0） |
| 教学区上联 | 10.0.10.0/30 ~ 10.0.10.12/30 | 核心与 agg-t1/t2 各两条 /30 |
| 宿舍区上联 | 10.0.20.0/30 ~ 10.0.20.12/30 | 核心与 agg-d1/d2 各两条 /30 |
| 实验区上联 | 10.0.30.0/30 ~ 10.0.30.12/30 | 核心与 agg-l1/l2 各两条 /30 |
| 图书馆上联 | 10.0.40.0/30 ~ 10.0.40.12/30 | 核心与 agg-lib1/lib2 各两条 /30 |
| 生活区上联 | 10.0.50.0/30 ~ 10.0.50.12/30 | 核心与 agg-life1/life2 各两条 /30 |
| Trust | 10.0.100.0/24 | 核心 VIP .253，防火墙 VIP .254，fw1 .11，fw2 .12 |
| Untrust | 10.90.1.0/24 | 出口路由 VIP .254，防火墙 VIP .253，r1 .1，r2 .2 |
| Internet | 203.0.113.0/24 | `internet` .100，r1/r2 VRRP .254 |
| 对外发布 VIP | 198.51.100.80/32 | Untrust 侧 VRRP 附加虚拟地址（主防火墙持有），TCP 80/443 DNAT 到 10.80.0.10 |
| 管理网 | 172.31.100.0/24 | 由 Containerlab 自动分配，仅带外管理；校园管理 VLAN 90 为 10.70.0.0/24 |

VRRP 采用 keepalived 实现，主节点优先级 120、备节点 100，主节点故障后备节点自动接管 VIP；主节点恢复后重新抢占。

### 3.3 DHCP 地址池

DHCP 服务器为 `srv-dc1`（10.60.0.10），dnsmasq 同时提供 DNS；10 台区域汇聚运行 DHCP Relay。动态池统一 `.100-.200`，保留地址 `.1-.11` 不分配。

| VLAN | 池范围 | 租期 |
| --- | --- | --- |
| 101/102/500 | 对应网段 .100-.200 | 14400 秒（4 小时） |
| 301/510 | 对应网段 .100-.200 | 43200 秒（12 小时） |
| 201 | 对应网段 .100-.200 | 28800 秒（8 小时） |
| 50/61 | 对应网段 .100-.200 | 28800 秒（8 小时） |

动态终端：`pc-dyn1`（VLAN 101）、`pc-dyn2`（VLAN 301）、`pc-dyn3`（VLAN 500）。静态终端保留作为对照。

## 4. 构建与部署

### 4.1 前置条件

- Docker Desktop（macOS）已运行，建议分配至少 **4 GB 内存、4 CPU**；44 个节点启动阶段峰值较高；
- 项目目录位于 Docker Desktop 的共享路径下（默认的 `/Users/...` 即可）；
- 首次构建时需要能访问 `ghcr.io`、Docker Hub（`alpine:3.24`）和 `mirrors.aliyun.com`；
- 本机有 `python3`（仅使用标准库，无需 pip 安装依赖）；
- 可运行官方 `ghcr.io/srl-labs/clab` 容器（或本机原生安装 containerlab）。

### 4.2 从零复原检查清单

1. **构建四个本地镜像**：

   ```sh
   sh build-images.sh
   ```

   脚本会检查本地是否已有 `alpine:3.24`，随后构建 `campus-frr`、`campus-l2`、`campus-fw`、`campus-host`，并检查 dnsmasq 版本不低于 2.86（`dhcp-relay` 选项要求）。低于门槛时脚本非零退出。

2. **生成拓扑与配置**：

   ```sh
   python3 gen.py
   ```

   预期输出：

   ```text
   generated 14 frr, 7 l2, 17 hosts, 2 fw, 4 bridges
   total nodes: 44
   links: 66
   ```

3. **部署**：

   ```sh
   sh run-clab.sh deploy -t campus-lab.clab.yml
   ```

4. **等待收敛后运行测试**（见第 5 节）。

镜像基于 `alpine:3.24`，使用阿里云 Alpine 镜像源安装 `frr`、`iproute2`、`nftables`、`keepalived`、`dnsmasq`、`conntrack-tools` 等软件，适用于 arm64 与 amd64。若构建时软件源不可用，可修改各 `Dockerfile` 中的 `apk` 源地址。

### 4.3 部署后确认

```sh
docker ps --filter name=clab-campus-lab- --format '{{.Names}}' | wc -l   # 应为 44
docker exec clab-campus-lab-core1 vtysh -c 'show ip ospf neighbor'        # 应为 11 条 Full
docker exec clab-campus-lab-core1 cat /proc/net/bonding/bond0             # 两个成员均 up
docker exec clab-campus-lab-srv-dc1 pgrep -a dnsmasq                      # DHCP/DNS 进程
docker exec clab-campus-lab-agg-d1 pgrep -a dnsmasq                       # Relay 进程
```

### 4.4 导出拓扑图（draw.io）

```sh
sh gen-drawio.sh
```

`drawio-postprocess.py` 现在对接口标签删除数、链路样式替换数、节点坐标缩放数分别校验；任一类为 0 时非零退出，避免上游格式变化后静默失效。

### 4.5 销毁与文件清理

```sh
sh run-clab.sh destroy -t campus-lab.clab.yml --cleanup
```

`destroy` 只清理容器、veth 和 Containerlab 网络，不会删除工程目录中的生成物。需要彻底清理时：

```sh
rm -f campus-lab.clab.drawio
rm -rf clab-campus-lab/
find . -name .DS_Store -delete
rm -rf configs campus-lab.clab.yml
```

## 5. 验证测试

部署完成后执行统一入口：

```sh
sh tests/run-all.sh
```

也可单独执行某个套件：

```sh
sh tests/connectivity.sh
sh tests/routing.sh
sh tests/security.sh
sh tests/dhcp.sh
sh tests/iso.sh
sh tests/nat.sh
sh tests/lag.sh
sh tests/failover.sh
```

### 5.1 用例与结果

| 套件 | 用例 | 内容 |
| --- | --- | --- |
| CONN | CONN-01~10 | 同 VLAN、跨 VLAN、跨区域（教学/实验→宿舍 ACL 阻断）、无线、NAT、DMZ |
| ROUTE | ROUTE-01~08 | OSPF 邻居（11）、OSPF 路由、默认路由、VRRP VIP |
| SEC | SEC-01~06 | Internet→DMZ 放行、Internet→内网阻断、私网直达阻断、计数器 |
| DHCP | DHCP-01~08 | 三台动态终端取址、网关、DNS、租期、Relay、租约文件 |
| ISO | ISO-01~12 | 宿舍→管理/教学/实验/数据中心阻断，宿舍互访与 Internet/DMZ 放行，管理源放行，计数器 |
| NAT | NAT-01~07 | 公网地址 80/443、未发布端口、私网直达、DNAT/SNAT/丢弃计数 |
| LAG | LAG-01~07 | bond 模式、成员状态、单逻辑地址、OSPF 单邻居、服务器聚合、成员故障 |
| FAIL | FAIL-01~06 | core VRRP 切换、上联故障恢复、fw1 切换、邻居恢复 |

结果写入 `tests/results/<run-id>/`：

- `results.jsonl`：一行一个用例，含 `id`、`status`、`expected`、`actual`、`cmd`、`ms`；
- `summary.txt`：总计与各套件通过/失败/跳过；
- `raw/<id>.log`：命令原始输出。

退出码：`0` 全部通过或跳过；`1` 存在失败；`2` 环境不可用（Docker 未启动、容器数不足、facts 缺失）。

### 5.2 能力开关与 SKIP

`configs/facts.json` 的 `capabilities` 为 `dhcp/acl/dnat/lag/report`。能力为 `false` 时对应套件 SKIP；能力为 `true` 但断言失败必须 FAIL，不得跳过。

### 5.3 实测状态（2026-11-08）

首次全量运行 run-id `20261108T115247Z` 结果为 **61/64 通过、3 失败**：

| 套件 | 通过/总数 | 失败项 |
| --- | --- | --- |
| CONN | 10/10 | — |
| ROUTE | 8/8 | — |
| SEC | 6/6 | — |
| DHCP | 8/8 | — |
| ISO | 11/12 | ISO-09 |
| NAT | 7/7 | — |
| LAG | 7/7 | — |
| FAIL | 4/6 | FAIL-04、FAIL-06 |

3 项失败均已定位并修复：DHCP 脚本执行权限、Relay 早于路由收敛、核心 ACL 加载不完整、管理回程不对称、OSPF 恢复等待窗口。修复后完成关键路径复核，但**未重跑 64 条全量回归**。详细证据见 `../docs/verification-report.md`。答辩前应重新执行 `sh tests/run-all.sh` 并用新 run-id 替换本节数据。

## 6. 注意事项

1. **不要在部署后直接 `docker restart` 某个节点**。Containerlab 的 veth 链路位于容器网络命名空间中，单纯重启 Docker 容器会丢失数据接口。故障实验后若要恢复，执行一次完整 `destroy` + `deploy`。
2. **重新运行 `gen.py` 后应重新部署**。Docker Desktop 对单文件 bind mount 使用固定 inode，宿主机重写配置文件后，运行中的容器可能仍看到旧文件甚至报 `No such file or directory`。
3. **管理网默认路由**：节点启动时保留了 Containerlab 管理网卡 `eth0`，但 `prestart.sh` 会删除管理网默认路由，确保数据面默认路由生效。
4. **链路聚合依赖内核 bonding**：核心使用 802.3ad，服务器使用 active-backup。若容器内核或 veth 不支持 LACP，`prestart.sh` 会回退 active-backup，测试 LAG-01 将 FAIL；报告中应如实记录该限制。
5. **DHCP Relay 依赖 dnsmasq >= 2.86**：构建脚本已检查版本。双汇聚同时运行 relay，服务器按 MAC 复用租约；需在实测中确认无重复分配。
6. **DMZ 443 不做 TLS**：`srv-dmz` 用 busybox `nc` 返回明文 banner，仅验证端口映射与策略。
7. **无线部分为逻辑验证**：VLAN 500/510 模拟无线业务网段，未模拟射频、信道、关联与漫游。
8. **测试脚本依赖容器名前缀** `clab-campus-lab-`；如修改拓扑 `name`，需同步调整 `tests/lib.sh` 的 `P` 变量。
9. **报告与事实一致性**：修改 `gen.py` 后重新生成 `facts.json`，并执行：

   ```sh
   cd net_prac
   python3 tools/report_check.py
   ```
10. **幂等校验排除 facts.json**：`facts.json` 含 `generated_at`，两次生成的 SHA 比对应排除该文件。