#!/usr/bin/env python3
"""
RADIUS agent for OpenVPN <-> IBSng.

Invoked by OpenVPN hooks:

  auth-user-pass-verify  .../openvpn_agent.py auth <creds-file>
  client-connect         .../openvpn_agent.py start
  client-disconnect      .../openvpn_agent.py stop
  interim updates (cron): openvpn_agent.py interim --status-file <file>

Configuration (environment):
  IBSNG_RADIUS_SECRET     RADIUS shared secret (REQUIRED)
  IBSNG_RADIUS_HOST       default 127.0.0.1
  IBSNG_RADIUS_AUTH_PORT  default 1812
  IBSNG_RADIUS_ACCT_PORT  default 1813
  IBSNG_RADIUS_TIMEOUT    seconds, default 5
  IBSNG_RADIUS_RETRIES    default 2
  IBSNG_NAS_IDENTIFIER    optional NAS-Identifier attribute value
  IBSNG_DICTIONARY        optional path to the RADIUS dictionary file

The RAS is matched by packet source IP, so the agent must send from the IP
the "openvpn" RAS was created with (normally 127.0.0.1).

NAS-Port (the engine's per-session unique id) is derived deterministically
from common_name + client IP so auth, start, stop and interim all agree
across OpenVPN hook invocations.
"""

import os
import sys
import time
import zlib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
if os.path.isdir(os.path.join(REPO_ROOT, "radius_server")):
    sys.path.insert(0, REPO_ROOT)

from radius_server.pyrad import client, packet, dictionary  # noqa: E402

DEFAULTS = {
    "host": "127.0.0.1",
    "auth_port": 1812,
    "acct_port": 1813,
    "timeout": 5,
    "retries": 2,
}

ACCT_START = 1
ACCT_STOP = 2
ACCT_ALIVE = 3
TERM_USER_REQUEST = 1  # VALUE Acct-Terminate-Cause User-Request


def load_env_file(path):
    """
        KEY=VALUE lines; used so cron/systemd can run interim updates
        without embedding the secret in the crontab
    """
    env = {}
    try:
        with open(path) as fd:
            for line in fd:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return env


def env_config():
    cfg = dict(DEFAULTS)
    cfg["secret"] = os.environ.get("IBSNG_RADIUS_SECRET", "")
    if not cfg["secret"]:
        env_file = os.environ.get("IBSNG_AGENT_ENV", "/etc/ibsng/openvpn_agent.env")
        file_env = load_env_file(env_file)
        cfg["secret"] = file_env.get("IBSNG_RADIUS_SECRET", "")
        for key in ("IBSNG_RADIUS_HOST", "IBSNG_RADIUS_AUTH_PORT",
                    "IBSNG_RADIUS_ACCT_PORT", "IBSNG_NAS_IDENTIFIER"):
            if key in file_env:
                os.environ.setdefault(key, file_env[key])
    cfg["host"] = os.environ.get("IBSNG_RADIUS_HOST", cfg["host"])
    cfg["auth_port"] = int(os.environ.get("IBSNG_RADIUS_AUTH_PORT", cfg["auth_port"]))
    cfg["acct_port"] = int(os.environ.get("IBSNG_RADIUS_ACCT_PORT", cfg["acct_port"]))
    cfg["timeout"] = int(os.environ.get("IBSNG_RADIUS_TIMEOUT", cfg["timeout"]))
    cfg["retries"] = int(os.environ.get("IBSNG_RADIUS_RETRIES", cfg["retries"]))
    cfg["nas_identifier"] = os.environ.get("IBSNG_NAS_IDENTIFIER", "")
    return cfg


def auth_dir():
    return os.environ.get("IBSNG_AUTH_DIR", "/tmp/ibsng_openvpn_auth")


def _auth_key(ip, port):
    return "%s_%s" % ((ip or "").replace(":", "_"), port or "")


def save_auth_identity(cn, ip, port):
    """
        remember the PAP username for this (ip, port) 5-tuple so the
        client-connect/disconnect/status hooks - which only see the
        certificate common_name - use the same session identity as auth
    """
    if not (cn and ip and port):
        return
    path = auth_dir()
    try:
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, _auth_key(ip, port)), "w") as fd:
            fd.write(cn)
        # prune stale mappings from crashed sessions
        cutoff = time.time() - 86400
        for name in os.listdir(path):
            full = os.path.join(path, name)
            try:
                if os.path.getmtime(full) < cutoff:
                    os.remove(full)
            except OSError:
                pass
    except OSError:
        pass


def load_auth_identity(ip, port):
    try:
        with open(os.path.join(auth_dir(), _auth_key(ip, port))) as fd:
            value = fd.read().strip()
        return value or None
    except OSError:
        return None


def drop_auth_identity(ip, port):
    try:
        os.remove(os.path.join(auth_dir(), _auth_key(ip, port)))
    except OSError:
        pass


def find_dictionary():
    candidates = [os.environ.get("IBSNG_DICTIONARY", "")]
    candidates.append(os.path.join(REPO_ROOT, "radius_server", "dictionary"))
    candidates.append("/usr/local/ibsng/radius_server/dictionary")
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    raise SystemExit("openvpn_agent: RADIUS dictionary not found (set IBSNG_DICTIONARY)")


