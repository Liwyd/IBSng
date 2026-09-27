#!/usr/bin/env bash
#
# IBSng interactive, idempotent installer.
#
#   Ubuntu 24.04 / Debian (apt)  - first class
#   EL 8/9/10 (dnf)              - best effort
#
# Every step checks current state before acting, so re-running the script
# converges a host instead of failing halfway. Run as root:
#
#   sudo ./install.sh            # interactive
#   sudo ./install.sh --yes      # accept all defaults (CI)
#
set -euo pipefail

UNINSTALL=0
KEEP_DB=0
PURGE_PKGS=0

# BASH_SOURCE is unset when the script is fed via stdin (curl | bash) or
# bash -c "…"; fall back to $0 so set -u doesn't abort the installer.
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
ASSUME_YES=0
ENABLE_OPENVPN=""
ENABLE_FIREWALL=""

info()  { printf '\033[1;32m[ IB ]\033[0m %s\n' "$*"; }
warn()  { printf '\033[1;33m[WARN]\033[0m %s\n' "$*"; }
die()   { printf '\033[1;31m[FAIL]\033[0m %s\n' "$*" >&2; exit 1; }

usage() {
    cat <<'EOF'
usage: install.sh [--yes] [--help] [--uninstall] [--keep-db] [--purge-packages]

  --yes, -y          non-interactive: accept all defaults / confirmations
  --help, -h         show this help

  --uninstall        full purge of this host: stop and remove the engine,
                     systemd unit, cron job, openvpn config, web config,
                     firewall rules, /usr/local/IBSng, /etc/ibsng,
                     /var/log/IBSng, and drop the IBSng database and role
  --keep-db          with --uninstall: keep the IBSng database and role
  --purge-packages   with --uninstall: also purge the web/database packages
                     the installer uses (WARNING: removes apache2/php/
                     postgresql - may break other software on this host)

defaults: prefix /usr/local/IBSng, db password ibsdbpass,
          admin password "system", openvpn off, firewall rules off
EOF
}

for arg in "$@"; do
    case "$arg" in
        -y|--yes) ASSUME_YES=1 ;;
        -h|--help) usage; exit 0 ;;
        -u|--uninstall) UNINSTALL=1 ;;
        --keep-db) KEEP_DB=1 ;;
        --purge-packages) PURGE_PKGS=1 ;;
        *) usage >&2; die "unknown argument: $arg" ;;
    esac
done

[ "$(id -u)" -eq 0 ] || die "please run this script as root (sudo ./install.sh)"

# ---------------------------------------------------------------- distro
if [ -r /etc/os-release ]; then
    . /etc/os-release
else
    die "/etc/os-release not found - unsupported system"
fi
PKG_MGR=""
case "${ID:-}" in
    ubuntu|debian|raspbian) PKG_MGR=apt ;;
    fedora|rhel|centos|rocky|almalinux) PKG_MGR=dnf ;;
    *)
        warn "distro '${ID:-unknown}' not explicitly supported"
        if command -v apt-get >/dev/null 2>&1; then PKG_MGR=apt
        elif command -v dnf >/dev/null 2>&1; then PKG_MGR=dnf
        else die "no supported package manager found"
        fi
        ;;
esac
info "distro: ${PRETTY_NAME:-$ID}, package manager: $PKG_MGR"

# ------------------------------------------------------- environment knobs
# IBS_DB_HOST / IBS_DB_PORT / IBS_DB_PASSWORD configure the database the
# installer bootstraps and the service talks to (containers/CI use these).
# Setting IBS_DB_SUPERUSER[_PASSWORD] forces TCP bootstrap even on 127.0.0.1
# (e.g. a postgres service container published on localhost).
DB_HOST="${IBS_DB_HOST:-127.0.0.1}"
DB_PORT="${IBS_DB_PORT:-5432}"
USE_REMOTE_DB=0
if [ "$DB_HOST" != "127.0.0.1" ] && [ "$DB_HOST" != "localhost" ]; then
    USE_REMOTE_DB=1
