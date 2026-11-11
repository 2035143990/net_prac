#!/usr/bin/env python3
"""从 containerlab 拓扑生成交互式 HTML 演示页。

数据源优先级：
1. campus-lab/clab-campus-lab/topology-data.json（containerlab 运行时导出，含节点与链路）
2. campus-lab/campus-lab.clab.yml（生成器产出的拓扑定义，含接口）

输出 docs/topology.html：自包含、无需安装任何软件，双击即可在浏览器打开。

用法：
    python3 tools/gen_topology_html.py
"""
from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "campus-lab"
TOPO_JSON = LAB / "clab-campus-lab" / "topology-data.json"
CLAB_YML = LAB / "campus-lab.clab.yml"
OUT = ROOT / "docs" / "topology.html"

# ---------------------------------------------------------------- 分层定义
# 每个节点按名称前缀归入一层；层序决定自上而下的排列。
LAYERS = [
    # (层 id, 显示名, 颜色, 判定规则)
    ("internet", "外网", "#64748b", lambda n: n == "internet"),
    ("inet_sw", "外网汇聚", "#94a3b8", lambda n: n == "inet-sw"),
    ("edge", "出口路由", "#ea580c", lambda n: n in ("r1", "r2")),
    ("untrust_sw", "Untrust 二层", "#a78bfa", lambda n: n == "untrust-sw"),
    ("fw", "防火墙", "#9333ea", lambda n: n.startswith("fw")),
    ("zone_sw", "Trust / DMZ 二层", "#34d399",
     lambda n: n in ("trust-sw", "dmz-sw")),
    ("core", "核心", "#dc2626", lambda n: n.startswith("core")),
    ("agg", "汇聚", "#2563eb", lambda n: n.startswith("agg")),
    ("access", "接入", "#16a34a", lambda n: n.startswith("acc") or n == "dc-sw"),
    ("host", "终端/服务器", "#0891b2", lambda n: True),
]

# 终端与服务器进一步细分显示色（同属 host 层）
HOST_COLORS = {
    "srv": "#0891b2",   # 服务器
    "pc": "#64748b",    # PC
    "ap": "#0d9488",    # AP
    "misc": "#94a3b8",  # 其他
}

# 各层的节点横向间距（层序自上而下）
GAP = {"internet": 220, "inet_sw": 220, "edge": 220, "untrust_sw": 220,
       "fw": 220, "zone_sw": 220, "core": 220,
       "agg": 190, "access": 150, "host": 105}
ROW_HEIGHT = 165


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


# ---------------------------------------------------------------- 数据读取
def load_nodes_and_links() -> tuple[list[str], list[tuple[str, str]]]:
    if TOPO_JSON.exists():
        data = json.loads(TOPO_JSON.read_text(encoding="utf-8"))
        nodes = [n["shortname"] if "shortname" in n else k
                 for k, n in sorted(data["nodes"].items(), key=lambda kv: int(kv[1].get("index", 0)))]
        links = []
        for link in data["links"]:
            a = link["endpoints"]["a"]["node"]
            b = link["endpoints"]["z"]["node"]
            links.append((a, b))
        return nodes, links

    # 回退：解析 clab.yml
    text = CLAB_YML.read_text(encoding="utf-8")
    nodes = []
    for m in re.finditer(r"^    (\w[\w-]*):\s*$", text, re.MULTILINE):
        if m.group(1) not in ("nodes", "links", "topology"):
            nodes.append(m.group(1))
    links = []
    for m in re.finditer(r'endpoints:\s*\["([^:]+):([^"]+)",\s*"([^:]+):([^"]+)"\]', text):
        links.append((m.group(1), m.group(3)))
    return nodes, links


