#!/bin/sh
# Shared assertion/result library for campus-lab test suites (POSIX sh).
# Each suite sources this file, calls suite_begin/case_begin/assert_*/case_end,
# then "suite_end; exit $?".

P=${P:-clab-campus-lab-}
RUN_ID=${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}
RESULT_DIR=${RESULT_DIR:-tests/results/$RUN_ID}
RAW_DIR=$RESULT_DIR/raw
JSONL=$RESULT_DIR/results.jsonl
SUITE_FILE=$RESULT_DIR/suites.tsv
mkdir -p "$RAW_DIR" 2>/dev/null || true

SUITE_PREFIX=""
SUITE_PASS=0
SUITE_FAIL=0
SUITE_SKIP=0

CASE_ID=""
CASE_CAP=""
CASE_DESC=""
CASE_STATUS=""
CASE_EXPECTED=""
CASE_ACTUAL=""
CASE_CMD=""
CASE_NODE=""
CASE_START_MS=0
CASE_END_MS=0

now_ms() {
  python3 -c 'import time; print(int(time.time()*1000))' 2>/dev/null || date +%s000
}

json_escape() {
  printf '%s' "$1" | awk 'BEGIN { ORS="" } {
    gsub(/\\/, "\\\\"); gsub(/"/, "\\\"");
    if (NR > 1) printf "\\n";
    printf "%s", $0
  }'
}

cap_enabled() {
  python3 - "$1" <<'PY' 2>/dev/null
import json, sys
try:
    data = json.load(open("configs/facts.json"))
except Exception:
    print("unknown")
    raise SystemExit(0)
print("true" if data.get("capabilities", {}).get(sys.argv[1]) else "false")
PY
}

require_cap() {
  if [ "$(cap_enabled "$1")" = "true" ]; then
    return 0
  fi
  echo "SKIP suite $SUITE_PREFIX: capability '$1' not declared in facts.json"
  return 1
}

suite_begin() {
  SUITE_PREFIX=$1
  SUITE_PASS=0
  SUITE_FAIL=0
  SUITE_SKIP=0
  echo "== SUITE $SUITE_PREFIX =="
}

case_begin() {
  CASE_ID=$1
  CASE_CAP=$2
  CASE_DESC=$3
  CASE_STATUS="PASS"
  CASE_EXPECTED=""
  CASE_ACTUAL=""
  CASE_CMD=""
  CASE_NODE=""
  CASE_START_MS=$(now_ms)
}

case_ok() {
  [ "$CASE_STATUS" = "FAIL" ] || CASE_STATUS="PASS"
}

case_fail() {
  CASE_STATUS="FAIL"
}

run_cmd() {
  CASE_NODE=$1
  CASE_CMD=$2
  OUT=$(docker exec "${P}${CASE_NODE}" sh -c "$CASE_CMD" 2>&1)
  RC=$?
  printf '%s\n' "$OUT" >> "$RAW_DIR/${CASE_ID}.log" 2>/dev/null || true
}

assert_eq() {
  CASE_EXPECTED=$1
  CASE_ACTUAL=$2
  if [ "$1" = "$2" ]; then
    case_ok
  else
    case_fail
  fi
}

assert_contains() {
  CASE_EXPECTED="contains: $1"
  CASE_ACTUAL=$2
  case "$2" in
    *"$1"*) case_ok ;;
    *) case_fail ;;
  esac
}

assert_not_contains() {
  CASE_EXPECTED="not contains: $1"
  CASE_ACTUAL=$2
  case "$2" in
    *"$1"*) case_fail ;;
    *) case_ok ;;
  esac
}

assert_reachable() {
  CASE_NODE=$1
  CASE_CMD="ping -c2 -W2 $2"
  CASE_EXPECTED="reachable $2"
  OUT=$(docker exec "${P}${CASE_NODE}" ping -c2 -W2 "$2" 2>&1)
  RC=$?
  printf '%s\n' "$OUT" >> "$RAW_DIR/${CASE_ID}.log" 2>/dev/null || true
  CASE_ACTUAL="rc=$RC"
  if [ "$RC" -eq 0 ]; then
    case_ok
  else
    case_fail
  fi
}

assert_unreachable() {
  CASE_NODE=$1
  CASE_CMD="ping -c2 -W2 $2"
  CASE_EXPECTED="unreachable $2"
  OUT=$(docker exec "${P}${CASE_NODE}" ping -c2 -W2 "$2" 2>&1)
  RC=$?
  printf '%s\n' "$OUT" >> "$RAW_DIR/${CASE_ID}.log" 2>/dev/null || true
  CASE_ACTUAL="rc=$RC"
  if [ "$RC" -eq 0 ]; then
    case_fail
  else
    case_ok
  fi
}

