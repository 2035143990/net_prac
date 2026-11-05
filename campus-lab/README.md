# 奉贤校区校园网 Containerlab 仿真

基于《奉贤校区校园网设计方案》构建的可运行校园网拓扑：双核心、分区域双汇聚、VLAN 接入、OSPF 动态路由、VRRP 网关冗余、Trust/Untrust/DMZ 防火墙与 NAT。

拓扑共 **40 个容器、61 条链路**，部署后可直接进行层二/层三转发、跨区域访问、Internet 访问、DMZ 发布和故障切换实验。

## 1. 目录结构

```text
campus-lab/
├─ campus-lab.clab.yml     # 由 gen.py 生成的 Containerlab 拓扑
├─ gen.py                  # 拓扑与全部节点配置的生成器
├─ gen-drawio.sh           # 生成分层 draw.io 拓扑图并优化可读性
├─ drawio-postprocess.py   # draw.io 后处理：加行距、去接口标签、淡化链路
├─ build-images.sh         # 一键构建三个本地镜像
├─ run-clab.sh             # macOS 下无 TTY 运行 containerlab 的包装脚本
├─ images/
│  ├─ frr/                 # Alpine + FRRouting + keepalived 路由节点镜像
│  ├─ l2/                  # Alpine + iproute2 二层/三层交换机镜像
│  └─ fw/                  # Alpine + nftables + keepalived 防火墙镜像
├─ configs/
│  ├─ frr/                 # 14 台 FRR 节点的 frr.conf / prestart / keepalived
│  ├─ access/              # 7 台接入/汇聚二层交换机的 VLAN 脚本
│  ├─ fw/                  # fw1/fw2 启动脚本、nftables 规则、VRRP
│  └─ hosts/               # 13 台终端/服务器的地址与默认路由脚本
├─ tests/                  # 连通性、路由、安全、故障切换测试
└─ README.md
```

说明：`configs/` 和 `campus-lab.clab.yml` 均由 `gen.py` 生成。修改设计时请改 `gen.py` 后重新生成，不要直接手改生成物。

## 2. 节点与冗余设计

| 层次 | 节点 | 说明 |
| --- | --- | --- |
| 核心 | `core1` `core2` | FRR，OSPF Area 0，核心间双链路；Trust 侧与数据中心 VLAN 提供 VRRP VIP |
| 教学区汇聚 | `agg-t1` `agg-t2` | 上联双核心，下联 `acc-ta` / `acc-tb`，VRRP 网关 |
| 宿舍区汇聚 | `agg-d1` `agg-d2` | 上联双核心，下联 `acc-d1`，VRRP 网关 |
| 实验区汇聚 | `agg-l1` `agg-l2` | 上联双核心，下联 `acc-la`，VRRP 网关 |
| 图书馆汇聚 | `agg-lib1` `agg-lib2` | 上联双核心，下联 `acc-lib`，VRRP 网关 |
| 生活区汇聚 | `agg-life1` `agg-life2` | 上联双核心，下联 `acc-life`，VRRP 网关 |
| 接入/二层 | `acc-ta` `acc-tb` `acc-d1` `acc-la` `acc-lib` `acc-life` `dc-sw` | Linux VLAN-filtering bridge，Trunk + Access 端口 |
| 边界防火墙 | `fw1` `fw2` | nftables 三区域策略、NAT、VRRP 双机热备 |
| 出口路由 | `r1` `r2` | 连接 Untrust 与模拟 Internet，静态路由 + VRRP |
| 传输二层 | `trust-sw` `untrust-sw` `dmz-sw` `inet-sw` | Trust / Untrust / DMZ / Internet 汇聚二层转发 |
| 终端 | `pc-*` `ap-*` `srv-*` `internet` | 13 台 Alpine 终端/服务器 |

路由：核心、汇聚之间运行 OSPF（Area 0），核心向 OSPF 注入默认路由；`r1/r2` 使用静态路由。

安全：`fw1/fw2` 上 Trust 可访问 Untrust/DMZ，Untrust 仅可访问 DMZ 的 TCP 80/443，Untrust→Trust、DMZ→Trust 默认丢弃；Trust→Untrust 出方向做源 NAT（masquerade）。

## 3. VLAN 与地址规划

### 3.1 业务 VLAN