elif [ -n "${IBS_DB_SUPERUSER:-}" ] || [ -n "${IBS_DB_SUPERUSER_PASSWORD:-}" ]; then
    USE_REMOTE_DB=1
fi
HAS_SYSTEMD=0
if command -v systemctl >/dev/null 2>&1 && [ -d /run/systemd/system ]; then
    HAS_SYSTEMD=1
fi

# ---------------------------------------------------------------- uninstall
run_uninstall() {
    PREFIX="${PREFIX:-/usr/local/IBSng}"

    info "IBSng full uninstall will remove:"
    info "  - engine process, systemd unit, init.d script, pid file"
    info "  - $PREFIX, /etc/ibsng (env/credentials), /var/log/IBSng"
    info "  - apache/web config, /etc/cron.d/ibsng-openvpn-interim, openvpn config"
    info "  - ufw/firewalld rules for 80/tcp, 1812/udp, 1813/udp, 1194/udp"
    if [ "$KEEP_DB" -eq 1 ]; then
        info "  - database: KEPT (--keep-db)"
    else
        info "  - database: DROP database IBSng and role ibs (IRREVERSIBLE)"
    fi
    if [ "$PURGE_PKGS" -eq 1 ]; then
        info "  - packages: PURGED (apache/php/postgresql - may affect other software!)"
    else
        info "  - packages: kept"
    fi

    if [ "$ASSUME_YES" -ne 1 ]; then
        [ -t 0 ] || die "stdin is not a terminal - re-run with --yes for non-interactive purge"
        local __answer=""
        read -r -p "Proceed with full uninstall? [y/N]: " __answer || true
        case "$__answer" in
            y|Y|yes|Yes) ;;
            *) info "aborted - nothing was changed"; return 1 ;;
        esac
    fi

    # ---- stop the engine
    if [ "$HAS_SYSTEMD" -eq 1 ]; then
        systemctl stop ibsng >/dev/null 2>&1 || true
        systemctl disable ibsng >/dev/null 2>&1 || true
    fi
    service IBSng stop >/dev/null 2>&1 || true
    pkill -f "${PREFIX}/ibs[.]py" >/dev/null 2>&1 || true
    local _w
    for _w in 1 2 3 4 5; do
        pgrep -f "${PREFIX}/ibs[.]py" >/dev/null 2>&1 || break
        sleep 1
    done
    pkill -9 -f "${PREFIX}/ibs[.]py" >/dev/null 2>&1 || true
    rm -f /run/IBSng.pid /run/openvpn/ibsng.status /run/openvpn/ibsng.sock
    info "engine stopped and runtime files removed"

    # ---- unit, cron, init.d, openvpn
    rm -f /etc/systemd/system/ibsng.service
    if [ "$HAS_SYSTEMD" -eq 1 ]; then
        systemctl daemon-reload >/dev/null 2>&1 || true
        systemctl disable --now openvpn-server@ibsng openvpn@ibsng >/dev/null 2>&1 || true
    fi
    rm -f /etc/cron.d/ibsng-openvpn-interim /etc/init.d/IBSng
    rm -f /etc/openvpn/server/ibsng.conf /etc/openvpn/ibsng.conf
    info "service unit, cron job and openvpn config removed"

    # ---- web config + reload
    if [ "$PKG_MGR" = apt ]; then
        command -v a2disconf >/dev/null 2>&1 && a2disconf ibsng >/dev/null 2>&1 || true
        rm -f /etc/apache2/conf-available/ibsng.conf /etc/apache2/conf-enabled/ibsng.conf
    else
        rm -f /etc/httpd/conf.d/ibsng.conf
    fi
    if pgrep -x apache2 >/dev/null 2>&1 || pgrep -x httpd >/dev/null 2>&1; then
        if [ "$PKG_MGR" = apt ]; then
            systemctl reload apache2 >/dev/null 2>&1 ||
                service apache2 reload >/dev/null 2>&1 ||
                apachectl graceful >/dev/null 2>&1 || true
        else
            systemctl reload httpd >/dev/null 2>&1 ||
                service httpd reload >/dev/null 2>&1 || true
        fi
    fi
    info "web config removed"

    # ---- firewall rules the installer may have opened
    if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q ALLOW; then
        local _p
        for _p in 80/tcp 1812/udp 1813/udp 1194/udp; do
            ufw --force delete allow "$_p" >/dev/null 2>&1 || true
            ufw --force delete allow "$_p" >/dev/null 2>&1 || true
        done
        info "ufw rules removed (80/1812/1813/1194)"
    elif command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
        firewall-cmd --permanent --remove-port=80/tcp >/dev/null 2>&1 || true
        firewall-cmd --permanent --remove-port=1812/udp >/dev/null 2>&1 || true
        firewall-cmd --permanent --remove-port=1813/udp >/dev/null 2>&1 || true
        firewall-cmd --permanent --remove-port=1194/udp >/dev/null 2>&1 || true
        firewall-cmd --reload >/dev/null 2>&1 || true
        info "firewalld ports removed (80/1812/1813/1194)"
    fi

    # ---- database (before package purge; local cluster stays up)
    if [ "$KEEP_DB" -eq 1 ]; then
        info "database IBSng and role ibs kept"
    else
        if [ "$USE_REMOTE_DB" -eq 1 ]; then
            local _super=(psql -h "$DB_HOST" -p "$DB_PORT"
                          -U "${IBS_DB_SUPERUSER:-postgres}" -d postgres)
            PGPASSWORD="${IBS_DB_SUPERUSER_PASSWORD:-${IBS_DB_PASSWORD:-}}" \
                "${_super[@]}" -c 'drop database if exists "IBSng"' >/dev/null \
                || warn "could not drop database IBSng on $DB_HOST"
            PGPASSWORD="${IBS_DB_SUPERUSER_PASSWORD:-${IBS_DB_PASSWORD:-}}" \
                "${_super[@]}" -c 'drop role if exists ibs' >/dev/null \
                || warn "could not drop role ibs on $DB_HOST"
        else
            su postgres -c 'psql -c "drop database if exists \"IBSng\""' >/dev/null \
                || warn "could not drop database IBSng"
            su postgres -c 'psql -c "drop role if exists ibs"' >/dev/null \
                || warn "could not drop role ibs"
        fi
        info "database IBSng and role ibs dropped"
    fi

    # ---- program tree, logs, credentials (guarded rm -rf)
    if [ -n "$PREFIX" ] && [ "$PREFIX" != "/" ] && \
       { [ -e "$PREFIX/ibs.py" ] || [ -d "$PREFIX/interface" ]; }; then
        rm -rf "$PREFIX"
        info "removed $PREFIX"
    else
        warn "skipping tree removal: '$PREFIX' does not look like an IBSng install"
    fi
    rm -rf /var/log/IBSng /etc/ibsng
    info "removed /var/log/IBSng and /etc/ibsng"

    # ---- packages (explicit opt-in only; may be shared with other software)
    if [ "$PURGE_PKGS" -eq 1 ]; then
        export DEBIAN_FRONTEND=noninteractive
        if [ "$PKG_MGR" = apt ]; then
            apt-get purge -y rsync apache2 php-cli libapache2-mod-php php-gd \
                php-xml php-mbstring postgresql postgresql-client >/dev/null 2>&1 \
                || warn "some packages could not be purged"
        else
            dnf remove -y rsync httpd php php-gd php-xml php-mbstring \
                postgresql-server postgresql >/dev/null 2>&1 \
                || warn "some packages could not be purged"
        fi
        info "packages purged (python3, git, curl and openvpn were left alone)"
    fi

    info "uninstall complete"
    if [ "$KEEP_DB" -eq 1 ]; then
        info "remember: database IBSng still exists - drop it manually if unwanted"
    fi
}

