# 奉贤校区校园网 Containerlab 仿真

基于《奉贤校区校园网设计方案》构建的可运行校园网拓扑：双核心、分区域双汇聚、VLAN 接入、OSPF 动态路由、VRRP 网关冗余、DHCP 集中地址服务与区域 Relay、宿舍区访问控制、Trust/Untrust/DMZ 三区防火墙、源 NAT 与 DMZ 目的 NAT、核心与服务器链路聚合。

拓扑共 **44 个容器、66 条链路**，部署后可直接进行层二/层三转发、跨区域访问、地址自动配置、Internet 访问、DMZ 发布和故障切换实验。节点数、链路数、VLAN 与地址池以 `configs/facts.json` 为准，本文数字由 `gen.py` 生成口径同步。

> 📖 想理解项目怎么组织、拓扑怎么分层、看图怎么做，见 [`ARCHITECTURE.md`](ARCHITECTURE.md)。
>
> 🖥️ 想直接看拓扑图：`sh topoviewer.sh` 后用浏览器打开 <http://localhost:50080/>。

## 1. 目录结构

```text
campus-lab/
├─ campus-lab.clab.yml     # 由 gen.py 生成的 Containerlab 拓扑
├─ gen.py                  # 拓扑与全部节点配置的生成器（单一事实源）
├─ gen-drawio.sh           # 生成分层 draw.io 拓扑图并优化可读性
├─ drawio-postprocess.py   # draw.io 后处理，替换条数异常时非零退出
├─ build-images.sh         # 一键构建四个本地镜像并检查 dnsmasq 版本
├─ deploy-lab.sh           # 统一部署入口：销毁 → 部署 → 等待收敛 → 就绪预检
├─ topoviewer.sh           # 启动 TopoViewer 交互式拓扑查看器
├─ run-clab.sh             # macOS 下无 TTY 运行 containerlab 的包装脚本
├─ images/
│  ├─ frr/                 # Alpine + FRRouting + keepalived + nftables + dnsmasq
│  │                       # start.sh 为 ENTRYPOINT，启动时自动应用配置
│  ├─ l2/                  # Alpine + iproute2 二层/三层交换机镜像
│  │                       # start.sh 为 ENTRYPOINT，启动时自动应用配置
│  ├─ fw/                  # Alpine + nftables + keepalived + conntrack-tools
│  │                       # start.sh 为 ENTRYPOINT，启动时自动应用配置
│  └─ host/                # Alpine + iproute2 + dnsmasq 终端/服务器镜像
│                           # start.sh 为 ENTRYPOINT，启动时自动应用配置
├─ configs/
│  ├─ frr/                 # 14 台 FRR 节点的 frr.conf / prestart / keepalived
│  │                       # 汇聚节点另有 acl.nft、dhcp-relay.conf、start-services.sh
│  ├─ access/              # 7 台接入/汇聚二层交换机的 VLAN 脚本
│  ├─ fw/                  # fw1/fw2 启动脚本、nftables 规则、VRRP
│  ├─ hosts/               # 17 台终端/服务器的地址、DHCP 客户端、dnsmasq 配置
│  └─ facts.json           # 生成期事实快照，测试与报告读取
├─ tests/
│  ├─ lib.sh               # 断言、编号、JSONL 结果库
│  ├─ cases.tsv            # 65 条用例清单
│  ├─ preflight.sh         # 拓扑就绪预检（二层/OSPF/VRRP），接入 run-all.sh
│  ├─ run-all.sh           # 统一 runner，退出码 0/1/2
│  ├─ connectivity.sh      # CONN-01~10
│  ├─ routing.sh           # ROUTE-01~08
│  ├─ security.sh          # SEC-01~06
│  ├─ dhcp.sh              # DHCP-01~08
│  ├─ iso.sh               # ISO-01~13
│  ├─ nat.sh               # NAT-01~07
│  ├─ lag.sh               # LAG-01~07
│  └─ failover.sh          # FAIL-01~06
├─ ../docs/course-report-draft.md
├─ ../tools/report_check.py
├─ ARCHITECTURE.md         # 架构说明：代码组织 + 拓扑分层 + TopoViewer 用法
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

安全：`fw1/fw2` 上 Trust 可访问 Untrust/DMZ；Untrust 仅可通过发布地址 `198.51.100.80` 的 DNAT 访问 DMZ 的 TCP 80/443；Untrust→Trust、DMZ→Trust 默认丢弃；Trust→Untrust 出方向做源 NAT。宿舍区（10.32–10.49、10.96–10.106，含无线 10.51.0.0/24）在 `agg-d1/agg-d2` 上通过 nftables 阻断到管理网、教学区（含有线/无线）、实验区、图书馆、数据中心、生活区及校内/出口互联和环回网段的访问，仅放行宿舍互访、DNS、Internet 与 DMZ 发布服务；`core1/core2` 另外阻断所有用户区域到管理网、校内/出口互联和环回网段的访问，并阻断教学/实验区到宿舍区、生活区到教学/实验/宿舍/图书馆/数据中心/管理网，以及数据中心主动访问 Untrust/Internet 的流量；管理网 10.70.0.0/24 不允许主动访问 Untrust，且仅运维可达。ACL 首条规则为 `ct state established,related accept`；由于双汇聚/双核心节点之间未部署 conntrack 状态同步，ACL 还显式放行受限区域发出的 ICMP echo-reply 以及 TCP 非纯 SYN 报文（含 ACK、SYN-ACK），避免非对称路径误伤回程流量。

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
   sh deploy-lab.sh deploy
   ```

   脚本会先用 `clab destroy` 清理旧环境，再部署拓扑，等待 120 秒让 OSPF / VRRP 收敛，最后执行一次拓扑就绪预检。本机装有原生 `clab` 时直接调用，否则退回用官方容器运行（macOS 场景）。

   > 清理请务必用 `clab destroy`，不要用 `docker rm` 手工删除容器：Containerlab 依赖自己的状态文件追踪容器与 veth，手工删除会让状态失步。

