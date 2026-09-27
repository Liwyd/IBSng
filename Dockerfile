# IBSng application container (app + external DB, see docker-compose.yml).
#
# The image ships the code and all runtime packages; the actual installation
# (schema load, admin password, apache config) happens idempotently on first
# container start via docker/entrypoint.sh, using IBS_DB_* environment
# variables supplied by docker-compose.yml.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Keep package postinst scripts from trying to start daemons at build time.
RUN set -eux; \
    printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d; \
    chmod +x /usr/sbin/policy-rc.d; \
    apt-get update -qq; \
    apt-get install -y -qq --no-install-recommends \
        rsync curl ca-certificates iproute2 \
        apache2 php-cli libapache2-mod-php php-gd php-xml php-mbstring \
        python3 python3-pygresql postgresql-client; \
    python3 -c 'import pg' 2>/dev/null || { \
        apt-get install -y -qq --no-install-recommends \
            python3-pip python3-dev libpq-dev build-essential && \
        pip3 install --quiet --break-system-packages PyGreSQL; }; \
    rm -rf /var/lib/apt/lists/*; \
    rm -f /usr/sbin/policy-rc.d

COPY . /opt/ibsng
RUN chmod +x /opt/ibsng/install.sh /opt/ibsng/docker/entrypoint.sh

EXPOSE 80 1812/udp 1813/udp

HEALTHCHECK --interval=15s --timeout=5s --start-period=300s --retries=4 \
    CMD curl -sf -o /dev/null http://127.0.0.1/IBSng/admin/ || exit 1

ENTRYPOINT ["/opt/ibsng/docker/entrypoint.sh"]