# ---------------------------------------------------------------- 布局
def layout(nodes: list[str]) -> dict[str, tuple[float, float, str]]:
    """按层排布，返回 {node: (x, y, layer)}。每层内节点水平居中、均匀分布。"""
    buckets: dict[str, list[str]] = defaultdict(list)
    for n in nodes:
        buckets[layer_of(n)].append(n)

    pos: dict[str, tuple[float, float, str]] = {}
    max_width = 0.0
    for _, _, _, _ in LAYERS:
        pass
    # 先估算最大宽度，用于整体居中
    widths = {}
    for lid, _, _, _ in LAYERS:
        count = len(buckets.get(lid, []))
        widths[lid] = max(count - 1, 0) * GAP[lid]
        max_width = max(max_width, widths[lid])

    y = 90.0
    for li, (lid, _, _, _) in enumerate(LAYERS):
        group = buckets.get(lid, [])
        if not group:
            y += ROW_HEIGHT
            continue
        # 层内排序：汇聚/接入按区域名，终端按名称
        group.sort()
        n = len(group)
        total = (n - 1) * GAP[lid]
        start = (max_width - total) / 2 + 80
        for i, name in enumerate(group):
            pos[name] = (start + i * GAP[lid], y, lid)
        y += ROW_HEIGHT
    return pos, max_width + 160, y + 60


# ---------------------------------------------------------------- SVG 生成
def build_svg(nodes, links, pos, width, height) -> str:
    parts = []

    # 链路（先画，避免盖住节点）
    for a, b in links:
        if a not in pos or b not in pos:
            continue
        ax, ay, al = pos[a]
        bx, by, bl = pos[b]
        layers = {al, bl}
        cls = "link " + " ".join(f"l-{l}" for l in layers)
        parts.append(
            f'<line class="{cls}" x1="{ax:.0f}" y1="{ay:.0f}" '
            f'x2="{bx:.0f}" y2="{by:.0f}" stroke="#cbd5e1" stroke-width="1.2" opacity="0.75"/>'
        )

    # 节点
    for name in nodes:
        if name not in pos:
            continue
        x, y, lid = pos[name]
        if lid == "host":
            color = HOST_COLORS[host_kind(name)]
            r = 11
        else:
            color = next(c for l, _, c, _ in LAYERS if l == lid)
            r = 15
        cls = f"node l-{lid} l-host-{host_kind(name)}" if lid == "host" else f"node l-{lid}"
        parts.append(
            f'<g class="{cls}" data-name="{html.escape(name)}" data-layer="{lid}">'
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{color}" '
            f'stroke="#ffffff" stroke-width="2"/>'
            f'<text x="{x:.0f}" y="{y + r + 13:.0f}" text-anchor="middle" font-size="10.5" '
            f'fill="#334155" font-family="ui-monospace,SFMono-Regular,Menlo,monospace">'
            f'{html.escape(name)}</text></g>'
        )
    return "\n".join(parts)