if [ "$UNINSTALL" -eq 1 ]; then
    run_uninstall
    exit $?
fi

# ---------------------------------------------------------------- prompts
prompt() { # prompt VAR "question" "default"
    local __var="$1" __q="$2" __default="$3" __answer=""
    if [ "$ASSUME_YES" -eq 1 ]; then
        __answer="$__default"
    else
        read -r -p "$__q [$__default]: " __answer || true
        [ -n "$__answer" ] || __answer="$__default"
    fi
    printf -v "$__var" '%s' "$__answer"
}

prompt_secret() { # prompt_secret VAR "question" "default"
    local __var="$1" __q="$2" __default="$3" __answer=""
    if [ "$ASSUME_YES" -eq 1 ]; then
        __answer="$__default"
    else
        read -r -s -p "$__q [$__default]: " __answer || true
        echo
        [ -n "$__answer" ] || __answer="$__default"
    fi
    printf -v "$__var" '%s' "$__answer"
}

prompt PREFIX     "Install prefix"                 "/usr/local/IBSng"
prompt DB_PASS    "PostgreSQL password for role ibs" "${IBS_DB_PASSWORD:-ibsdbpass}"
prompt_secret ADMIN_PASS "Web admin password for user 'system'" "system"
case "$DB_PASS" in
    *"'"*|*"\\"*) die "database password must not contain single quotes or backslashes" ;;