| VLAN | 用途 | 网段 | 网关 VIP | 代表终端 |
| --- | --- | --- | --- | --- |
| 101 | 教学区有线 | 10.10.0.0/24 | 10.10.0.1 | `pc-ta1` 10.10.0.11 / `pc-ta2` 10.10.0.12 |
| 102 | 教学区有线 | 10.10.1.0/24 | 10.10.1.1 | `pc-tb1` 10.10.1.11 |
| 500 | 教学区无线 | 10.50.0.0/24 | 10.50.0.1 | `ap-ta` 10.50.0.11 |
| 201 | 实验区 | 10.20.0.0/24 | 10.20.0.1 | `pc-la1` 10.20.0.11 |
| 301 | 宿舍区有线 | 10.32.0.0/24 | 10.32.0.1 | `pc-d1` 10.32.0.11 |
| 510 | 宿舍区无线 | 10.51.0.0/24 | 10.51.0.1 | `ap-d1` 10.51.0.11 |
| 50 | 图书馆 | 10.55.0.0/24 | 10.55.0.1 | `pc-lib` 10.55.0.11 |
| 61 | 生活区 | 10.64.0.0/24 | 10.64.0.1 | `pc-life` 10.64.0.11 |
| 70 | 数据中心 | 10.60.0.0/24 | 10.60.0.1 | `srv-dc1` 10.60.0.10 / `srv-dc2` 10.60.0.11 |
| 80 | DMZ | 10.80.0.0/24 | 10.80.0.1 | `srv-dmz` 10.80.0.10 |

每个业务 VLAN 由对应汇聚对提供 VRRP 虚拟网关；数据中心 VLAN 70 由 `core1/core2` 直接提供网关。

### 3.2 互联与出口地址

| 链路 | 网段 | 主要地址 |
| --- | --- | --- |
| 核心互联 | 10.0.0.0/30、10.0.0.4/30 | core1 10.0.0.1/10.0.0.5，core2 10.0.0.2/10.0.0.6 |
| 教学区上联 | 10.0.10.0/30 ~ 10.0.10.12/30 | 核心与 agg-t1/t2 各两条 /30 |
| 宿舍区上联 | 10.0.20.0/30 ~ 10.0.20.12/30 | 核心与 agg-d1/d2 各两条 /30 |
| 实验区上联 | 10.0.30.0/30 ~ 10.0.30.12/30 | 核心与 agg-l1/l2 各两条 /30 |
| 图书馆上联 | 10.0.40.0/30 ~ 10.0.40.12/30 | 核心与 agg-lib1/lib2 各两条 /30 |
| 生活区上联 | 10.0.50.0/30 ~ 10.0.50.12/30 | 核心与 agg-life1/life2 各两条 /30 |
| Trust | 10.0.100.0/24 | 核心 VIP .253，防火墙 VIP .254，fw1 .11，fw2 .12 |
| Untrust | 10.90.1.0/24 | 出口路由 VIP .254，防火墙 VIP .253，r1 .1，r2 .2 |
| Internet | 203.0.113.0/24 | `internet` .100，r1/r2 VRRP .254 |
| 管理网 | 172.31.100.0/24 | 由 Containerlab 自动分配 |

VRRP 采用 keepalived 实现，主节点优先级 120、备节点 100，主节点故障后备节点自动接管 VIP；主节点恢复后重新抢占。

## 4. 构建与部署

### 4.1 前置条件

- Docker Desktop（macOS）已运行，建议分配至少 **4 GB 内存、4 CPU**（40 个节点实测运行时合计约 300 MiB，启动阶段峰值更高）；
- 项目目录位于 Docker Desktop 的共享路径下（默认的 `/Users/...` 即可）；
- 首次构建时需要能访问 `ghcr.io`（containerlab 与 clab-io-draw 镜像）、Docker Hub（`alpine:3.24`）和 `mirrors.aliyun.com`（构建 FRR 镜像时的 apk 源）；若本机已有 `alpine:3.24`，构建脚本会跳过 Docker Hub 拉取；
- 本机有 `python3`（仅使用标准库，无需 pip 安装依赖）；
- 可运行官方 `ghcr.io/srl-labs/clab` 容器（或本机原生安装 containerlab）。

### 4.2 从零复原检查清单

假设 Docker 中没有任何本地镜像和容器，按以下顺序执行即可完整复原：

