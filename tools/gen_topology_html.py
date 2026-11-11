#!/usr/bin/env python3
"""生成交互式校园网拓扑演示页 docs/topology.html。

页面提供两个视图，可在线切换：

1. **完整设计布局**（默认）：按《奉贤校区校园网设计方案》2.1/5.1 的楼宇清单，
   画出全部 48 个子网对应的楼宇——教学楼 A–E、实验楼 A–H、学生公寓 1–28 号楼、
   图书馆、食堂 1–2、体育馆、信息大楼（计算机实验中心/数据中心）、
   无线与功能网段，并用中文标注楼层、信息点与 VLAN。
2. **仿真运行拓扑**：从 containerlab 导出的 topology-data.json 读取
   实际部署的 44 个容器与 66 条链路，按网络层级排布。

数据来源：
- 楼宇清单与网段：tools/c_address_plan.py（与设计方案 5.1/5.2 同源）
- 信息点数：设计方案 2.1 / 7.1
- 仿真节点：campus-lab/clab-campus-lab/topology-data.json

用法：
    python3 tools/gen_topology_html.py
"""
from __future__ import annotations

import html
import ipaddress
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import c_address_plan as cap  # noqa: E402

LAB = ROOT / "campus-lab"
TOPO_JSON = LAB / "clab-campus-lab" / "topology-data.json"
CLAB_YML = LAB / "campus-lab.clab.yml"
OUT = ROOT / "docs" / "topology.html"

# ---------------------------------------------------------------- 楼宇静态信息
# 方案 2.1/7.1：每栋楼的楼层与单栋信息点（不是全区域合计）
BUILDING_INFO = {
    "教学楼": dict(floors=4, points=80, per="10 间教室 × 2 点/层，单栋 80 点"),
    "实验楼": dict(floors=8, points=512, per="16 间实验室 × 4 点/层，单栋 512 点"),
    "学生公寓": dict(floors=6, points=240, per="24 间宿舍 × 2 点/层，单栋 240 点"),
    "图书馆": dict(floors=10, points=328, per="1–4F 阅览室 + 5F 电子阅览室 200 点"),
    "食堂": dict(floors=3, points=48, per="餐厅 6 点 + 办公室 5 间 × 2 点"),
    "体育馆": dict(floors=1, points=10, per="赛事直播 / 监控 / 计分"),
    "数据中心服务器": dict(floors=2, points=1200, per="2–3F 计算机实验中心 6 间 × 100 点"),
    "DMZ": dict(floors=0, points=0, per="对外发布服务（Web/邮件/对外 DNS）"),
    "网络管理": dict(floors=0, points=0, per="NMS / SSH / SNMP 管理网"),
    "无线-教学/图书馆/信息楼": dict(floors=0, points=0, per="SSID ECUST-EDU（VLAN 500）"),
    "无线-宿舍/实验区": dict(floors=0, points=0, per="SSID ECUST-STU（VLAN 510）"),
}

# 楼宇中文显示名（地址规划工具里的名字已是中文，这里只做分组）
REGION_ORDER = ["教学区", "实验区", "宿舍区", "图书馆", "生活区", "数据中心", "网络中心", "出口", "无线"]
REGION_COLOR = {
    "教学区": "#2563eb",
    "实验区": "#7c3aed",
    "宿舍区": "#0d9488",
    "图书馆": "#b45309",
    "生活区": "#be123c",
    "数据中心": "#0891b2",
    "网络中心": "#475569",
    "出口": "#9333ea",
    "无线": "#64748b",
}
REGION_LABEL = {
    "教学区": "教学区", "实验区": "实验区", "宿舍区": "宿舍区",
    "图书馆": "图书馆", "生活区": "生活区", "数据中心": "数据中心 / 计算机实验中心",
    "网络中心": "网络管理", "出口": "DMZ（出口发布区）", "无线": "无线子网",
}

# 楼宇所在汇聚点（设计方案 2.1）
AGGREGATION = {
    "教学区": "教学 A 楼汇聚",
    "实验区": "实验 A 楼汇聚",
    "宿舍区": "第 1 宿舍汇聚",
    "图书馆": "图书馆汇聚",
    "生活区": "生活区汇聚",
    "数据中心": "直连双核心",
    "网络中心": "核心 SW1/SW2",
}