def build_html(nodes, links, svg_body, width, height) -> str:
    layer_meta = []
    counts = defaultdict(int)
    for n in nodes:
        counts[layer_of(n)] += 1
    for lid, label, color, _ in LAYERS:
        c = counts.get(lid, 0)
        if c == 0:
            continue
        layer_meta.append((lid, label, color, c))

    toggles = "".join(
        f'<label class="tg" data-layer="{lid}">'
        f'<input type="checkbox" checked onchange="toggle(this, \'{lid}\')">'
        f'<i style="background:{color}"></i>{label}'
        f'<span class="cnt">{c}</span></label>'
        for lid, label, color, c in layer_meta
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>奉贤校区校园网拓扑 · {len(nodes)} 节点 / {len(links)} 链路</title>
<style>
  :root {{ --border:#e2e8f0; --muted:#64748b; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:system-ui,-apple-system,"PingFang SC",sans-serif;
          background:#f8fafc; color:#0f172a; }}
  header {{ padding:14px 22px 10px; background:#fff; border-bottom:1px solid var(--border); }}
  h1 {{ margin:0; font-size:16px; font-weight:650; letter-spacing:.2px; }}
  .meta {{ margin-top:4px; font-size:12px; color:var(--muted); }}
  .bar {{ display:flex; flex-wrap:wrap; gap:14px; align-items:center;
          padding:10px 22px; background:#fff; border-bottom:1px solid var(--border);
          position:sticky; top:0; z-index:5; }}
  .tg {{ display:inline-flex; align-items:center; gap:6px; font-size:12.5px;
         cursor:pointer; user-select:none; padding:4px 9px; border-radius:999px;
         border:1px solid var(--border); background:#fff; transition:.15s; }}
  .tg:hover {{ background:#f1f5f9; }}
  .tg input {{ margin:0; cursor:pointer; }}
  .tg i {{ width:9px; height:9px; border-radius:50%; display:inline-block; }}
  .tg .cnt {{ color:var(--muted); font-size:11px; }}
  .spacer {{ flex:1; }}
  .btns {{ display:flex; gap:6px; }}
  button {{ font:inherit; font-size:12.5px; padding:5px 12px; border-radius:7px;
            border:1px solid var(--border); background:#fff; cursor:pointer; color:#0f172a; }}
  button:hover {{ background:#f1f5f9; }}
  #wrap {{ height:calc(100vh - 108px); overflow:auto; padding:18px;
           display:flex; justify-content:center; align-items:flex-start; }}
  svg {{ background:#fff; border-radius:12px; box-shadow:0 1px 3px rgba(15,23,42,.08);
         flex:none; }}
  .node circle {{ transition:r .12s ease; }}
  .node:hover circle {{ stroke:#0f172a; }}
  .node text {{ pointer-events:none; }}
  .hidden-layer {{ display:none; }}
  .link.hidden-layer {{ display:none; }}
</style></head><body>
<header>
  <h1>奉贤校区校园网 · 仿真拓扑</h1>
  <div class="meta">{len(nodes)} 个节点 · {len(links)} 条链路 · 由 containerlab 生成 · 可勾选图层单独查看</div>
</header>
<div class="bar">
  {toggles}
  <span class="spacer"></span>
  <span class="btns">
    <button onclick="setZoom(-0.15)">−</button>
    <button onclick="setZoom(0.15)">+</button>
    <button onclick="fit()">适应窗口</button>
    <button onclick="allOn()">全部显示</button>
  </span>
</div>
<div id="wrap">
<svg id="topo" viewBox="0 0 {width:.0f} {height:.0f}" xmlns="http://www.w3.org/2000/svg">
{svg_body}
</svg>
</div>
<script>
const svg = document.getElementById('topo');
const wrap = document.getElementById('wrap');
const VBW = svg.viewBox.baseVal.width, VBH = svg.viewBox.baseVal.height;
let scale = 1;

function apply() {{
  const availW = wrap.clientWidth - 36;
  const availH = wrap.clientHeight - 36;
  const base = Math.min(availW / VBW, availH / VBH);
  svg.style.width  = (VBW * base * scale) + 'px';
  svg.style.height = (VBH * base * scale) + 'px';
}}
function setZoom(d) {{ scale = Math.min(3, Math.max(0.25, scale + d)); apply(); }}
function fit() {{ scale = 1; apply(); }}

function toggle(cb, layer) {{
  const on = cb.checked;
  const L = layer;
  svg.querySelectorAll('.l-' + L).forEach(el => el.classList.toggle('hidden-layer', !on));
  // 链路：仅当两端图层都可见时才显示
  const visible = new Set();
  document.querySelectorAll('.tg').forEach(t => {{
    if (t.querySelector('input').checked) visible.add(t.dataset.layer);
  }});
  svg.querySelectorAll('.link').forEach(el => {{
    const ls = [...el.classList].filter(c => c.startsWith('l-') && c !== 'link');
    const show = ls.every(c => visible.has(c.slice(2)));
    el.classList.toggle('hidden-layer', !show);
  }});
}}
function allOn() {{
  document.querySelectorAll('.tg input').forEach(cb => {{ cb.checked = true; }});
  svg.querySelectorAll('.hidden-layer').forEach(el => el.classList.remove('hidden-layer'));
}}
window.addEventListener('resize', apply);
window.addEventListener('load', apply);
apply();
</script>
</body></html>"""


def main() -> int:
    nodes, links = load_nodes_and_links()
    if not nodes:
        print("未读取到拓扑节点，请检查 topology-data.json 或 campus-lab.clab.yml")
        return 1
    pos, width, height = layout(nodes)
    svg_body = build_svg(nodes, links, pos, width, height)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_html(nodes, links, svg_body, width, height), encoding="utf-8")
    layers = defaultdict(int)
    for n in nodes:
        layers[layer_of(n)] += 1
    print(f"已生成 {OUT.relative_to(ROOT)}")
    print(f"  节点 {len(nodes)} / 链路 {len(links)} / 画布 {width:.0f}x{height:.0f}")
    print("  分层: " + ", ".join(f"{lid}={c}" for lid, c in layers.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