1. **构建三个本地镜像**（必须，否则 `campus-*:latest` 不存在）：

   ```bash
   sh build-images.sh
   ```

   该脚本会检查本地是否已有 `alpine:3.24`：有则直接使用，无则先执行 `docker pull alpine:3.24`，再依次构建三个镜像。这样既能避免 BuildKit 拉取基础镜像超时，也能在 Docker Hub 暂时不可达时使用本地缓存。也可手动执行：

   ```bash
   docker pull alpine:3.24
   docker build -t campus-frr:latest images/frr
   docker build -t campus-l2:latest  images/l2
   docker build -t campus-fw:latest  images/fw
   ```

2. **确认镜像存在**：

   ```bash
   docker image ls | grep -E 'campus-(frr|l2|fw)|alpine.*3\.24'
   ```

   若出现以下错误：

   ```text
   failed to resolve reference "docker.io/library/alpine:3.24":
   Head "https://registry-1.docker.io/v2/library/alpine/manifests/3.24":
   net/http: TLS handshake timeout
   ```

   说明 Docker Desktop 当前无法完成到 Docker Hub 的 TLS 握手，属于网络/代理/镜像源问题，不是 Dockerfile 或工程文件错误。可先确认本地是否已有该镜像：

   ```bash
   docker image inspect alpine:3.24 >/dev/null 2>&1 && echo local-ok
   docker images | grep alpine
   ```

   有本地镜像时直接重跑 `sh build-images.sh` 即可（脚本会跳过 pull）；没有本地镜像时请检查代理/VPN/DNS，或配置 Docker Desktop 的 registry mirror 后重试。apk 包来自 `mirrors.aliyun.com`，与 Docker Hub 无关。

3. **生成拓扑与配置**（即使仓库中已有生成物，也建议执行一次）：

   ```bash
   python3 gen.py
   ```

4. **部署**：

   ```bash
   sh run-clab.sh deploy -t campus-lab.clab.yml
   ```

   首次运行会自动拉取 `ghcr.io/srl-labs/clab:latest` 和 `alpine:3.24`。

5. **等待收敛后运行测试**（见第 5 节）。

镜像基于 `alpine:3.24`，使用阿里云 Alpine 镜像源安装 `frr`、`iproute2`、`nftables`、`keepalived` 等软件，适用于 arm64 与 amd64。若构建时软件源不可用，可修改各 `Dockerfile` 中的 `apk` 源地址；若需要更换 Alpine 版本，需同时修改三个 `Dockerfile` 的 `FROM alpine:3.24`、各 `Dockerfile` 中的 `v3.24` 源路径以及 `gen.py` 中终端镜像的 `alpine:3.24`。

### 4.3 生成并部署

```bash
cd net_prac/campus-lab
python3 gen.py                         # 重新生成 configs/ 与 campus-lab.clab.yml
sh run-clab.sh deploy -t campus-lab.clab.yml
```

若本机已可直接使用 containerlab，也可执行：

```bash
clab deploy -t campus-lab.clab.yml
```

部署需要约 20~40 秒完成 OSPF 收敛与 VRRP 选举。可用以下命令确认：

```bash
docker ps --filter name=clab-campus-lab- --format '{{.Names}}' | wc -l   # 应为 40
docker exec clab-campus-lab-core1 vtysh -c 'show ip ospf neighbor'        # 应为 12 条 Full
```

### 4.4 导出拓扑图（draw.io）

生成可用 draw.io 打开的拓扑文件：

```bash
sh gen-drawio.sh
```

脚本会依次执行：

1. 用 Containerlab 自带的 clab-io-draw 按 `graph-level` 生成**纵向分层**布局；
2. 用 `drawio-postprocess.py` 做可读性优化：
   - 行距由 175 px 增加到 240 px，避免层级纵向挤在一起；
   - 删除 122 个链路接口名标签，减少线条区域的文字密度；
   - 链路改为浅灰色细线，带弧线跳线，降低视觉权重。

最终输出 `campus-lab.clab.drawio`，可直接用 draw.io / diagrams.net 打开或导出为 PNG/SVG，用于报告和答辩材料。首次执行会拉取 `ghcr.io/srl-labs/clab-io-draw` 工具镜像。

若本机已可直接使用 containerlab，也可手动执行：

