# IBSNG Radius Server

## Overview

**IBSNG** is a RADIUS server with a web admin panel, plan/quota accounting,
and NAS integrations (including OpenVPN accounting via the bundled RADIUS
NAS adapter). The codebase has been ported to Python 3 and PHP 8.3 and is
supported on:

- **Ubuntu 24.04 / Debian** (first class)
- **EL 8/9/10** (best effort)
- **Docker** (application + PostgreSQL, see below)

## Install on a host

One-liner (interactive prompts; requires `curl`):

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/Liwyd/IBSng/main/install.sh)"
```

Fully non-interactive — accept all defaults (admin/system):

```bash
curl -fsSL https://raw.githubusercontent.com/Liwyd/IBSng/main/install.sh | sudo bash -s -- --yes
```

Note: `sudo bash <(curl …)` does **not** work — sudo closes file descriptors ≥ 3
before running the command, so bash cannot open `/dev/fd/63`. When there is no
local clone the installer clones the repository itself (it installs `git` first
if needed).

or from a clone:

```bash
git clone https://github.com/Liwyd/IBSng.git
cd IBSng
sudo ./install.sh          # interactive, idempotent
# or
sudo ./install.sh --yes    # accept defaults (admin/system on system/system)
```

The installer is safe to re-run: it converges the host instead of failing
halfway. It installs packages, bootstraps PostgreSQL (or uses an external
database via `IBS_DB_*` environment variables), loads the schema, configures
Apache, installs the `ibsng.service` systemd unit, and can optionally wire
OpenVPN accounting.

After installation open `http://server-ip/IBSng/admin`:

- **Username:** `system`
- **Password:** the one you chose (`system` with `--yes`)

**Security checklist:** change the default admin password, and keep the
XML-RPC endpoint (127.0.0.1:1235) and the database local-only.

## Docker (app + database)

```bash
docker compose up -d --build
# open http://localhost/IBSng/admin   (login: system / system)
```

First start runs the installer inside the container (~1-2 minutes); later
starts skip setup. Ports: `80/tcp` (admin), `1812/udp` (RADIUS auth),
`1813/udp` (RADIUS accounting). Data lives in the `dbdata` volume.

## Development & tests

```bash
python3 -m pytest tests/ -q
```

Tests expect a PostgreSQL with the IBSng schema; point them at one with
`IBSNG_TEST_DB_HOST`, `IBSNG_TEST_DB_PORT`, `IBSNG_TEST_DB_USER`,
`IBSNG_TEST_DB_PASSWORD`, `IBSNG_TEST_DB_NAME`. CI
(`.github/workflows/ci.yml`) runs the suite, a PHP 8.3 lint sweep over all
`interface/**/*.{php,inc}`, an installer smoke test with admin-login E2E,
and a full Docker Compose end-to-end test on every push.

### [training ibsng (persian)](https://raw.githubusercontent.com/imafaz/IBSng/main/training.pdf)

## License

This project is licensed under the MIT License. Refer to the [LICENSE](LICENSE) file for more information.
