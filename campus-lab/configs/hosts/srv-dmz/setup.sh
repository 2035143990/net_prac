#!/bin/sh
set -e
n=0; while [ ! -e /sys/class/net/eth1 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
n=0; while [ ! -e /sys/class/net/eth2 ] && [ $n -lt 60 ]; do sleep 0.5; n=$((n+1)); done
ip link set eth1 up
ip addr replace 10.80.0.10/24 dev eth1
ip route replace default via 10.80.0.1
mkdir -p /www
echo 'DMZ server OK' > /www/index.html
cat > /www/serve80.sh <<'EOF'
while true; do
  printf 'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 13\r\nConnection: close\r\n\r\nDMZ server OK' | nc -l -p 80 -w 2
done
EOF
cat > /www/serve443.sh <<'EOF'
while true; do
  printf 'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 13\r\nConnection: close\r\n\r\nDMZ server OK' | nc -l -p 443 -w 2
done
EOF
sh /www/serve80.sh >/var/log/dmz-http.log 2>&1 &
sh /www/serve443.sh >/var/log/dmz-https.log 2>&1 &
exit 0
