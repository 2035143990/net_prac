FROM alpine:3.24
RUN echo "https://mirrors.aliyun.com/alpine/v3.24/main" > /etc/apk/repositories \
 && echo "https://mirrors.aliyun.com/alpine/v3.24/community" >> /etc/apk/repositories \
 && apk add --no-cache iproute2 dnsmasq \
 && mkdir -p /var/log /www
COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh
ENTRYPOINT ["/usr/local/bin/start.sh"]
