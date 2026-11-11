# 报告配图说明

## 1. 图目录与插入位置

| 图号 | 文件 | 插入章节 | 内容 | 来源 |
| --- | --- | --- | --- | --- |
| 图 4-1 | `fig-4-1-campus-topology.svg` | 4.1 网络拓扑结构 | 校园网总体拓扑（核心/汇聚/接入/出口/DMZ） | 手绘示意 |
| 图 4-2 | `fig-4-2-simulation-topology.svg` | 4.1 网络拓扑结构 | Containerlab 49 节点/72 链路分层与规模 | 手绘示意 |
| 图 7-1 | `fig-7-1-teaching-vlan.svg` | 7.1.3 网络配置拓扑结构 | 教学区 VLAN/Trunk/VRRP | 手绘示意 |
| 图 7-2 | `fig-7-2-dhcp-relay.svg` | 7.2.3 网络配置拓扑结构 | DHCP Relay 报文流程与地址池 | 手绘示意 |
| 图 7-3 | `fig-7-3-firewall-nat.svg` | 7.3.3 防火墙配置 | Trust/Untrust/DMZ、SNAT、DNAT | 手绘示意 |
| 图 7-4 | `fig-7-4-ospf-lag.svg` | 7.4.2 网络配置拓扑结构 | OSPF 邻居、核心/服务器链路聚合 | 手绘示意 |
| 图 7-5 | `fig-7-5-dorm-isolation.svg` | 7.5.1 宿舍区访问控制原理 | 宿舍 ACL 规则与管理网保护 | 手绘示意 |

> 每个 SVG 旁已生成同名 `.png`（2400 px 宽），报告正文引用的是 PNG，可直接插入 Word；SVG 保留为可编辑源文件。

PNG 由仓库内脚本 `tools/svg2png.py` 生成（无头浏览器渲染，中文、描边、圆角与浏览器一致）：

```sh
python3 tools/svg2png.py            # 转换 docs/figures 下全部 SVG，输出 2400 px 宽
python3 tools/svg2png.py --width 3000
python3 tools/svg2png.py --backend svglib   # 无浏览器时的纯 Python 备选
```

## 2. 正式拓扑图从哪来

`campus-lab/gen-drawio.sh` 会用 Containerlab 的 `graph --drawio` 生成完整拓扑：

```sh
cd net_prac/campus-lab
sh gen-drawio.sh
```

产出：

```text
campus-lab/campus-lab.clab.drawio
```

然后用 draw.io 打开并导出：

1. 打开 <https://app.diagrams.net/> 或 draw.io Desktop；
2. File → Open → 选择 `campus-lab.clab.drawio`；
3. File → Export as → PNG；
4. 建议设置：Zoom 100%、Width 1600–2000 px、Background 透明关闭、DPI 300；
5. 保存为 `docs/figures/fig-4-1-campus-topology.png`（覆盖或新增，不覆盖 SVG 源）。

如果 `sh gen-drawio.sh` 在容器方式下长时间无输出，可在本机安装 containerlab 后直接执行：

```sh
containerlab graph --drawio --drawio-args "--layout vertical" -o -t campus-lab.clab.yml
python3 drawio-postprocess.py campus-lab.clab.drawio
```

注意：`drawio-postprocess.py` 已对“接口标签删除数、链路样式替换数、节点坐标缩放数”加断言，上游格式变化时会非零退出，不会静默生成旧样式。

## 3. 示意图转 PNG（Word 用）

报告里的 7 张示意图是 SVG，Markdown/浏览器可直接显示。若老师要求 Word，用仓库内脚本转换（推荐，跨平台且中文渲染正确）：

```sh
python3 tools/svg2png.py
```

脚本优先调用无头 Chrome / Edge；找不到浏览器时自动回退到 svglib 纯 Python 链路。手工转换的备选方法：

- 方法一：浏览器打开 SVG → 右键“图片另存为”/截图（最简单）；
- 方法二：macOS Quick Look 缩略图：

  ```sh
  qlmanage -t -s 2000 -o docs/figures docs/figures/fig-4-1-campus-topology.svg
  ```

  会生成 `fig-4-1-campus-topology.svg.png`，重命名后使用；
- 方法三：安装 `rsvg-convert` 或 Inkscape 后批量转换：

  ```sh
  rsvg-convert -w 2000 docs/figures/fig-4-1-campus-topology.svg \
    -o docs/figures/fig-4-1-campus-topology.png
  ```

## 4. Word 排版要求

- 图片居中，宽度约 14–15 cm，不超出正文版心；
- 图题在图下方居中，五号宋体，格式为“图 4-1 校园网总体拓扑”；
- 正文首次引用写“如图 4-1 所示”，不要只放图不引用；
- 图中文字建议不小于 8 pt，导出 PNG 时保证 2000 px 左右宽度；
- 若使用 draw.io 导出的正式拓扑，建议保留一份 SVG，方便答辩前修改。

## 5. 建议的正文引用句

- 4.1：“校园网总体拓扑如图 4-1 所示，仿真拓扑与节点规模如图 4-2 所示。”
- 7.1.3：“教学区 VLAN、Trunk 与 VRRP 关系如图 7-1 所示。”
- 7.2.3：“DHCP Relay 的报文流程如图 7-2 所示。”
- 7.3.3：“防火墙三区与 SNAT/DNAT 路径如图 7-3 所示。”
- 7.4.2：“OSPF 邻居与链路聚合关系如图 7-4 所示。”
- 7.5.1：“宿舍区访问控制路径如图 7-5 所示。”