```bash
clab graph --drawio --drawio-args "--layout vertical" -o -t campus-lab.clab.yml
python3 drawio-postprocess.py campus-lab.clab.drawio
```

> 拓扑中各节点已在 `campus-lab.clab.yml` 中通过 `graph-level` 指定层级（由 `gen.py` 生成）。如需在图上保留每条链路的 `ethX` 接口名，直接执行上面的 `clab graph` 命令、跳过 `drawio-postprocess.py` 即可。

### 4.5 销毁与文件清理

销毁容器和网络：

```bash
sh run-clab.sh destroy -t campus-lab.clab.yml --cleanup
```

在 macOS 上销毁时可能打印与 `/etc/hosts` 权限有关的错误，这是 Containerlab 写宿主机 hosts 文件失败所致，不影响容器清理；可用 `docker ps -a | grep clab-campus-lab` 确认已删除。

注意：`destroy` 只清理容器、veth 和 Containerlab 网络，**不会删除工程目录中生成的拓扑文件、配置文件和拓扑图**。如需彻底清理工作区，在 `campus-lab/` 目录下手动执行：

```bash
# 删除 draw.io 拓扑图
rm -f campus-lab.clab.drawio

# 删除 Containerlab 可能残留的运行时状态目录（macOS 上 destroy 后常见）
rm -rf clab-campus-lab/

# 删除 macOS 元数据文件
find . -name .DS_Store -delete

# 可选：删除由 gen.py 生成的拓扑与节点配置
# 删除后不影响源文件，需要时执行 python3 gen.py 重新生成
rm -rf configs campus-lab.clab.yml
```

以上生成物均已写入仓库根目录的 `.gitignore`，删除后不会影响 Git 状态。如需一并删除本地镜像：

```bash
docker image rm campus-frr:latest campus-l2:latest campus-fw:latest
```

## 5. 验证测试

部署完成后，依次执行：

```bash
sh tests/connectivity.sh   # 同 VLAN、跨 VLAN、跨区域、无线、NAT、DMZ
sh tests/routing.sh        # OSPF 邻居、OSPF 路由、VRRP VIP、默认路由
sh tests/security.sh       # Internet→DMZ 放行、Internet→内网阻断、策略计数器
sh tests/failover.sh       # VRRP 主备切换、OSPF 上联故障与恢复
```

预期结果：

- 连通性测试全部 PASS，内网终端可访问 Internet 与 DMZ；
- `core1`/`core2` 各有 12 条 OSPF Full 邻居，各业务网段均显示 `Known via "ospf"`；
- `fw1` 的 nftables 计数器显示 MASQUERADE、Internet→DMZ 放行、Internet→Trust 丢弃均有命中；
- 关闭 `core1` 的 keepalived 后，`core2` 接管 10.0.100.253，业务不中断；恢复后 `core1` 重新抢占；
- `agg-t1` 上联 `eth1` 断开期间，流量经另一条上联转发，丢包 0%，恢复后 OSPF 邻居回到 Full。

单独查看策略命中：

```bash
docker exec clab-campus-lab-fw1 nft list table inet fw
```

## 6. 注意事项

1. **不要在部署后直接 `docker restart` 某个节点**。Containerlab 的 veth 链路位于容器网络命名空间中，单纯重启 Docker 容器会丢失数据接口。故障实验后若要恢复，执行一次完整 `destroy` + `deploy`，或在节点故障期间依赖冗余路径。
2. **重新运行 `gen.py` 后应重新部署**。Docker Desktop 对单文件 bind mount 使用固定 inode，宿主机重写配置文件后，运行中的容器可能仍看到旧文件甚至报 `No such file or directory`；重新 deploy 可消除该问题。
3. **管理网默认路由**：节点启动时保留了 Containerlab 管理网卡 `eth0`，但 `prestart.sh` 会删除管理网默认路由，确保数据面默认路由生效。
4. **资源占用**：40 个 Alpine/FRR 容器可同时运行，但启动与 OSPF 收敛需要时间；请等待测试脚本通过后再截图取证。
5. **无线部分为逻辑验证**：VLAN 500/510 模拟无线业务网段，未模拟射频、信道、关联与漫游。
6. **测试脚本依赖容器名前缀** `clab-campus-lab-`；如修改拓扑 `name`，需同步调整脚本中的 `P` 变量。
