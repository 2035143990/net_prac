#!/usr/bin/env python3
"""把 docs/figures 下的示意图 SVG 转成报告引用的 PNG。

报告正文引用的是 .png（2400 px 宽），SVG 保留为可编辑源文件。

渲染优先用无头浏览器（Chrome / Edge / Chromium），SVG 原生渲染，中文字体、
描边、虚线、圆角都与浏览器中一致；找不到浏览器时回退到 svglib 纯 Python 链路：

    SVG --(svglib)--> Drawing --(renderPDF)--> PDF --(pypdfium2)--> PNG

用法：
    python3 tools/svg2png.py                # 转换 docs/figures 下全部 SVG
    python3 tools/svg2png.py --width 2400   # 指定输出宽度
    python3 tools/svg2png.py --backend svglib  # 强制使用纯 Python 后端
"""
from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIG_DIR = REPO / "docs" / "figures"
DEFAULT_WIDTH = 2400

BROWSER_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/microsoft-edge",
]

# (family, bold) -> 候选字体文件，按平台顺序尝试
CJK_FONT_CANDIDATES = [
    # Windows
    ("Microsoft YaHei", "C:/Windows/Fonts/msyh.ttc"),
    ("Microsoft YaHei", "C:/Windows/Fonts/msyhbd.ttc"),
    ("SimHei", "C:/Windows/Fonts/simhei.ttf"),
    ("SimSun", "C:/Windows/Fonts/simsun.ttc"),
    # macOS
    ("PingFang SC", "/System/Library/Fonts/PingFang.ttc"),
    ("Heiti SC", "/System/Library/Fonts/STHeiti Medium.ttc"),
    # Linux
    ("Noto Sans CJK SC", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    ("WenQuanYi Zen Hei", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
    # 通用兜底
    ("DejaVu Sans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]

_REGISTERED = False


# --------------------------------------------------------------------------
# 浏览器后端
# --------------------------------------------------------------------------
def find_browser() -> str | None:
    """查找可用的 Chrome / Edge 可执行文件。"""
    for path in BROWSER_CANDIDATES:
        if Path(path).exists():
            return path
    for name in ("chrome", "chromium", "chromium-browser", "google-chrome", "msedge"):
        found = shutil.which(name)
        if found:
            return found
    return None


def svg_size(svg_path: Path) -> tuple[int, int]:
    """从 SVG 根元素读取像素宽高。"""
    import re

    text = svg_path.read_text(encoding="utf-8")
    m = re.search(r'<svg[^>]*?\bwidth="([\d.]+)"[^>]*?\bheight="([\d.]+)"', text, re.S)
    if not m:
        m = re.search(r'<svg[^>]*?\bviewBox="([\d.\-]+)\s+([\d.\-]+)\s+([\d.]+)\s+([\d.]+)"', text, re.S)
        if not m:
            raise ValueError(f"无法读取 SVG 尺寸: {svg_path}")
        return int(float(m.group(3))), int(float(m.group(4)))
    return int(float(m.group(1))), int(float(m.group(2)))


def render_with_browser(browser: str, svg_path: Path, out_path: Path, width: int) -> tuple[int, int]:
    """用无头浏览器把 SVG 渲染成 PNG。

    Chrome 的 --screenshot 按 CSS 像素截取，--force-device-scale-factor 才能放大，
    因此这里按 width / svg_w 设置缩放倍数，保证输出位图宽度等于 width。
    """
    svg_w, svg_h = svg_size(svg_path)
    scale = width / svg_w
    height = max(1, round(svg_h * scale))

    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<style>html,body{margin:0;padding:0;background:transparent;}"
        f"svg{{display:block;width:{svg_w}px;height:{svg_h}px;}}</style>"
        f"</head><body>{svg_path.read_text(encoding='utf-8')}</body></html>"
    )

    with tempfile.TemporaryDirectory() as tmp:
        html_path = Path(tmp) / "fig.html"
        html_path.write_text(html, encoding="utf-8")
        png_path = Path(tmp) / "fig.png"
        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--default-background-color=00000000",
            f"--force-device-scale-factor={scale}",
            f"--window-size={svg_w},{svg_h}",
            f"--screenshot={png_path}",
            html_path.as_uri(),
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=180)
        if not png_path.exists():
            raise RuntimeError(
                f"浏览器渲染失败 (exit {proc.returncode}): "
                f"{proc.stderr.decode('utf-8', 'ignore')[-400:]}"
            )
        out_path.write_bytes(png_path.read_bytes())

    # 以实际位图尺寸为准，避免截图被浏览器裁剪后尺寸与预期不符。
    try:
        from PIL import Image

        with Image.open(out_path) as im:
            return im.width, im.height
    except Exception:  # noqa: BLE001 - 读不到就回退到推算值
        return width, height


# --------------------------------------------------------------------------
# 纯 Python 后端（svglib + reportlab + pypdfium2）
# --------------------------------------------------------------------------
def register_fonts() -> list[str]:
    """注册中文字体到 reportlab，返回实际使用的字体族列表。"""
    global _REGISTERED
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    if _REGISTERED:
        return pdfmetrics.getRegisteredFontNames()

    families: list[str] = []
    for family, path in CJK_FONT_CANDIDATES:
        if not Path(path).exists() or family in families:
            continue
        try:
            pdfmetrics.registerFont(TTFont(family, path))
            families.append(family)
        except Exception:  # noqa: BLE001 - 字体损坏/不支持时跳过
            continue

    if families:
        # registerFontFamily 需要字体名字符串，不能传 TTFont 对象。
        for family in families:
            pdfmetrics.registerFontFamily(
                family, normal=family, bold=family, italic=family, boldItalic=family
            )

    _REGISTERED = True
    return families


def svg_to_pdf_bytes(svg_path: Path) -> bytes:
    from reportlab.graphics import renderPDF
    from svglib.svglib import svg2rlg

    drawing = svg2rlg(str(svg_path))
    if drawing is None:
        raise ValueError(f"无法解析 SVG: {svg_path}")
    w, h = float(drawing.width), float(drawing.height)
    if w <= 0 or h <= 0:
        raise ValueError(f"SVG 尺寸非法: {w}x{h}")
    buf = io.BytesIO()
    renderPDF.drawToFile(drawing, buf, autoSize=0, pagesize=(w, h))
    return buf.getvalue()


def render_with_svglib(svg_path: Path, out_path: Path, width: int) -> tuple[int, int]:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(svg_to_pdf_bytes(svg_path))
    try:
        page = pdf[0]
        scale = width / page.get_width()
        image = page.render(scale=scale).to_pil()
        buf = io.BytesIO()
        image.save(buf, format="PNG", optimize=True)
        out_path.write_bytes(buf.getvalue())
        return image.width, image.height
    finally:
        pdf.close()


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    ap.add_argument("--dir", type=Path, default=FIG_DIR)
    ap.add_argument("--backend", choices=("auto", "browser", "svglib"), default="auto")
    args = ap.parse_args()

    browser = find_browser() if args.backend in ("auto", "browser") else None
    if args.backend == "browser" and not browser:
        raise SystemExit("未找到 Chrome / Edge，可改用 --backend svglib")
    if args.backend == "auto":
        if browser:
            print(f"==> 使用浏览器后端: {browser}")
        else:
            print("==> 未找到浏览器，回退到 svglib 后端")
            families = register_fonts()
            if families:
                print(f"==> 中文字体: {', '.join(families)}")
            else:
                print("警告：未找到中文字体，中文可能渲染为方框", file=sys.stderr)

    svg_files = sorted(args.dir.glob("*.svg"))
    if not svg_files:
        raise SystemExit(f"未找到 SVG: {args.dir}")

    failed = []
    for svg in svg_files:
        out = svg.with_suffix(".png")
        try:
            if browser:
                w, h = render_with_browser(browser, svg, out, args.width)
            else:
                w, h = render_with_svglib(svg, out, args.width)
        except Exception as exc:  # noqa: BLE001 - 逐个报告失败项
            failed.append((svg.name, exc))
            print(f"FAIL  {svg.name}: {exc}", file=sys.stderr)
            continue
        print(f"OK    {out.name}  {w}x{h}")

    if failed:
        print(f"\n{len(failed)} 个文件转换失败", file=sys.stderr)
        return 1
    print(f"\n共转换 {len(svg_files)} 个文件")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    raise SystemExit(main())