assert_http_contains() {
  CASE_NODE=$1
  CASE_CMD="wget -T3 -qO- $2"
  CASE_EXPECTED="HTTP $2 contains: $3"
  OUT=$(docker exec "${P}${CASE_NODE}" sh -c "wget -T3 -qO- '$2'" 2>&1)
  RC=$?
  printf '%s\n' "$OUT" >> "$RAW_DIR/${CASE_ID}.log" 2>/dev/null || true
  CASE_ACTUAL="rc=$RC body=$(printf '%s' "$OUT" | tr '\n' ' ')"
  case "$OUT" in
    *"$3"*) [ "$RC" -eq 0 ] && case_ok || case_fail ;;
    *) case_fail ;;
  esac
}

assert_counter_positive() {
  node=$1
  table=$2
  comment=$3
  CASE_NODE=$node
  CASE_CMD="nft list table $table | grep '$comment'"
  CASE_EXPECTED="counter $comment > 0"
  OUT=$(docker exec "${P}${node}" nft list table "$table" 2>&1 | grep "$comment")
  printf '%s\n' "$OUT" >> "$RAW_DIR/${CASE_ID}.log" 2>/dev/null || true
  CASE_ACTUAL=$OUT
  if printf '%s' "$OUT" | grep -Eq 'packets [1-9][0-9]*'; then
    case_ok
  else
    case_fail
  fi
}

# DNS 解析断言。
#
# 注意：不能用 ping 代替 DNS 校验。设计方案 6.6 的访问控制矩阵把宿舍区
# 定为隔离区域，只放行「宿舍互访、DNS(53)、Internet、DMZ 发布服务」，
# 因此 ping 数据中心的 DNS 服务器会被 iso.dorm2dc 规则丢弃（ISO-04 正是
# 断言这一点）。要验证 DNS 可用，必须真的发起一次域名解析。
assert_dns_resolves() {
  CASE_NODE=$1
  CASE_CMD="nslookup $2 $3"
  CASE_EXPECTED="resolve $2 via $3 -> $4"
  OUT=$(docker exec "${P}${CASE_NODE}" nslookup "$2" "$3" 2>&1)
  RC=$?
  printf '%s\n' "$OUT" >> "$RAW_DIR/${CASE_ID}.log" 2>/dev/null || true
  CASE_ACTUAL="rc=$RC out=$(printf '%s' "$OUT" | tr '\n' ' ')"
  # busybox nslookup 的成功输出形如 "Address: 10.80.0.10"。
  if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -qE "Address: +$4([^0-9.]|$)"; then
    case_ok
  else
    case_fail
  fi
}

skip_case() {
  CASE_STATUS="SKIP"
  CASE_EXPECTED=$1
  CASE_ACTUAL="skipped"
}

case_end() {
  CASE_END_MS=$(now_ms)
  ms=$((CASE_END_MS - CASE_START_MS))
  case "$CASE_STATUS" in
    PASS)
      SUITE_PASS=$((SUITE_PASS + 1))
      printf 'PASS  %-9s %s\n' "$CASE_ID" "$CASE_DESC"
      ;;
    FAIL)
      SUITE_FAIL=$((SUITE_FAIL + 1))
      printf 'FAIL  %-9s %s (expected=%s actual=%s)\n' "$CASE_ID" "$CASE_DESC" "$CASE_EXPECTED" "$CASE_ACTUAL"
      ;;
    *)
      SUITE_SKIP=$((SUITE_SKIP + 1))
      printf 'SKIP  %-9s %s (%s)\n' "$CASE_ID" "$CASE_DESC" "$CASE_EXPECTED"
      ;;
  esac
  printf '{"run_id":"%s","id":"%s","suite":"%s","capability":"%s","status":"%s","desc":"%s","expected":"%s","actual":"%s","cmd":"%s","node":"%s","ms":%s,"evidence":"raw/%s.log"}\n' \
    "$RUN_ID" "$CASE_ID" "$SUITE_PREFIX" "$CASE_CAP" "$CASE_STATUS" \
    "$(json_escape "$CASE_DESC")" "$(json_escape "$CASE_EXPECTED")" \
    "$(json_escape "$CASE_ACTUAL")" "$(json_escape "$CASE_CMD")" "$CASE_NODE" \
    "$ms" "$CASE_ID" >> "$JSONL"
}

suite_end() {
  if [ -n "$SUITE_PREFIX" ]; then
    printf '%s\t%s\t%s\t%s\n' "$SUITE_PREFIX" "$SUITE_PASS" "$SUITE_FAIL" "$SUITE_SKIP" >> "$SUITE_FILE"
    printf 'SUITE %-10s pass=%s fail=%s skip=%s\n' "$SUITE_PREFIX" "$SUITE_PASS" "$SUITE_FAIL" "$SUITE_SKIP"
  fi
  [ "$SUITE_FAIL" -eq 0 ] && return 0
  return 1
}

wait_for() {
  node=$1
  limit=$2
  shift 2
  i=0
  while [ "$i" -lt "$limit" ]; do
    if docker exec "${P}${node}" sh -c "$*" >/dev/null 2>&1; then
      return 0
    fi
    i=$((i + 1))
    sleep 1
  done
  return 1
}