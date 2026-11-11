#!/usr/bin/env python3
"""把仓库内的文本文件统一转换为 LF 行尾。

Windows 全局 git core.autocrlf=true 会让 shell 脚本在检出后变成 CRLF，
导致 Linux/WSL 下 `set -e` 报 "Illegal option"、命令被当成 `cmd\r` 而找不到。

配合仓库根目录的 .gitattributes（*.sh text eol=lf）使用。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

TEXT_SUFFIXES = {
    ".sh", ".bash", ".py", ".yml", ".yaml", ".md", ".conf", ".nft",
    ".cfg", ".txt", ".svg", ".drawio", ".json",
}

# 这些目录不参与转换（构建产物、依赖、虚拟环境等）
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "clab-campus-lab", "results", ".clab",
}


def is_skipped(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def main() -> int:
    changed: list[Path] = []
    total = 0

    for path in REPO.rglob("*"):
        if not path.is_file():
            continue
        if is_skipped(path.relative_to(REPO)):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue

        total += 1
        data = path.read_bytes()
        if b"\r\n" not in data:
            continue
        # 只把 CRLF 换成 LF，不动裸 CR
        path.write_bytes(data.replace(b"\r\n", b"\n"))
        changed.append(path.relative_to(REPO))

    print(f"扫描 {total} 个文本文件")
    if not changed:
        print("没有需要转换的文件（行尾已是 LF）")
        return 0

    print(f"转换 {len(changed)} 个文件为 LF 行尾：")
    for p in changed:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
