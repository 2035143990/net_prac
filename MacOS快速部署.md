# Containerlab on macOS (Docker-based)

本文档记录在 macOS 上通过 Docker 运行 Containerlab 的本地部署流程。适用于希望在不安装 Linux 虚拟机的情况下，快速搭建容器化网络实验环境的开发者。

## 前置条件

- macOS（Intel 或 Apple Silicon）
- Docker Desktop 已安装并正常运行
- 终端（默认 zsh）
- 可访问 `ghcr.io` 的网络环境

> **说明**：Containerlab 依赖 Linux 内核特性（网络命名空间、veth pair 等），macOS 本身不提供这些能力。因此本方案通过 Docker Desktop 内置的 Linux 虚拟机提供运行环境，Containerlab 本身以容器形式运行在该虚拟机内。

## 1. 安装并启动 Docker Desktop

从 Docker 官网下载 macOS 版本并完成安装。启动后确认菜单栏出现 Docker 图标，终端执行以下命令验证：

```bash
docker ps
```

若输出表头（即使无运行中的容器），说明 Docker 已就绪。

## 2. 配置 clab 快捷命令

Containerlab 官方未提供 macOS 原生安装包。推荐做法是在 shell 配置中定义一个函数，将 `clab` 命令封装为对官方 Containerlab 镜像的调用。

将以下内容追加到 `~/.zshrc`：

```bash
clab() {
  docker run --rm -it --privileged \
    --network host \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /var/run/netns:/var/run/netns \
    -v /etc/hosts:/etc/hosts \
    -v /var/lib/docker/containers:/var/lib/docker/containers \
    --pid="host" \
    -v "$(pwd)":"$(pwd)" \
    -w "$(pwd)" \
    ghcr.io/srl-labs/clab containerlab "$@"
}
```

执行 `source ~/.zshrc` 使配置生效。

关键参数说明：

- `--pid="host"`：使 Containerlab 容器能访问 Docker 虚拟机内部的进程命名空间，从而正确创建 veth pair。缺少该参数时，设备容器可启动但链路不通。
- `-v "$(pwd)":"$(pwd)"` 与 `-w "$(pwd)"`：将当前工作目录挂载进容器，确保拓扑文件可被访问。路径使用双引号包裹，以兼容包含空格的目录名。

## 3. 验证安装

```bash
clab version
```

首次执行会自动拉取 `ghcr.io/srl-labs/clab:latest` 镜像。输出中显示版本号即表示环境配置成功。

## 4. 工作目录约定

建议为每个实验建立独立目录，避免拓扑文件与实验残留物混杂：

```bash
mkdir -p ~/containerlab-labs/my-first-lab
cd ~/containerlab-labs/my-first-lab
```

`clab` 函数会将当前目录挂载进容器，因此拓扑文件应位于执行命令时所在的目录中。

## 5. 部署示例实验

创建 `test-lab.clab.yml`：

```yaml
name: test-lab
topology:
  nodes:
    node1:
      kind: linux
      image: alpine:latest
      cmd: sleep infinity
    node2:
      kind: linux
      image: alpine:latest
      cmd: sleep infinity
  links:
    - endpoints: ["node1:eth1", "node2:eth1"]
```

部署：

```bash
clab deploy -t test-lab.clab.yml
```

检查状态：

```bash
clab inspect -t test-lab.clab.yml
```

两个节点状态均为 `running` 即表示部署成功。

> **注意**：部署过程中可能出现 `failed to create hosts file: open /etc/hosts: permission denied` 报错。该错误仅表示 Containerlab 无法将节点信息写入宿主机 `/etc/hosts`，不影响实验网络本身。可通过 `docker exec` 直接进入节点操作。

## 6. 拓扑可视化

Web 交互图（`clab graph`）在 macOS 上受 Docker Desktop 网络隔离限制，其监听地址位于 Docker 虚拟机内部，宿主机浏览器无法直接访问。推荐使用静态导出：

```bash
clab graph --drawio -t test-lab.clab.yml
```

该命令会拉取 `ghcr.io/srl-labs/clab-io-draw` 镜像并生成 `.drawio` 文件，可用 draw.io 打开查看。

## 7. 清理

销毁实验并清除残留目录：

```bash
clab destroy -t test-lab.clab.yml --cleanup
```

`--cleanup` 参数用于删除实验生成的 `clab-<name>` 目录。若省略，容器会被删除但残留目录仍会保留。

删除拓扑文件：

```bash
rm test-lab.clab.yml
```

清理未使用的 Docker 资源：

```bash
docker system prune
```

## 注意事项

- **Apple Silicon 兼容性**：优先选用原生支持 ARM64 的网络设备镜像（如 Nokia SR Linux、Arista cEOS、FRR）。仅支持 x86_64 的镜像需经 Rosetta 2 模拟运行，性能明显下降。
- **目录名避免空格**：虽然 `clab` 函数已对路径加引号，仍建议工作目录路径不含空格，以减少潜在的解析问题。
- **镜像存储**：Containerlab 工具镜像与实验设备镜像均存放于 Docker 本地镜像库。删除 `ghcr.io/srl-labs/clab` 不会影响实验镜像；`docker system prune -a` 会清理未被使用的镜像。