# ---------------------------------------------------------------- 仿真分层
LAYERS = [
    ("internet", "外网", "#64748b", lambda n: n == "internet"),
    ("inet_sw", "外网汇聚", "#94a3b8", lambda n: n == "inet-sw"),
    ("edge", "出口路由", "#ea580c", lambda n: n in ("r1", "r2")),
    ("untrust_sw", "Untrust 二层", "#a78bfa", lambda n: n == "untrust-sw"),
    ("fw", "防火墙", "#9333ea", lambda n: n.startswith("fw")),
    ("zone_sw", "Trust / DMZ 二层", "#34d399", lambda n: n in ("trust-sw", "dmz-sw")),
    ("core", "核心", "#dc2626", lambda n: n.startswith("core")),
    ("agg", "汇聚", "#2563eb", lambda n: n.startswith("agg")),
    ("access", "接入", "#16a34a", lambda n: n.startswith("acc") or n == "dc-sw"),
    ("host", "终端/服务器", "#0891b2", lambda n: True),
]
NODE_CN = {
    "internet": "外网模拟", "inet-sw": "外网二层", "r1": "出口路由1", "r2": "出口路由2",
    "untrust-sw": "Untrust 二层", "fw1": "防火墙1", "fw2": "防火墙2",
    "trust-sw": "Trust 二层", "dmz-sw": "DMZ 二层",
    "core1": "核心1", "core2": "核心2",
    "agg-t1": "教学汇聚1", "agg-t2": "教学汇聚2",
    "agg-d1": "宿舍汇聚1", "agg-d2": "宿舍汇聚2",
    "agg-l1": "实验汇聚1", "agg-l2": "实验汇聚2",
    "agg-lib1": "图书馆汇聚1", "agg-lib2": "图书馆汇聚2",
    "agg-life1": "生活区汇聚1", "agg-life2": "生活区汇聚2",
    "acc-ta": "教学A接入", "acc-tb": "教学B接入", "acc-d1": "宿舍接入",
    "acc-la": "实验接入", "acc-lib": "图书馆接入", "acc-life": "生活区接入",
    "dc-sw": "数据中心接入",
    "pc-ta1": "教学PC1", "pc-ta2": "教学PC2", "pc-tb1": "教学PC3",
    "pc-d1": "宿舍PC", "pc-la1": "实验PC", "pc-lib": "图书馆PC", "pc-life": "生活区PC",
    "pc-dyn1": "动态终端1", "pc-dyn2": "动态终端2", "pc-dyn3": "动态终端3",
    "ap-ta": "教学AP", "ap-d1": "宿舍AP", "mgmt-pc": "管理PC",
    "srv-dc1": "数据中心1", "srv-dc2": "数据中心2", "srv-dmz": "DMZ服务器",
}
HOST_COLORS = {"srv": "#0891b2", "pc": "#64748b", "ap": "#0d9488", "misc": "#94a3b8"}
GAP = {"internet": 220, "inet_sw": 220, "edge": 220, "untrust_sw": 220, "fw": 220,
       "zone_sw": 220, "core": 220, "agg": 190, "access": 150, "host": 105}


def layer_of(name: str) -> str:
    for lid, _, _, rule in LAYERS:
        if rule(name):
            return lid
    return "host"


def host_kind(name: str) -> str:
    if name.startswith("srv"):
        return "srv"
    if name.startswith("ap"):
        return "ap"
    if name.startswith("pc") or name in ("internet", "mgmt-pc"):
        return "pc"
    return "misc"


# ---------------------------------------------------------------- 仿真数据
def load_sim() -> tuple[list[str], list[tuple[str, str]]]:
    if TOPO_JSON.exists():
        data = json.loads(TOPO_JSON.read_text(encoding="utf-8"))
        nodes = [n.get("shortname", k)
                 for k, n in sorted(data["nodes"].items(), key=lambda kv: int(kv[1].get("index", 0)))]
        links = [(l["endpoints"]["a"]["node"], l["endpoints"]["z"]["node"]) for l in data["links"]]
        return nodes, links
    text = CLAB_YML.read_text(encoding="utf-8")
    nodes = [m.group(1) for m in __import__("re").finditer(r"^    (\w[\w-]*):\s*$", text, __import__("re").MULTILINE)
             if m.group(1) not in ("nodes", "links", "topology")]
    links = [(m.group(1), m.group(3)) for m in
             __import__("re").finditer(r'endpoints:\s*\["([^:]+):([^"]+)",\s*"([^:]+):([^"]+)"\]', text)]
    return nodes, links


def sim_layout(nodes):
    buckets = defaultdict(list)
    for n in nodes:
        buckets[layer_of(n)].append(n)
    max_w = max((len(v) - 1) * GAP[lid] for lid, _, _, _ in LAYERS for v in [buckets.get(lid, [])])
    pos, y, row = {}, 80.0, 165
    for lid, _, _, _ in LAYERS:
        g = sorted(buckets.get(lid, []))
        if g:
            total = (len(g) - 1) * GAP[lid]
            start = (max_w - total) / 2 + 80
            for i, n in enumerate(g):
                pos[n] = (start + i * GAP[lid], y, lid)
        y += row
    return pos, max_w + 160, y + 40


