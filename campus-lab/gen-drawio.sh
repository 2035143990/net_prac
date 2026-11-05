#!/bin/sh
# 生成分层 draw.io 拓扑图并做可读性优化。
# 依赖 campus-lab.clab.yml 中由 gen.py 写入的 graph-level 标签。
# Run from anywhere; paths are resolved relative to this script.
set -e
cd "$(dirname "$0")"
sh run-clab.sh graph --drawio \
  --drawio-args "--layout vertical" \
  -o -t campus-lab.clab.yml
python3 drawio-postprocess.py campus-lab.clab.drawio