esac

if [ "$ASSUME_YES" -eq 0 ]; then
    prompt ENABLE_OPENVPN "Install and wire OpenVPN accounting? (y/n)" "n"
    prompt ENABLE_FIREWALL "Open firewall ports 80/tcp, 1812/udp, 1813/udp? (y/n)" "n"
fi
ENABLE_OPENVPN="${ENABLE_OPENVPN:-n}"
ENABLE_FIREWALL="${ENABLE_FIREWALL:-n}"

# ---------------------------------------------------------------- packages
python3 -c 'import pg' >/dev/null 2>&1 && HAVE_PG_PY=1 || HAVE_PG_PY=0

install_packages_apt() {
    local wanted=("$@") missing=()
    export DEBIAN_FRONTEND=noninteractive
    local pkg
    for pkg in "${wanted[@]}"; do
        dpkg -s "$pkg" >/dev/null 2>&1 || missing+=("$pkg")
    done
    if [ "${#missing[@]}" -gt 0 ]; then
        info "installing packages: ${missing[*]}"
        apt-get update -qq
        apt-get install -y -qq "${missing[@]}"
    else
        info "all required packages already installed"
    fi
}

install_packages_dnf() {
    local wanted=("$@") missing=()
    local pkg
    for pkg in "${wanted[@]}"; do
        rpm -q "$pkg" >/dev/null 2>&1 || missing+=("$pkg")
    done
    if [ "${#missing[@]}" -gt 0 ]; then
        info "installing packages: ${missing[*]} (best effort on EL)"
        dnf install -y "${missing[@]}" || warn "some packages failed - check output"
    else
        info "all required packages already installed"
    fi
}

if [ "$PKG_MGR" = apt ]; then
    PACKAGES=(rsync curl ca-certificates
              apache2 php-cli libapache2-mod-php php-gd php-xml php-mbstring)
    if [ "$USE_REMOTE_DB" -eq 1 ]; then PACKAGES+=(postgresql-client)
    else PACKAGES+=(postgresql); fi
    if [ "$ENABLE_OPENVPN" = y ]; then PACKAGES+=(openvpn); fi
    install_packages_apt "${PACKAGES[@]}"
    # PyGreSQL: distro package first, pip fallback (Ubuntu is PEP 668 managed)
    if [ "$HAVE_PG_PY" -eq 0 ]; then
        install_packages_apt python3-pygresql || true
        if ! python3 -c 'import pg' >/dev/null 2>&1; then
            info "installing PyGreSQL via pip"
            install_packages_apt python3-pip python3-dev libpq-dev build-essential
            pip3 install --quiet --break-system-packages PyGreSQL
        fi
    fi
else
    PACKAGES=(rsync curl git httpd php php-gd php-xml php-mbstring python3)
    if [ "$USE_REMOTE_DB" -eq 1 ]; then PACKAGES+=(postgresql)
    else PACKAGES+=(postgresql-server); fi
    if [ "$ENABLE_OPENVPN" = y ]; then PACKAGES+=(openvpn); fi
    install_packages_dnf "${PACKAGES[@]}"
    if [ "$HAVE_PG_PY" -eq 0 ]; then
        install_packages_dnf python3-pygresql || true
        if ! python3 -c 'import pg' >/dev/null 2>&1; then
            warn "PyGreSQL not available from dnf - trying pip"
            dnf install -y python3-pip libpq-devel gcc python3-devel || true
            pip3 install --quiet PyGreSQL || die "cannot install PyGreSQL"
        fi
    fi