# ---------------------------------------------------------------- 完整设计布局
def building_layout():
    """按区域分块画出全部楼宇，返回 SVG 片段与画布尺寸。"""
    rows = cap.all_rows()
    by_region = defaultdict(list)
    for r in rows:
        by_region[r.region].append(r)

    parts = []
    y = 30.0
    canvas_w = 0.0
    BOX_W, BOX_H, GAPX, GAPY = 150, 62, 12, 12
    region_blocks = []

    # 每行数量：保证总宽不超过约 1200，字号才不至于溢出卡片
    PER_ROW = {"教学区": 5, "实验区": 4, "宿舍区": 7, "图书馆": 2,
               "生活区": 3, "数据中心": 1, "网络中心": 1, "出口": 1, "无线": 2}

    for region in REGION_ORDER:
        items = by_region.get(region, [])
        if not items:
            continue
        color = REGION_COLOR[region]
        per_row = PER_ROW.get(region, 5)
        n_rows = (len(items) + per_row - 1) // per_row
        rows_w = min(len(items), per_row) * (BOX_W + GAPX) - GAPX
        canvas_w = max(canvas_w, rows_w)
        agg = AGGREGATION.get(region, "")
        title = REGION_LABEL[region]
        parts.append(
            f'<text x="0" y="{y:.0f}" font-size="14" font-weight="700" fill="{color}" '
            f'font-family="system-ui,-apple-system,\'PingFang SC\',sans-serif">{title}</text>'
            f'<text x="{max(len(title)*14 + 10, 70)}" y="{y:.0f}" font-size="11" fill="#64748b" '
            f'font-family="system-ui,-apple-system,\'PingFang SC\',sans-serif">'
            f'共 {len(items)} 个网段 · {html.escape(agg)}</text>'
        )
        top = y + 12
        for i, r in enumerate(items):
            cx = (i % per_row) * (BOX_W + GAPX)
            cy = top + (i // per_row) * (BOX_H + GAPY)
            info = next((v for k, v in BUILDING_INFO.items() if r.building.startswith(k)),
                        dict(floors=0, points=0, per=""))
            name = html.escape(r.building)
            line2 = f"VLAN {r.vlan} · {r.subnet}"
            if info["floors"]:
                line3 = f"{info['floors']} 层 · 单栋 {info['points']} 点"
            else:
                line3 = info["per"].split("（")[0][:18] or "—"
            parts.append(
                f'<g class="bld"><title>{name} — VLAN {r.vlan}，{r.subnet}，网关 {r.gateway}\n'
                f'{html.escape(info["per"])}</title>'
                f'<rect x="{cx:.0f}" y="{cy:.0f}" width="{BOX_W}" height="{BOX_H}" rx="7" '
                f'fill="#fff" stroke="{color}" stroke-width="1.3"/>'
                f'<rect x="{cx:.0f}" y="{cy:.0f}" width="4" height="{BOX_H}" rx="2" fill="{color}"/>'
                f'<text x="{cx + 12:.0f}" y="{cy + 21:.0f}" font-size="12.5" font-weight="600" '
                f'fill="#0f172a" font-family="system-ui,-apple-system,\'PingFang SC\',sans-serif">{name}</text>'
                f'<text x="{cx + 12:.0f}" y="{cy + 37:.0f}" font-size="9.5" fill="#475569" '
                f'font-family="ui-monospace,Menlo,monospace">{line2}</text>'
                f'<text x="{cx + 12:.0f}" y="{cy + 51:.0f}" font-size="9.5" fill="#64748b" '
                f'font-family="system-ui,-apple-system,\'PingFang SC\',sans-serif">{html.escape(line3)}</text>'
                f'</g>'
            )
        region_blocks.append((region, len(items)))
        y = top + n_rows * (BOX_H + GAPY) + 22

    return "\n".join(parts), canvas_w + 20, y, region_blocks


def sim_svg(nodes, links, pos):
    parts = []
    for a, b in links:
        if a not in pos or b not in pos:
            continue
        ax, ay, al = pos[a]
        bx, by, bl = pos[b]
        cls = "link " + " ".join(f"l-{l}" for l in {al, bl})
        parts.append(f'<line class="{cls}" x1="{ax:.0f}" y1="{ay:.0f}" x2="{bx:.0f}" y2="{by:.0f}" '
                     f'stroke="#cbd5e1" stroke-width="1.2" opacity="0.75"/>')
    for n in nodes:
        if n not in pos:
            continue
        x, y, lid = pos[n]
        if lid == "host":
            color, r = HOST_COLORS[host_kind(n)], 11
            cls = f"node l-{lid} l-host-{host_kind(n)}"
        else:
            color = next(c for l, _, c, _ in LAYERS if l == lid)
            r = 15
            cls = f"node l-{lid}"
        parts.append(
            f'<g class="{cls}" data-layer="{lid}"><title>{html.escape(n)}</title>'
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{color}" stroke="#fff" stroke-width="2"/>'
            f'<text x="{x:.0f}" y="{y + r + 13:.0f}" text-anchor="middle" font-size="10.5" fill="#334155" '
            f'font-family="ui-monospace,Menlo,monospace">{html.escape(NODE_CN.get(n, n))}</text></g>')
    return "\n".join(parts)


# ---------------------------------------------------------------- 页面
def build_page(design_svg, dw, dh, sim_svg_body, sim_w, sim_h, nodes, links, region_blocks):
    counts = defaultdict(int)
    for n in nodes:
        counts[layer_of(n)] += 1
    toggles = "".join(
        f'<label class="tg" data-layer="{lid}"><input type="checkbox" checked '
        f'onchange="toggleLayer(this,\'{lid}\')"><i style="background:{c}"></i>{lab}'
        f'<span class="cnt">{counts.get(lid,0)}</span></label>'
        for lid, lab, c, _ in LAYERS if counts.get(lid, 0))

    legend = "".join(
        f'<span class="lg"><i style="background:{REGION_COLOR[rg]}"></i>{REGION_LABEL[rg]}'
        f'<span class="cnt">{n}</span></span>' for rg, n in region_blocks)

    total_buildings = sum(n for _, n in region_blocks)
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>奉贤校区校园网拓扑 · 完整布局与仿真</title>
<style>
  :root{{--bd:#e2e8f0;--muted:#64748b}}
  *{{box-sizing:border-box}}
  body{{margin:0;font-family:system-ui,-apple-system,"PingFang SC",sans-serif;background:#f8fafc;color:#0f172a}}
  header{{padding:14px 22px 10px;background:#fff;border-bottom:1px solid var(--bd)}}
  h1{{margin:0;font-size:16px;font-weight:650}}
  .meta{{margin-top:4px;font-size:12px;color:var(--muted)}}
  .bar{{display:flex;flex-wrap:wrap;gap:10px;align-items:center;padding:10px 22px;background:#fff;
       border-bottom:1px solid var(--bd);position:sticky;top:0;z-index:5}}
  .tabs{{display:flex;gap:4px;margin-right:14px}}
  .tab{{font:inherit;font-size:13px;padding:6px 14px;border-radius:8px;border:1px solid var(--bd);
        background:#fff;cursor:pointer;font-weight:600;color:#475569}}
  .tab.on{{background:#0f172a;color:#fff;border-color:#0f172a}}
  .tg{{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;cursor:pointer;user-select:none;
       padding:4px 9px;border-radius:999px;border:1px solid var(--bd);background:#fff}}
  .tg:hover{{background:#f1f5f9}}
  .tg i,.lg i{{width:9px;height:9px;border-radius:50%;display:inline-block}}
  .lg{{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;padding:4px 9px;
       border-radius:999px;border:1px solid var(--bd);background:#fff}}
  .cnt{{color:var(--muted);font-size:11px}}
  .spacer{{flex:1}}
  button.act{{font:inherit;font-size:12.5px;padding:5px 12px;border-radius:7px;border:1px solid var(--bd);
              background:#fff;cursor:pointer}}
  button.act:hover{{background:#f1f5f9}}
  #wrap{{height:calc(100vh - 112px);overflow:auto;padding:18px;display:flex;justify-content:center;
         align-items:flex-start}}
  svg{{background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(15,23,42,.08);flex:none}}
  .hidden-layer,.link.hidden-layer{{display:none}}
  .totals{{font-size:12.5px;color:var(--muted);margin-left:8px}}
</style></head><body>
<header>
  <h1>奉贤校区校园网 · 拓扑总览</h1>
  <div class="meta" id="sub">完整设计布局：{total_buildings} 个楼宇/网段，涵盖教学楼 A–E、实验楼 A–H、学生公寓 1–28 号楼、图书馆、食堂与体育馆等</div>
</header>
<div class="bar">
  <div class="tabs">
    <button class="tab on" onclick="showView('design',this)">完整设计布局</button>
    <button class="tab" onclick="showView('sim',this)">仿真运行拓扑</button>
  </div>
  <span id="legend-design">{legend}</span>
  <span id="legend-sim" style="display:none">{toggles}</span>
  <span class="spacer"></span>
  <span id="ops-sim" style="display:none">
    <button class="act" onclick="setZoom(-0.15)">−</button>
    <button class="act" onclick="setZoom(0.15)">+</button>
    <button class="act" onclick="fit()">适应窗口</button>
    <button class="act" onclick="allOn()">全部显示</button>
  </span>
</div>
<div id="wrap">
<div id="view-design">
<svg id="svg-design" viewBox="0 0 {dw:.0f} {dh:.0f}" xmlns="http://www.w3.org/2000/svg">
{design_svg}
</svg>
</div>
<div id="view-sim" style="display:none">
<svg id="svg-sim" viewBox="0 0 {sim_w:.0f} {sim_h:.0f}" xmlns="http://www.w3.org/2000/svg">
{sim_svg_body}
</svg>
</div>
</div>
<script>
const wrap = document.getElementById('wrap');
let view = 'design', scale = 1;
const SVG = {{design: document.getElementById('svg-design'), sim: document.getElementById('svg-sim')}};

function apply(){{
  const s = SVG[view];
  const vb = s.viewBox.baseVal;
  const availW = wrap.clientWidth - 44, availH = wrap.clientHeight - 44;
  // 等比缩放到完整可见（不裁切）；scale=1 即"适应窗口"
  const k = Math.min(availW / vb.width, availH / vb.height) * scale;
  s.style.width  = (vb.width  * k) + 'px';
  s.style.height = (vb.height * k) + 'px';
}}
function showView(v, btn){{
  view = v; scale = 1;
  document.getElementById('view-design').style.display = v === 'design' ? '' : 'none';
  document.getElementById('view-sim').style.display = v === 'sim' ? '' : 'none';
  document.getElementById('legend-design').style.display = v === 'design' ? '' : 'none';
  document.getElementById('legend-sim').style.display = v === 'sim' ? '' : 'none';
  document.getElementById('ops-sim').style.display = v === 'sim' ? '' : 'none';
  document.getElementById('sub').textContent = v === 'design'
    ? '完整设计布局：{total_buildings} 个楼宇/网段，涵盖教学楼 A–E、实验楼 A–H、学生公寓 1–28 号楼、图书馆、食堂与体育馆等'
    : '仿真运行拓扑：{len(nodes)} 个节点、{len(links)} 条链路，按网络层级排布';
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('on'));
  btn.classList.add('on');
  apply();
}}
function setZoom(d){{ scale = Math.min(3, Math.max(0.3, scale + d)); apply(); }}
function fit(){{ scale = 1; apply(); }}
function toggleLayer(cb, L){{
  const s = SVG.sim;
  s.querySelectorAll('.l-' + L).forEach(el => el.classList.toggle('hidden-layer', !cb.checked));
  const vis = new Set();
  document.querySelectorAll('#legend-sim .tg').forEach(t => {{
    if (t.querySelector('input').checked) vis.add(t.dataset.layer);
  }});
  s.querySelectorAll('.link').forEach(el => {{
    const ls = [...el.classList].filter(c => c.startsWith('l-') && c !== 'link');
    el.classList.toggle('hidden-layer', !ls.every(c => vis.has(c.slice(2))));
  }});
}}
function allOn(){{
  document.querySelectorAll('#legend-sim input').forEach(cb => cb.checked = true);
  SVG.sim.querySelectorAll('.hidden-layer').forEach(el => el.classList.remove('hidden-layer'));
}}
window.addEventListener('resize', apply);
window.addEventListener('load', apply);
apply();
</script>
</body></html>"""


def main() -> int:
    design_svg, dw, dh, region_blocks = building_layout()
    nodes, links = load_sim()
    pos, sim_w, sim_h = sim_layout(nodes)
    sim_body = sim_svg(nodes, links, pos)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_page(design_svg, dw, dh, sim_body, sim_w, sim_h, nodes, links, region_blocks),
                   encoding="utf-8")
    print(f"已生成 {OUT.relative_to(ROOT)}")
    print(f"  完整设计视图：{sum(n for _, n in region_blocks)} 个楼宇/网段，画布 {dw:.0f}x{dh:.0f}")
    for rg, n in region_blocks:
        print(f"    {REGION_LABEL[rg]}: {n}")
    print(f"  仿真视图：{len(nodes)} 节点 / {len(links)} 链路，画布 {sim_w:.0f}x{sim_h:.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
