#!/bin/sh
# Build all local images required by campus-lab.clab.yml.
# Run from anywhere; paths are resolved relative to this script.
set -e
cd "$(dirname "$0")"

BASE_IMAGE=alpine:3.24
if [ "${FORCE_PULL:-0}" != "1" ] && docker image inspect "$BASE_IMAGE" >/dev/null 2>&1; then
  echo "==> base image $BASE_IMAGE already exists locally, skipping pull"
  echo '    (use FORCE_PULL=1 sh build-images.sh to force a pull)'
else
  echo "==> pulling pinned base image $BASE_IMAGE"
  docker pull "$BASE_IMAGE"
fi

echo '==> campus-frr:latest'
docker build -t campus-frr:latest images/frr

echo '==> campus-l2:latest'
docker build -t campus-l2:latest images/l2

echo '==> campus-fw:latest'
docker build -t campus-fw:latest images/fw

echo '==> campus-host:latest'
docker build -t campus-host:latest images/host

echo '==> checking dnsmasq DHCP relay support (>= 2.86)'
ver=$(docker run --rm campus-frr:latest dnsmasq --version 2>/dev/null | sed -n '1s/.*version //p')
case "$ver" in
  2.8[6-9]*|2.9*|3.*) echo "    dnsmasq $ver OK" ;;
  *) echo "    dnsmasq version '$ver' is too old for dhcp-relay" >&2; exit 1 ;;
esac

echo
echo '==> local images'
docker image ls --filter reference='campus-*' --format '{{.Repository}}:{{.Tag}} {{.Size}}'