4. **等待收敛后运行测试**（见第 5 节）。

镜像基于 `alpine:3.24`，使用阿里云 Alpine 镜像源安装 `frr`、`iproute2`、`nftables`、`keepalived`、`dnsmasq`、`conntrack-tools` 等软件，适用于 arm64 与 amd64。若构建时软件源不可用，可修改各 `Dockerfile` 中的 `apk` 源地址。

### 4.3 Windows + WSL2 部署

> **为什么不能直接用 Docker Desktop**：Containerlab 需要在宿主机上创建 veth 虚拟网线，并把一端塞进各容器的网络命名空间（netns）。Docker Desktop 的容器运行在一个**独立的 Linux 虚拟机**里，与 WSL2 是两个不同的内核，因此宿主机看不到容器的 netns，链路必然创建失败（报错 `network namespace is not available`）。
>
> 解决办法是让容器与 clab 跑在**同一个 Linux 内核**内，即使用 WSL2 自带的 Docker Engine，而不是 Docker Desktop 的 Linux VM。

**准备（PowerShell，管理员）**：

```powershell
wsl --install -d Ubuntu-24.04      # 若已安装可跳过
```

**在 WSL 内安装 Docker Engine**：

```sh
sudo apt update && sudo apt install -y docker.io containerd
sudo systemctl enable --now docker
sudo usermod -aG docker $USER      # 重新登录后生效
```

**配置镜像源**（WSL 无法直连 Docker Hub）：

```sh
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json >/dev/null <<'JSON'
{
  "registry-mirrors": ["https://docker.m.daocloud.io"]
}
JSON
sudo systemctl restart docker
```

**安装 containerlab**（GitHub Releases 直连不通时，从官方镜像提取二进制）：

```sh
docker create --name clab-extract ghcr.io/srl-labs/clab:latest
docker cp clab-extract:/usr/bin/containerlab ~/bin/clab
docker rm clab-extract
chmod +x ~/bin/clab
~/bin/clab version
```

**构建与部署**：

