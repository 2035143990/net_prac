#!/usr/bin/env python3
"""对 clab-io-draw 生成的 draw.io 文件做可读性优化。

优化内容：
1. 删除每条链路上的接口名标签（122 个），避免线缆区域文字密集；
2. 将层级行距由 175 px 增加到 240 px，缓解纵向拥挤；
3. 链路改为浅灰色、带弧线跳线的细线，降低视觉权重。

只修改显示属性，不改变节点、链路及其连接关系。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROW_OLD = 175.0      # clab-io-draw 默认 padding_y
ROW_NEW = 240.0      # 优化后的行距
TOP_Y = 100.0
BOTTOM_MARGIN = 100.0

# 接口标签是独立的 edgeLabel 单元格，删除后 draw.io 中不再显示 ethX。
EDGE_LABEL_RE = re.compile(
    r'\s*<mxCell id="[^"]+" value="[^"]*" style="edgeLabel;.*?" vertex="1".*?</mxCell>',
    re.DOTALL,
)

# 只缩放节点（vertex）的 y 坐标；链路是 edge 单元格，没有绝对坐标。
VERTEX_GEOM_RE = re.compile(
    r'(<mxCell[^>]*\bvertex="1"[^>]*>\s*<mxGeometry x="[\d.]+" y=")([\d.]+)(")'
)

LINK_STYLE_OLD = 'style="endArrow=none;jumpStyle=gap;'
LINK_STYLE_NEW = (
    'style="endArrow=none;jumpStyle=arc;strokeColor=#94A3B8;'
    'strokeWidth=1.5;opacity=75;'
)


def main(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    text = EDGE_LABEL_RE.sub("", text)
    text = text.replace(LINK_STYLE_OLD, LINK_STYLE_NEW)

    max_y = 0.0

    def scale(match: re.Match[str]) -> str:
        nonlocal max_y
        old_y = float(match.group(2))
        new_y = TOP_Y + (old_y - TOP_Y) * ROW_NEW / ROW_OLD
        max_y = max(max_y, new_y)
        return f"{match.group(1)}{new_y:.1f}{match.group(3)}"

    text = VERTEX_GEOM_RE.sub(scale, text)

    # 节点高 75 px，底部再留 100 px 空白。
    page_height = max_y + 75.0 + BOTTOM_MARGIN
    text, n = re.subn(
        r'(pageHeight=")[\d.]+(")',
        rf"\g<1>{page_height:.1f}\g<2>",
        text,
        count=1,
    )
    if n != 1:
        raise SystemExit("无法找到 pageHeight，文件格式可能已变化")

    path.write_text(text, encoding="utf-8")
    print(
        f"优化完成：行距 {ROW_OLD:.0f} -> {ROW_NEW:.0f} px，"
        f"页面高度 {page_height:.0f} px，已移除接口标签。"
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"用法: {sys.argv[0]} <campus-lab.clab.drawio>")
    main(Path(sys.argv[1]))