fi
python3 -c 'import pg' >/dev/null 2>&1 || die "PyGreSQL (import pg) unavailable"

# ---------------------------------------------------------------- source tree
# (resolved after package bootstrap: the clone fallback needs git, which a
# fresh minimal distro does not ship)
if [ -f "$SRC_DIR/ibs.py" ]; then
    SOURCE="$SRC_DIR"
else
    info "no local source tree next to install.sh - cloning repository"
    if ! command -v git >/dev/null 2>&1; then
        info "git missing - installing it first"
        if [ "$PKG_MGR" = apt ]; then install_packages_apt git
        else install_packages_dnf git
        fi
    fi
    TMP_CLONE="$(mktemp -d /tmp/ibsng-src.XXXXXX)"
    # mktemp creates the dir 0700; rsync -a would propagate that to
    # $PREFIX and the web server could no longer traverse the tree (403)
    chmod 755 "$TMP_CLONE"
    git clone --depth 1 https://github.com/Liwyd/IBSng.git "$TMP_CLONE"
    SOURCE="$TMP_CLONE"
fi

# ---------------------------------------------------------------- postgres
psql_as_postgres() {
    if [ "$USE_REMOTE_DB" -eq 1 ]; then
        PGPASSWORD="${IBS_DB_SUPERUSER_PASSWORD:-${DB_PASS:-}}" \
        psql -h "$DB_HOST" -p "$DB_PORT" -U "${IBS_DB_SUPERUSER:-postgres}" \
             -d postgres -v ON_ERROR_STOP=1 -qtAc "$1"
        return
    fi
    if command -v runuser >/dev/null 2>&1; then
        runuser -u postgres -- psql -v ON_ERROR_STOP=1 -qtAc "$1"
    else
        su -s /bin/sh postgres -c "psql -v ON_ERROR_STOP=1 -qtAc \"$1\""
    fi
}

