#!/bin/sh
# Unified campus-lab test runner.
# Usage: sh tests/run-all.sh [suite ...]
# Exit: 0 all pass/skip, 1 any fail, 2 environment unavailable.
set -u
cd "$(dirname "$0")/.." || exit 2
P=clab-campus-lab-
RUN_ID=${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}
RESULT_DIR=${RESULT_DIR:-tests/results/$RUN_ID}
export P RUN_ID RESULT_DIR
mkdir -p "$RESULT_DIR/raw" 2>/dev/null || { echo "cannot create $RESULT_DIR" >&2; exit 2; }
: > "$RESULT_DIR/results.jsonl"
: > "$RESULT_DIR/suites.tsv"
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)

if ! docker info >/dev/null 2>&1; then
  echo "ENV: Docker daemon unavailable" >&2
  printf 'run_id=%s\nstarted=%s\nresult=ENV_UNAVAILABLE\nreason=docker daemon unavailable\n' "$RUN_ID" "$START" > "$RESULT_DIR/summary.txt"
  exit 2
fi

if [ ! -f configs/facts.json ]; then
  python3 gen.py >/dev/null 2>&1 || { echo "ENV: gen.py failed" >&2; exit 2; }
fi
EXPECTED=$(python3 -c 'import json;print(json.load(open("configs/facts.json"))["nodes"]["total"])' 2>/dev/null)
ACTUAL=$(docker ps --filter "name=${P}" --format '{{.Names}}' 2>/dev/null | wc -l | tr -d ' ')
if [ "${EXPECTED:-0}" -le 0 ] || [ "${ACTUAL:-0}" -lt "${EXPECTED:-0}" ]; then
  echo "ENV: expected $EXPECTED containers, found $ACTUAL" >&2
  printf 'run_id=%s\nstarted=%s\nresult=ENV_UNAVAILABLE\nexpected_nodes=%s\nactual_nodes=%s\n' "$RUN_ID" "$START" "$EXPECTED" "$ACTUAL" > "$RESULT_DIR/summary.txt"
  exit 2
fi

DEFAULT_SUITES="switching connectivity routing security dhcp iso nat lag failover"
SUITES=${*:-$DEFAULT_SUITES}
OVERALL=0
for suite in $SUITES; do
  script="tests/${suite}.sh"
  [ -f "$script" ] || script="tests/suites/${suite}.sh"
  if [ ! -f "$script" ]; then
    echo "SKIP suite $suite: script not found" | tee -a "$RESULT_DIR/suites.tsv"
    continue
  fi
  sh "$script"
  rc=$?
  [ "$rc" -ne 0 ] && OVERALL=1
done

FINISH=$(date -u +%Y-%m-%dT%H:%M:%SZ)
TOTAL=$(wc -l < "$RESULT_DIR/results.jsonl" | tr -d ' ')
PASS=$(grep -c '"status":"PASS"' "$RESULT_DIR/results.jsonl" 2>/dev/null || true)
FAIL=$(grep -c '"status":"FAIL"' "$RESULT_DIR/results.jsonl" 2>/dev/null || true)
SKIP=$(grep -c '"status":"SKIP"' "$RESULT_DIR/results.jsonl" 2>/dev/null || true)
PASS=${PASS:-0}; FAIL=${FAIL:-0}; SKIP=${SKIP:-0}
if [ "$OVERALL" -eq 0 ]; then RESULT=PASS; else RESULT=FAIL; fi

{
  echo "run_id=$RUN_ID"
  echo "started=$START"
  echo "finished=$FINISH"
  echo "env=containerlab / campus-lab / $EXPECTED nodes"
  echo "total=$TOTAL pass=$PASS fail=$FAIL skip=$SKIP"
  if [ -f "$RESULT_DIR/suites.tsv" ]; then
    while IFS="	" read -r suite sp sf ss; do
      [ -n "$suite" ] && echo "suite $suite: pass=$sp fail=$sf skip=$ss"
    done < "$RESULT_DIR/suites.tsv"
  fi
  echo "result=$RESULT"
} > "$RESULT_DIR/summary.txt"

echo
cat "$RESULT_DIR/summary.txt"
echo "results: $RESULT_DIR"
exit "$OVERALL"
