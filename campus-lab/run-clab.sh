#!/bin/sh
# Run containerlab inside the official container without requiring a TTY.
# Must be executed from the directory containing campus-lab.clab.yml.
exec docker run --rm --privileged --network host \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /var/run/netns:/var/run/netns \
  -v /etc/hosts:/etc/hosts \
  -v /var/lib/docker/containers:/var/lib/docker/containers \
  --pid=host \
  -v "$PWD":"$PWD" -w "$PWD" \
  ghcr.io/srl-labs/clab containerlab "$@"