setup_postgres() {
    if [ "$USE_REMOTE_DB" -eq 1 ]; then
        info "using external postgres at $DB_HOST:$DB_PORT (no local cluster)"
    elif [ "$PKG_MGR" = apt ]; then
        systemctl enable --now postgresql >/dev/null 2>&1 || true
    else
        if [ ! -d /var/lib/pgsql/data/base ]; then
            postgresql-setup --initdb >/dev/null 2>&1 || \
                warn "postgresql-setup initdb failed - assuming cluster exists"
        fi
        systemctl enable --now postgresql >/dev/null 2>&1 || \
            systemctl enable --now postgresql-* >/dev/null 2>&1 || true
        # best effort: password auth on loopback (EL defaults to ident)
        local hba
        for hba in /var/lib/pgsql/data/pg_hba.conf /var/lib/pgsql/*/data/pg_hba.conf; do
            [ -f "$hba" ] || continue
            if grep -qE '^host.*127\.0\.0\.1/32.*(ident|peer)' "$hba"; then
                sed -i -E 's/^(host.*127\.0\.0\.1\/32.*(ident|peer))/\1 scram-sha-256 #/' "$hba"
                systemctl restart postgresql >/dev/null 2>&1 || true
            fi
        done
    fi

    if [ "$USE_REMOTE_DB" -eq 0 ]; then
        # containers / hosts without systemd never start the local cluster
        # via the package postinst - bring it up ourselves, then verify
        local _pg_try
        for _pg_try in 1 2 3 4 5; do
            psql_as_postgres "select 1" >/dev/null 2>&1 && break
            service postgresql start >/dev/null 2>&1 || true
            sleep 2
        done
        psql_as_postgres "select 1" >/dev/null 2>&1 || \
            die "local PostgreSQL is not running - check 'service postgresql status'"
    fi

    if [ "$(psql_as_postgres "select 1 from pg_roles where rolname='ibs'")" != "1" ]; then
        info "creating postgres role ibs"
        psql_as_postgres "create role ibs with login createdb password '$DB_PASS'" >/dev/null
    else
        psql_as_postgres "alter role ibs with login password '$DB_PASS'" >/dev/null
    fi

    if [ "$(psql_as_postgres "select 1 from pg_database where datname='IBSng'")" != "1" ]; then
        info "creating database IBSng"
        psql_as_postgres "createdb -O ibs IBSng" >/dev/null 2>&1 || \
            psql_as_postgres "create database \"IBSng\" owner ibs" >/dev/null
    fi
}

sql_ib() { # run SQL as role ibs over TCP
    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U ibs -d IBSng \
        -v ON_ERROR_STOP=1 -qtAc "$1"
}

load_schema() {
    if [ "$(sql_ib "select to_regclass('public.users')")" = "users" ]; then
        info "database schema already present - skipping load"
        return
    fi
    info "loading database schema"
    local f
    for f in tables.sql functions.sql initial.sql defs.sql; do
        PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U ibs -d IBSng \
            -v ON_ERROR_STOP=1 -q -f "$SOURCE/db/$f"
    done
}

set_admin_password() {
    info "setting admin password for 'system'"
    local md5
    md5="$(IBS_ADMIN_PASSWORD="$ADMIN_PASS" python3 - "$PREFIX" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import os
from core.lib import password_lib
print(password_lib.Password(os.environ["IBS_ADMIN_PASSWORD"]).getMd5Crypt())
PY
)" || die "could not generate admin password hash"
    sql_ib "update admins set password='$md5' where username='system'" >/dev/null
}

# ---------------------------------------------------------------- files/services
copy_tree() {
    info "syncing source tree to $PREFIX"
    mkdir -p "$PREFIX"
    rsync -a --delete \
        --exclude '.git' --exclude '.pytest_cache' --exclude '__pycache__' \
        --exclude '.pytest_cache' \
        "$SOURCE/" "$PREFIX/"
    # normalize modes regardless of the source tree's umask/clone perms:
    # dirs and executables get x (X), everything else 644; the web server
    # must be able to traverse every path under $PREFIX
    chmod -R u=rwX,go=rX "$PREFIX"
    chmod 755 "$PREFIX/ibs.py" "$PREFIX/backup_ibs" "$PREFIX/restore_ibs" \
        "$PREFIX/addons/openvpn/openvpn_agent.py"
}

write_env_file() {
    install -d -m 755 /etc/ibsng
    cat > /etc/ibsng/ibsng.env <<EOF
IBS_DB_HOST=$DB_HOST
IBS_DB_PORT=$DB_PORT
IBS_DB_USERNAME=ibs
IBS_DB_PASSWORD=$DB_PASS
EOF
    chmod 600 /etc/ibsng/ibsng.env
    info "wrote /etc/ibsng/ibsng.env (mode 600)"
}

setup_web() {
    local web_user conf_dir
    if [ "$PKG_MGR" = apt ]; then
        web_user=www-data
        conf_dir=/etc/apache2/conf-available
        install -m 644 "$PREFIX/addons/apache/ibs.conf" "$conf_dir/ibsng.conf"
        a2enmod -q alias expires deflate >/dev/null 2>&1 || true
        a2enconf -q ibsng >/dev/null 2>&1 || true
    else
        web_user=apache
        conf_dir=/etc/httpd/conf.d
        install -m 644 "$PREFIX/addons/apache/ibs.conf" "$conf_dir/ibsng.conf"
    fi
    # apache's default <Directory /> rule denies everything outside the
    # web root - grant the interface tree explicitly (idempotent rewrite)
    cat >> "$conf_dir/ibsng.conf" <<EOF

<Directory "$PREFIX/interface/IBSng">
    Options -Indexes +FollowSymLinks
    AllowOverride None
    Require all granted
</Directory>
EOF
    install -d -m 775 -o root -g "$web_user" /var/log/IBSng
    chown -R "$web_user:" "$PREFIX/interface/smarty/templates_c"
    chmod -R ug+rw "$PREFIX/interface/smarty/templates_c"
    if [ "$HAS_SYSTEMD" -eq 1 ]; then
        systemctl enable apache2 >/dev/null 2>&1 || \
            systemctl enable httpd >/dev/null 2>&1 || \
            warn "could not enable web server service"
        systemctl reload-or-restart apache2 >/dev/null 2>&1 || \
            systemctl reload-or-restart httpd >/dev/null 2>&1 || \
            warn "could not (re)load web server"
        # reload can succeed and the daemon still die a moment later
        # (stale master after a package reinstall) - verify it stays up
        local _web_svc=apache2
        systemctl cat apache2 >/dev/null 2>&1 || _web_svc=httpd
        sleep 1
        if ! systemctl is-active --quiet "$_web_svc"; then
            systemctl start "$_web_svc" >/dev/null 2>&1 || true
            sleep 1
        fi
        systemctl is-active --quiet "$_web_svc" || \
            warn "web server is not running - check: journalctl -u $_web_svc"
    else
        apachectl -t >/dev/null 2>&1 || warn "apache configuration test failed"
        info "no systemd - web server config validated; start apache from your init"
    fi
}

setup_service() {
    if [ "$HAS_SYSTEMD" -eq 0 ]; then
        info "no systemd - skipping ibsng.service (start $PREFIX/ibs.py from your init)"
        return 0
    fi
    info "installing systemd unit ibsng.service"
    cat > /etc/systemd/system/ibsng.service <<EOF
[Unit]
Description=IBSng RADIUS server
After=network-online.target postgresql.service
Wants=network-online.target

[Service]
Type=forking
EnvironmentFile=-/etc/ibsng/ibsng.env
ExecStart=$PREFIX/ibs.py
PIDFile=/run/IBSng.pid
Restart=on-failure
RestartSec=5
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable ibsng >/dev/null 2>&1 || true
    systemctl restart ibsng
    local i
    for i in $(seq 1 30); do
        if awk '$2 ~ /:0714$/ {found=1} END {exit !found}' /proc/net/udp 2>/dev/null; then
            info "IBSng is up (RADIUS listening on UDP/1812)"
            return 0
        fi
        sleep 1
    done
    warn "IBSng did not bind UDP/1812 within 30s - check: journalctl -u ibsng"
}

setup_firewall() {
    [ "$ENABLE_FIREWALL" = y ] || { info "firewall rules skipped"; return; }
    if command -v ufw >/dev/null 2>&1; then
        ufw allow 80/tcp >/dev/null 2>&1 || true
        ufw allow 1812/udp >/dev/null 2>&1 || true
        ufw allow 1813/udp >/dev/null 2>&1 || true
        [ "$ENABLE_OPENVPN" = y ] && ufw allow 1194/udp >/dev/null 2>&1 || true
        info "ufw rules added (enable ufw yourself if it is inactive)"
    elif command -v firewall-cmd >/dev/null 2>&1; then
        firewall-cmd --permanent --add-port=80/tcp >/dev/null 2>&1 || true
        firewall-cmd --permanent --add-port=1812/udp >/dev/null 2>&1 || true
        firewall-cmd --permanent --add-port=1813/udp >/dev/null 2>&1 || true
        [ "$ENABLE_OPENVPN" = y ] && firewall-cmd --permanent --add-port=1194/udp >/dev/null 2>&1 || true
        firewall-cmd --reload >/dev/null 2>&1 || true
        info "firewalld rules added"
    else
        warn "no ufw/firewalld found - open ports 80/tcp, 1812/udp, 1813/udp manually"
    fi
}

# ---------------------------------------------------------------- openvpn
setup_openvpn() {
    [ "$ENABLE_OPENVPN" = y ] || { info "OpenVPN wiring skipped"; return; }

    local secret existing
    existing="$(sql_ib "select radius_secret from ras where ras_type='openvpn' limit 1")"
    if [ -n "$existing" ]; then
        secret="$existing"
        info "openvpn RAS already exists - reusing its radius secret"
    else
        if [ -n "$(sql_ib "select ras_ip from ras where ras_ip='127.0.0.1' limit 1")" ]; then
            die "RAS with IP 127.0.0.1 already exists and is not type openvpn - resolve in admin UI first"
        fi
        secret="$(openssl rand -hex 16 2>/dev/null || head -c16 /dev/urandom | od -An -tx1 | tr -d ' \n')"
        info "creating RAS 'openvpn-local' (127.0.0.1)"
        sql_ib "insert into ras (ras_id, ras_description, ras_ip, ras_type, radius_secret)
                values ((select coalesce(max(ras_id),0)+1 from ras),
                        'openvpn-local', '127.0.0.1', 'openvpn', '$secret')" >/dev/null
    fi

    install -d -m 700 /etc/ibsng
    cat > /etc/ibsng/openvpn_agent.env <<EOF
IBSNG_RADIUS_SECRET=$secret
IBSNG_RADIUS_HOST=127.0.0.1
IBSNG_AUTH_DIR=/run/openvpn/ibsng-auth
EOF
    chmod 600 /etc/ibsng/openvpn_agent.env

    install -d -m 755 /etc/openvpn/server
    cat > /etc/openvpn/server/ibsng.conf <<EOF
# generated by IBSng installer - RADIUS NAS accounting into IBSng
port 1194
proto udp
dev tun
topology subnet
server 10.8.0.0 255.255.255.0
persist-key
persist-tun

script-security 2
auth-user-pass-verify $PREFIX/addons/openvpn/openvpn_agent.py auth via-file
client-connect $PREFIX/addons/openvpn/openvpn_agent.py start
client-disconnect $PREFIX/addons/openvpn/openvpn_agent.py stop

status /run/openvpn/ibsng.status 30
status-version 2
management /run/openvpn/ibsng.sock unix
EOF

    cat > /etc/cron.d/ibsng-openvpn-interim <<EOF
# interim RADIUS accounting updates for OpenVPN sessions
* * * * * root $PREFIX/addons/openvpn/openvpn_agent.py interim --status-file /run/openvpn/ibsng.status >> /var/log/IBSng/openvpn_interim.log 2>&1
EOF
    chmod 644 /etc/cron.d/ibsng-openvpn-interim

    if [ "$HAS_SYSTEMD" -eq 1 ]; then
        systemctl enable --now openvpn-server@ibsng >/dev/null 2>&1 || \
            systemctl enable --now openvpn@ibsng >/dev/null 2>&1 || \
            warn "could not start openvpn-server@ibsng - check /etc/openvpn/server/ibsng.conf"
    else
        info "no systemd - openvpn config written but not started"
    fi
    info "OpenVPN accounting wired (server config + interim cron)"
}

# ---------------------------------------------------------------- run
info "IBSng installer starting (prefix: $PREFIX)"
setup_postgres
load_schema
copy_tree
set_admin_password
write_env_file
setup_web
setup_service
setup_openvpn
setup_firewall

# display only - tolerate missing iproute2 / no route (minimal containers)
LOCAL_IP="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1); exit}')" || LOCAL_IP=""
LOCAL_IP="${LOCAL_IP:-127.0.0.1}"
if [ "$HAS_SYSTEMD" -eq 1 ]; then
    SERVICE_HINT="systemctl {start|stop|status|restart} ibsng"
    LOG_HINT="journalctl -u ibsng  and  /var/log/IBSng/"
else
    SERVICE_HINT="start $PREFIX/ibs.py from your init (the docker entrypoint does this)"
    LOG_HINT="/var/log/IBSng/"
fi

cat <<EOF

IBSng installation finished.

  Admin panel:   http://$LOCAL_IP/IBSng/admin
  Admin login:   system / (the password you chose)
  RADIUS:        UDP 1812 (auth), UDP 1813 (accounting)
  Service:       $SERVICE_HINT
  Logs:          $LOG_HINT

Security checklist:
  * change the admin password immediately if you kept the default
  * XML-RPC (127.0.0.1:1235) and the database must stay local-only
  * re-run this script any time - it converges instead of failing
EOF