```sh
cd /mnt/d/code/net_prac/campus-lab
bash build-images.sh
python3 gen.py
sh deploy-lab.sh deploy
```

`deploy-lab.sh` 会依次完成：销毁旧环境（用 `clab destroy`，不要手工 `docker rm`）→ 部署拓扑 → 记录 dockerd 的 MainPID → 等待 120 秒收敛 → 执行拓扑就绪预检。

**运行测试**：

```sh
bash tests/run-all.sh
```

**注意事项**：

> **⚠️ 最重要的一条：整个流程必须在同一个持续打开的 WSL 终端窗口内完成。**
>
> WSL2 发行版在没有活跃前台进程时会被 Windows 回收。一旦实例被回收，systemd 会执行完整的关机序列（`Stopping docker.service`），dockerd 随之退出；下次启动 WSL 时 dockerd 虽然会恢复容器进程，但 **Containerlab 注入的 veth 链路不会重新注入**，二层广播域与 VRRP 全部失效，表现为「容器数量正常但大量用例失败」。
>
> 正确做法：在 PowerShell 里执行 `wsl -d Ubuntu-24.04 -u root` 进入 WSL，**保持该窗口不关闭**，然后在同一个会话里依次执行构建、生成、部署、测试的全部命令。
>
> `deploy-lab.sh` 会把部署时 dockerd 的 MainPID 记录到 `.deploy-dockerd-pid`，`tests/preflight.sh` 会比对它，一旦发现 dockerd 在部署后被重启过，会直接指出「WSL 实例被回收或 docker 服务重启」，而不是笼统报环境异常。
>
> 手工验证：部署前后对比 `systemctl show docker -p MainPID --value`，PID 相同说明期间 dockerd 未被重启。

1. 跑实验期间请**退出 Docker Desktop**，避免它与 WSL 内的 dockerd 争抢 `/var/run/docker.sock`；
2. WSL2 的代理不会自动镜像到 WSL，用镜像源而不是代理来拉取镜像；
3. 仓库内 shell 脚本统一为 LF 行尾（见根目录 `.gitattributes`）。若检出后出现 `set: Illegal option -` 之类的错误，执行 `python3 tools/fix-eol.py` 转换；
4. `keepalived` 拒绝加载带可执行位的配置文件，容器启动脚本会先把配置复制到容器本地并 `chmod 0644`；
5. **宿主机或 WSL 重启后需要重新 `deploy`**。节点配置（bridge、VLAN、地址、ACL、VRRP）由镜像 ENTRYPOINT 自动重跑，但 Containerlab 注入的 veth 链路不会自动重新注入，须重新部署并等待约 90 秒收敛。`tests/run-all.sh` 的预检会检测这类失效状态并直接提示重新部署。
6. **不要用 `docker rm` 手工删除实验室容器**。Containerlab 依赖自己的状态文件（`clab-campus-lab/.state.clab.yaml`）追踪容器与 veth，手工删除会让状态失步，后续 `deploy` 可能触发二次清理并重建容器。清理请一律使用 `clab destroy -t campus-lab.clab.yml --cleanup`。

### 4.4 部署后确认

```sh
docker ps --filter name=clab-campus-lab- --format '{{.Names}}' | wc -l   # 应为 44
docker exec clab-campus-lab-core1 vtysh -c 'show ip ospf neighbor'        # 应为 11 条 Full
docker exec clab-campus-lab-core1 cat /proc/net/bonding/bond0             # 两个成员均 up
docker exec clab-campus-lab-srv-dc1 pgrep -a dnsmasq                      # DHCP/DNS 进程
docker exec clab-campus-lab-agg-d1 pgrep -a dnsmasq                       # Relay 进程
```

### 4.5 用 TopoViewer 查看拓扑（推荐）

Containerlab 内置了交互式拓扑查看器。**部署完成后**在同一个 WSL 终端里执行：

```sh
sh topoviewer.sh
```

然后在 Windows 浏览器打开 <http://localhost:50080/>。

界面支持拖拽平移、滚轮缩放、"Fit stage" 适配全图、全屏、横向/纵向布局切换，点击节点可看接口与 IP。其它导出格式：