def common_name(env):
    return env.get("common_name", "") or ""


def client_ip(env):
    """
        real client address; OpenVPN exposes it as trusted_ip once the
        connection is trusted, untrusted_ip during authentication
    """
    for key in ("trusted_ip", "untrusted_ip", "peer_ip"):
        if env.get(key):
            return env[key]
    return ""


def client_port(env):
    for key in ("trusted_port", "untrusted_port"):
        if env.get(key):
            return env[key]
    return ""


def nas_port(cn, ip):
    """
        deterministic numeric NAS-Port for (common_name, client ip)
    """
    return zlib.crc32(("%s|%s" % (cn, ip)).encode("utf-8")) & 0x7FFFFFFF


def session_id(cn, ip):
    return "openvpn-%08x" % (zlib.crc32(("session|%s|%s" % (cn, ip)).encode("utf-8")) & 0xFFFFFFFF)


def identity(env):
    """
        session identity: the authenticated PAP username when known,
        otherwise the certificate common_name
    """
    ip = client_ip(env)
    mapped = load_auth_identity(ip, client_port(env))
    return mapped or common_name(env)


def base_attrs(env):
    cn = identity(env)
    ip = client_ip(env)
    attrs = {
        "User-Name": cn,
        "NAS-Port": nas_port(cn, ip),
        "Acct-Session-Id": session_id(cn, ip),
    }
    if ip:
        attrs["Calling-Station-Id"] = ip
    return attrs


def send(cfg, is_auth, attrs, dict_path=None):
    """
        send one RADIUS request, return the reply packet (or raise)
    """
    if not cfg["secret"]:
        raise SystemExit("openvpn_agent: IBSNG_RADIUS_SECRET is not set")

    dict_obj = dictionary.Dictionary(dict_path or find_dictionary())
    srv = client.Client(cfg["host"], cfg["auth_port"], cfg["acct_port"],
                        cfg["secret"].encode("utf-8"), dict_obj)
    srv.timeout = cfg["timeout"]
    srv.retries = cfg["retries"]

    if is_auth:
        req = srv.CreateAuthPacket()
    else:
        req = srv.CreateAcctPacket()

    for key, value in attrs.items():
        if value is None or value == "":
            continue
        if is_auth and key == "User-Password":
            req[key] = req.PwCrypt(value)  # RADIUS PAP obfuscation
        else:
            req[key] = value

    if cfg["nas_identifier"]:
        req["NAS-Identifier"] = cfg["nas_identifier"]

    return srv.SendPacket(req)


def read_creds_file(path):
    with open(path, "rb") as fd:
        data = fd.read().decode("utf-8", "replace")
    lines = data.splitlines()
    username = lines[0] if lines else ""
    password = lines[1] if len(lines) > 1 else ""
    return username, password


def cmd_auth(cfg, argv):
    """
        auth-user-pass-verify (via-file): argv[0] = credentials file
        also accepts --username/--password for manual testing
        exit 0 = accept, exit 1 = reject (fail closed)
    """
    if argv and argv[0] == "--username":
        username, password = argv[1], (argv[2] if len(argv) > 2 else "")
    elif argv:
        username, password = read_creds_file(argv[0])
    else:
        sys.stderr.write("usage: openvpn_agent.py auth <creds-file> | --username U [P]\n")
        return 1

    env = os.environ.copy()
    env["common_name"] = username  # PAP identity decides the user, not cert CN here

    attrs = base_attrs(env)
    attrs["User-Password"] = password  # PwCrypt below

    try:
        reply = send(cfg, True, attrs)
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write("openvpn_agent: radius auth error: %s\n" % exc)
        return 1

    if reply.code == packet.AccessAccept:
        env = os.environ
        save_auth_identity(username, env.get("untrusted_ip") or env.get("trusted_ip") or "",
                           env.get("untrusted_port") or env.get("trusted_port") or "")
        return 0
    sys.stderr.write("openvpn_agent: access rejected (code %s)\n" % reply.code)
    return 1


def cmd_start(cfg, argv):
    """
        client-connect: Accounting-Start; non-zero exit aborts the client
    """
    env = os.environ
    attrs = base_attrs(env)
    attrs["Acct-Status-Type"] = ACCT_START
    if env.get("ifconfig_pool_remote_ip"):
        attrs["Framed-IP-Address"] = env["ifconfig_pool_remote_ip"]

    try:
        reply = send(cfg, False, attrs)
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write("openvpn_agent: radius start error: %s\n" % exc)
        return 1

    if reply.code != packet.AccountingResponse:
        sys.stderr.write("openvpn_agent: start not acknowledged (code %s)\n" % reply.code)
        return 1
    return 0


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def stop_attrs(env):
    attrs = base_attrs(env)
    attrs["Acct-Status-Type"] = ACCT_STOP

    # OpenVPN: bytes_received = from client (uplink), bytes_sent = to client
    # RADIUS:  Acct-Input-Octets = from user (uplink), Acct-Output-Octets = downlink
    received = _int_or_none(env.get("bytes_received"))
    sent = _int_or_none(env.get("bytes_sent"))
    if received is not None:
        attrs["Acct-Input-Octets"] = received
    if sent is not None:
        attrs["Acct-Output-Octets"] = sent

    duration = _int_or_none(env.get("time_duration"))
    if duration is not None:
        attrs["Acct-Session-Time"] = duration

    if env.get("ifconfig_pool_remote_ip"):
        attrs["Framed-IP-Address"] = env["ifconfig_pool_remote_ip"]

    attrs["Acct-Terminate-Cause"] = TERM_USER_REQUEST
    return attrs