```sh
~/bin/clab graph --drawio  -t campus-lab.clab.yml   # draw.io 图形
~/bin/clab graph --mermaid -t campus-lab.clab.yml   # mermaid 流程图
```

`topoviewer.sh` 会顺带启动一个 keeper 进程保活，避免 WSL 实例被回收导致 veth 丢失、拓扑图断链。默认端口 50080，可改：`sh topoviewer.sh 0.0.0.0:8080`。

详见 [`ARCHITECTURE.md`](ARCHITECTURE.md) 第 5 节。

### 4.6 导出拓扑图（draw.io）

```sh
sh gen-drawio.sh
```

`drawio-postprocess.py` 现在对接口标签删除数、链路样式替换数、节点坐标缩放数分别校验；任一类为 0 时非零退出，避免上游格式变化后静默失效。

### 4.7 销毁与文件清理

```sh
sh deploy-lab.sh destroy
```

或直接调用 containerlab：

```sh
~/bin/clab destroy -t campus-lab.clab.yml --cleanup
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
| ISO | ISO-01~13 | 宿舍→管理/教学/实验/数据中心阻断，宿舍互访与 Internet/DMZ 放行，管理源放行，教学→宿舍阻断，计数器 |
| NAT | NAT-01~07 | 公网地址 80/443、未发布端口、私网直达、DNAT/SNAT/丢弃计数 |
| LAG | LAG-01~07 | bond 模式、成员状态、单逻辑地址、OSPF 单邻居、服务器聚合、成员故障 |
| FAIL | FAIL-01~06 | core VRRP 切换、上联故障恢复、fw1 切换、邻居恢复 |

结果写入 `tests/results/<run-id>/`：

- `results.jsonl`：一行一个用例，含 `id`、`status`、`expected`、`actual`、`cmd`、`ms`；
- `summary.txt`：总计与各套件通过/失败/跳过；
- `raw/<id>.log`：命令原始输出。

退出码：`0` 全部通过或跳过；`1` 存在失败；`2` 环境不可用（Docker 未启动、容器数不足、facts 缺失、**拓扑未就绪**）。

### 5.1.1 拓扑就绪预检

`run-all.sh` 在执行任何用例前会先运行 `tests/preflight.sh`，校验实验环境是否真正处于"已就绪"状态：

- 12 台二层设备的 `br0` 存在，且已接入至少一个端口（二层广播域成立）；
- `core1` 的 OSPF Full 邻居为 11；
- 四组 VRRP VIP（核心 `10.0.100.253`、教学区汇聚 `10.10.0.1`、宿舍区汇聚 `10.32.0.1`、防火墙 `10.0.100.254`）各自**恰好有 1 个**持有者。

任一项不满足，runner 会以退出码 `2` 终止并输出 `result=ENV_UNAVAILABLE`，同时给出重新部署命令，不再产出无意义的用例级失败。

> 这一检查是必要的：Containerlab 的 `exec` 只在 `deploy` 时执行一次，容器被 restart 后配置不会重跑，而容器数量检查无法发现这类"看起来正常、实际已失效"的状态。

### 5.2 能力开关与 SKIP

`configs/facts.json` 的 `capabilities` 为 `dhcp/acl/dnat/lag/report`。能力为 `false` 时对应套件 SKIP；能力为 `true` 但断言失败必须 FAIL，不得跳过。

### 5.3 实测状态（2026-11-11）

全量运行 run-id `20261111T122017Z` 结果为 **65/65 通过、0 失败、0 跳过**（Windows / WSL2 / Docker Engine 29.1.3 / Containerlab 0.83.0）：

| 套件 | 通过/总数 | 失败项 |
| --- | --- | --- |
| CONN | 10/10 | — |
| ROUTE | 8/8 | — |
| SEC | 6/6 | — |
| DHCP | 8/8 | — |
| ISO | 13/13 | — |
| NAT | 7/7 | — |
| LAG | 7/7 | — |
| FAIL | 6/6 | — |
| **合计** | **65/65** | |

历史轮次：首轮 `20261108T115247Z` 为 61/64（3 项失败均已定位修复）；迁移到 WSL 后 `20261109T135137Z` 为 29/64、`20261109T141507Z` 为 62/64，`20261109T150150Z` ~ `20261109T155017Z` 均为 65/65；`20261110T031032Z` 为 37/65（宿主机重启后 `exec` 未重跑导致二层广播域失效与 VRRP 双主，已通过镜像 ENTRYPOINT 自愈机制修复，并新增拓扑预检拦截此类状态）；`20261111T062929Z` 为 64/64（按设计方案补全教学区、实验区、宿舍区地址范围，并新增生活区出向隔离与数据中心禁止主动出校 ACL）。

本轮修复了三类问题：一是部署后 OSPF 尚未收敛就执行测试导致的 CONN/ROUTE/DHCP 假失败，现由 `tests/run-all.sh` 在套件执行前等待 `core1/core2` 的 OSPF Full 邻居达到 11，再执行拓扑预检；二是「教学区 -> 宿舍区」阻断规则原先只挂在 `dorm_filter` 链（仅 `saddr ∈ @dorm_nets` 时才跳转），教学区出向流量根本进不去，现已在 forward 基础链增加 `ip saddr @teaching_nets ip daddr @dorm_nets counter drop`；三是 WSL2 实例被 Windows 回收导致 dockerd 重启、veth 链路丢失，预检现会比对部署时记录的 dockerd MainPID 并给出准确提示。

详细证据见 `../docs/verification-report.md`。

## 6. 注意事项

1. **不要在部署后直接 `docker restart` 某个节点**。节点配置（bridge、VLAN、地址、ACL、VRRP）已由镜像 ENTRYPOINT 在容器每次启动时自动恢复，但 Containerlab 注入的 veth 链路位于容器网络命名空间中，容器重启后不会自动重新注入，数据面依然不通。故障实验后若要恢复，执行一次完整 `destroy` + `deploy`。
2. **宿主机重启后必须重新部署**。Windows 重启会让 Docker 恢复容器（节点配置会自动重跑），但 veth 链路同样可能失效。请执行 `clab destroy -t campus-lab.clab.yml --cleanup && clab deploy -t campus-lab.clab.yml`，等待约 90 秒收敛后再跑测试；`run-all.sh` 的预检会在环境未就绪时直接给出该提示。
3. **重新运行 `gen.py` 后应重新部署**。Docker Desktop 对单文件 bind mount 使用固定 inode，宿主机重写配置文件后，运行中的容器可能仍看到旧文件甚至报 `No such file or directory`。
4. **管理网默认路由**：节点启动时保留了 Containerlab 管理网卡 `eth0`，但 `prestart.sh` 会删除管理网默认路由，确保数据面默认路由生效。
5. **链路聚合依赖内核 bonding**：核心使用 802.3ad，服务器使用 active-backup。若容器内核或 veth 不支持 LACP，`prestart.sh` 会回退 active-backup，测试 LAG-01 将 FAIL；报告中应如实记录该限制。
6. **DHCP Relay 依赖 dnsmasq >= 2.86**：构建脚本已检查版本。双汇聚同时运行 relay，服务器按 MAC 复用租约；需在实测中确认无重复分配。
7. **DMZ 443 不做 TLS**：`srv-dmz` 用 busybox `nc` 返回明文 banner，仅验证端口映射与策略。
8. **无线部分为逻辑验证**：VLAN 500/510 模拟无线业务网段，未模拟射频、信道、关联与漫游。
9. **测试脚本依赖容器名前缀** `clab-campus-lab-`；如修改拓扑 `name`，需同步调整 `tests/lib.sh` 的 `P` 变量。
10. **报告与事实一致性**：修改 `gen.py` 后重新生成 `facts.json`，并执行：

   ```sh
   cd net_prac
   python3 tools/report_check.py
   ```
11. **幂等校验排除 facts.json**：`facts.json` 含 `generated_at`，两次生成的 SHA 比对应排除该文件。