def cmd_stop(cfg, argv):
    """
        client-disconnect: Accounting-Stop (best effort, log and exit 0)
    """
    env = os.environ
    try:
        send(cfg, False, stop_attrs(env))
    except Exception as exc:
        sys.stderr.write("openvpn_agent: radius stop error: %s\n" % exc)
    drop_auth_identity(client_ip(env), client_port(env))
    return 0


def parse_status_file(text):
    """
        parse an OpenVPN --status file, return list of dicts with keys:
        common_name, real_address, bytes_received, bytes_sent, virtual_address
        supports status-version 1/2/3 layouts by mapping HEADER columns
    """
    clients = []
    header = None
    for raw in text.splitlines():
        line = raw.rstrip("\r")
        if not line:
            continue
        cells = line.split(",")
        head0 = cells[0].strip().lower().replace("_", " ")

        if head0 == "header":
            cols = [c.strip().lower().replace(" ", "_") for c in cells[1:]]
            if "common_name" in cols and "bytes_received" in cols:
                header = cols
            else:
                header = None
            continue

        # status-version 1 header line: "Common Name,Real Address,Bytes Received,..."
        if header is None and "common name" in head0 and "bytes received" in line.lower():
            header = [c.strip().lower().replace(" ", "_") for c in cells]
            continue

        if header is None:
            continue

        if cells[0].strip() == "CLIENT_LIST":
            data = cells[1:]
        elif len(cells) == len(header):
            data = cells
        else:
            continue

        if len(data) < len(header):
            continue

        row = dict(zip(header, [c.strip() for c in data]))
        if "common_name" not in row:
            continue

        clients.append({
            "common_name": row.get("common_name", ""),
            "real_address": row.get("real_address", ""),
            "bytes_received": _int_or_none(row.get("bytes_received")),
            "bytes_sent": _int_or_none(row.get("bytes_sent")),
            "virtual_address": row.get("virtual_address", ""),
        })
    return clients


def real_address_ip(addr):
    """
        "1.2.3.4:1194" -> "1.2.3.4"; "[2001:db8::1]:1194" -> "2001:db8::1"
    """
    addr = addr or ""
    if addr.startswith("["):
        return addr[1:].split("]")[0]
    if addr.count(":") == 1:
        return addr.split(":")[0]
    return addr


def alive_attrs(client_row):
    ip = real_address_ip(client_row["real_address"])
    cn = client_row["common_name"]
    attrs = {
        "User-Name": cn,
        "NAS-Port": nas_port(cn, ip),
        "Acct-Session-Id": session_id(cn, ip),
        "Acct-Status-Type": ACCT_ALIVE,
    }
    if client_row.get("bytes_received") is not None:
        attrs["Acct-Input-Octets"] = client_row["bytes_received"]
    if client_row.get("bytes_sent") is not None:
        attrs["Acct-Output-Octets"] = client_row["bytes_sent"]
    if client_row.get("virtual_address"):
        attrs["Framed-IP-Address"] = client_row["virtual_address"]
    if ip:
        attrs["Calling-Station-Id"] = ip
    return attrs


def cmd_interim(cfg, argv):
    status_path = None
    if "--status-file" in argv:
        idx = argv.index("--status-file")
        if idx + 1 < len(argv):
            status_path = argv[idx + 1]
    if not status_path:
        sys.stderr.write("usage: openvpn_agent.py interim --status-file <file>\n")
        return 1
    if not os.path.isfile(status_path):
        sys.stderr.write("openvpn_agent: status file %s missing\n" % status_path)
        return 1

    with open(status_path, "r", errors="replace") as fd:
        clients = parse_status_file(fd.read())

    failures = 0
    for client_row in clients:
        try:
            reply = send(cfg, False, alive_attrs(client_row))
            if reply.code != packet.AccountingResponse:
                failures += 1
        except Exception as exc:
            failures += 1
            sys.stderr.write("openvpn_agent: interim error for %s: %s\n" %
                             (client_row["common_name"], exc))
    return 1 if failures else 0


COMMANDS = {
    "auth": cmd_auth,
    "start": cmd_start,
    "stop": cmd_stop,
    "interim": cmd_interim,
}


def main(argv):
    if len(argv) < 1 or argv[0] not in COMMANDS:
        sys.stderr.write("usage: openvpn_agent.py {%s} [...]\n" % "|".join(sorted(COMMANDS)))
        return 1
    cfg = env_config()
    return COMMANDS[argv[0]](cfg, argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
