"""
OpenVPN RAS integration (phase 5).

- agent unit tests: deterministic session identity, RADIUS attribute
  mapping, OpenVPN status-file parsing, env/config handling
- RAS unit tests: packet -> ras_msg translation (auth/start/stop/alive),
  onlines bookkeeping, type registration
"""
import importlib.util
import os
import sys

import pytest

from tests.conftest import REPO_ROOT, requires_engine


def _load_agent():
    path = os.path.join(REPO_ROOT, "addons", "openvpn", "openvpn_agent.py")
    spec = importlib.util.spec_from_file_location("openvpn_agent", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["openvpn_agent"] = module
    spec.loader.exec_module(module)
    return module


agent = _load_agent()


class FakeReply:
    def __init__(self, code):
        self.code = code


@pytest.fixture()
def clean_env(monkeypatch):
    for key in list(os.environ):
        if key.startswith("IBSNG_"):
            monkeypatch.delenv(key, raising=False)
    return monkeypatch


# ---------------------------------------------------------------- agent: identity

def test_nas_port_deterministic_across_hook_phases(clean_env):
    # auth phase: untrusted_*; connect/disconnect phase: trusted_*
    auth_env = {"common_name": "alice", "untrusted_ip": "203.0.113.7", "untrusted_port": "50100"}
    conn_env = {"common_name": "alice", "trusted_ip": "203.0.113.7", "trusted_port": "50100"}

    auth_attrs = agent.base_attrs(auth_env)
    conn_attrs = agent.base_attrs(conn_env)

    assert auth_attrs["NAS-Port"] == conn_attrs["NAS-Port"]
    assert auth_attrs["Acct-Session-Id"] == conn_attrs["Acct-Session-Id"]
    assert auth_attrs["User-Name"] == "alice"
    assert auth_attrs["Calling-Station-Id"] == "203.0.113.7"
    assert 0 <= auth_attrs["NAS-Port"] <= 0x7FFFFFFF


def test_nas_port_differs_per_user_and_ip(clean_env):
    a = agent.base_attrs({"common_name": "alice", "trusted_ip": "10.0.0.1"})
    b = agent.base_attrs({"common_name": "bob", "trusted_ip": "10.0.0.1"})
    c = agent.base_attrs({"common_name": "alice", "trusted_ip": "10.0.0.2"})
    assert len({a["NAS-Port"], b["NAS-Port"], c["NAS-Port"]}) == 3
    assert a["Acct-Session-Id"] != c["Acct-Session-Id"]


# ---------------------------------------------------------------- agent: attributes

def test_stop_attrs_byte_direction(clean_env):
    # OpenVPN bytes_received = from client = uplink = RADIUS Acct-Input-Octets
    # OpenVPN bytes_sent     = to client   = downlink = RADIUS Acct-Output-Octets
    env = {
        "common_name": "alice",
        "trusted_ip": "203.0.113.7",
        "bytes_received": "1111",
        "bytes_sent": "2222",
        "time_duration": "3600",
        "ifconfig_pool_remote_ip": "10.8.0.2",
    }
    attrs = agent.stop_attrs(env)
    assert attrs["Acct-Status-Type"] == agent.ACCT_STOP
    assert attrs["Acct-Input-Octets"] == 1111
    assert attrs["Acct-Output-Octets"] == 2222
    assert attrs["Acct-Session-Time"] == 3600
    assert attrs["Framed-IP-Address"] == "10.8.0.2"
    assert attrs["Acct-Terminate-Cause"] == agent.TERM_USER_REQUEST


def test_stop_attrs_tolerates_missing_bytes(clean_env):
    attrs = agent.stop_attrs({"common_name": "alice", "trusted_ip": "1.2.3.4"})
    assert "Acct-Input-Octets" not in attrs
    assert "Acct-Output-Octets" not in attrs
    assert attrs["Acct-Status-Type"] == agent.ACCT_STOP


def test_alive_attrs_mapping(clean_env):
    row = {
        "common_name": "alice",
        "real_address": "203.0.113.7:50100",
        "bytes_received": 1111,
        "bytes_sent": 2222,
        "virtual_address": "10.8.0.2",
    }
    attrs = agent.alive_attrs(row)
    assert attrs["User-Name"] == "alice"
    assert attrs["NAS-Port"] == agent.nas_port("alice", "203.0.113.7")
    assert attrs["Acct-Status-Type"] == agent.ACCT_ALIVE
    assert attrs["Acct-Input-Octets"] == 1111
    assert attrs["Acct-Output-Octets"] == 2222
    assert attrs["Framed-IP-Address"] == "10.8.0.2"
    assert attrs["Calling-Station-Id"] == "203.0.113.7"


# ---------------------------------------------------------------- agent: status file

STATUS_V2 = """TITLE,OpenVPN 2.6 status
TIME,Sun Sep 27 12:00:00 2026
HEADER,common_name,real_address,virtual_address,virtual_ipv6_address,bytes_received,bytes_sent,connected_since,ping_since
CLIENT_LIST,alice,203.0.113.7:50100,10.8.0.2,,1111,2222,Sun Sep 27 11:00:00 2026,Sun Sep 27 11:59:30 2026
CLIENT_LIST,bob,198.51.100.9:40000,10.8.0.3,,10,20,Sun Sep 27 11:30:00 2026,Sun Sep 27 11:59:40 2026
HEADER,destination,netmask,gateway
ROUTE,0.0.0.0,0.0.0.0,10.8.0.1
"""

STATUS_V1 = """OpenVPN Status List
Sun Sep 27 12:00:00 2026
Common Name,Real Address,Bytes Received,Bytes Sent,Connected Since
alice,203.0.113.7:50100,1111,2222,Sun Sep 27 11:00:00 2026
"""


def test_parse_status_file_v2(clean_env):
    clients = agent.parse_status_file(STATUS_V2)
    assert [c["common_name"] for c in clients] == ["alice", "bob"]
    alice = clients[0]
    assert alice["real_address"] == "203.0.113.7:50100"
    assert alice["bytes_received"] == 1111
    assert alice["bytes_sent"] == 2222
    assert alice["virtual_address"] == "10.8.0.2"


def test_parse_status_file_v1(clean_env):
    clients = agent.parse_status_file(STATUS_V1)
    assert len(clients) == 1
    assert clients[0]["common_name"] == "alice"
    assert clients[0]["bytes_received"] == 1111


def test_real_address_ip(clean_env):
    assert agent.real_address_ip("203.0.113.7:50100") == "203.0.113.7"
    assert agent.real_address_ip("[2001:db8::1]:1194") == "2001:db8::1"
    assert agent.real_address_ip("") == ""


# ---------------------------------------------------------------- agent: config/commands

def test_env_config_requires_secret(clean_env, monkeypatch):
    monkeypatch.setenv("IBSNG_AGENT_ENV", "/nonexistent/openvpn_agent.env")
    cfg = agent.env_config()
    assert cfg["secret"] == ""


def test_env_config_reads_secret_from_env_file(clean_env, monkeypatch, tmp_path):
    env_file = tmp_path / "openvpn_agent.env"
    env_file.write_text('IBSNG_RADIUS_SECRET="s3cret"\nIBSNG_RADIUS_HOST=10.9.9.9\n')
    monkeypatch.setenv("IBSNG_AGENT_ENV", str(env_file))
    cfg = agent.env_config()
    assert cfg["secret"] == "s3cret"
    assert cfg["host"] == "10.9.9.9"


def test_read_creds_file(clean_env, tmp_path):
    creds = tmp_path / "creds"
    creds.write_text("alice\ntopsecret\n")
    assert agent.read_creds_file(str(creds)) == ("alice", "topsecret")


def test_cmd_auth_accept(clean_env, monkeypatch, tmp_path):
    creds = tmp_path / "creds"
    creds.write_text("alice\npw\n")
    monkeypatch.setenv("IBSNG_RADIUS_SECRET", "x")

    seen = {}

    def fake_send(cfg, is_auth, attrs, dict_path=None):
        seen["is_auth"] = is_auth
        seen["attrs"] = attrs
        return FakeReply(__import__("radius_server.pyrad.packet", fromlist=["packet"]).AccessAccept)

    monkeypatch.setattr(agent, "send", fake_send)
    rc = agent.cmd_auth(agent.env_config(), [str(creds)])
    assert rc == 0
    assert seen["is_auth"] is True
    assert seen["attrs"]["User-Name"] == "alice"
    assert seen["attrs"]["User-Password"] == "pw"
    assert seen["attrs"]["NAS-Port"] == agent.nas_port("alice", "")


def test_cmd_auth_reject(clean_env, monkeypatch):
    monkeypatch.setenv("IBSNG_RADIUS_SECRET", "x")
    from radius_server.pyrad import packet as rad_packet
    monkeypatch.setattr(agent, "send",
                        lambda *a, **k: FakeReply(rad_packet.AccessReject))
    rc = agent.cmd_auth(agent.env_config(), ["--username", "mallory", "wrong"])
    assert rc == 1


def test_cmd_start_sends_accounting_start(clean_env, monkeypatch):
    monkeypatch.setenv("IBSNG_RADIUS_SECRET", "x")
    monkeypatch.setenv("common_name", "alice")
    monkeypatch.setenv("trusted_ip", "203.0.113.7")
    monkeypatch.setenv("ifconfig_pool_remote_ip", "10.8.0.2")

    seen = {}
    monkeypatch.setattr(agent, "send",
                        lambda cfg, is_auth, attrs, dict_path=None:
                        seen.update(is_auth=is_auth, attrs=attrs) or FakeReply(5))
    rc = agent.cmd_start(agent.env_config(), [])
    assert rc == 0
    assert seen["is_auth"] is False
    assert seen["attrs"]["Acct-Status-Type"] == agent.ACCT_START
    assert seen["attrs"]["Framed-IP-Address"] == "10.8.0.2"


def test_cmd_interim_walks_status_file(clean_env, monkeypatch, tmp_path):
    monkeypatch.setenv("IBSNG_RADIUS_SECRET", "x")
    status = tmp_path / "status"
    status.write_text(STATUS_V2)

    sent = []

    def fake_send(cfg, is_auth, attrs, dict_path=None):
        sent.append(attrs)
        return FakeReply(5)

    monkeypatch.setattr(agent, "send", fake_send)
    rc = agent.cmd_interim(agent.env_config(), ["--status-file", str(status)])
    assert rc == 0
    assert len(sent) == 2
    assert {a["User-Name"] for a in sent} == {"alice", "bob"}
    assert all(a["Acct-Status-Type"] == agent.ACCT_ALIVE for a in sent)


def test_cmd_interim_missing_status_file(clean_env, monkeypatch):
    monkeypatch.setenv("IBSNG_RADIUS_SECRET", "x")
    assert agent.cmd_interim(agent.env_config(), ["--status-file", "/no/such/file"]) == 1


# ---------------------------------------------------------------- RAS class

def _make_ras():
    from core.ras.rases.openvpn import OpenVPNRas
    return OpenVPNRas("127.0.0.1", 1, "openvpn nas", "openvpn", "secret", "", [], [], {})


def _make_packets(is_auth):
    from radius_server.pyrad import client, packet, dictionary
    dict_path = os.path.join(REPO_ROOT, "radius_server", "dictionary")
    dict_obj = dictionary.Dictionary(dict_path)
    srv = client.Client("127.0.0.1", 1812, 1813, b"secret", dict_obj)
    if is_auth:
        req = srv.CreateAuthPacket()
        reply = req.CreateReply()
    else:
        req = srv.CreateAcctPacket()
        reply = srv.CreateAcctPacket(code=packet.AccountingResponse)
    reply.dict = dict_obj  # same as rad_server does for outgoing packets
    return req, reply


@requires_engine
class TestOpenVPNRas:
    def test_type_registration(self, monkeypatch):
        from core.ras import ras_main
        from core.ras.ras_factory import RasFactory
        factory = RasFactory()
        monkeypatch.setattr(ras_main, "ras_factory", factory, raising=False)
        import core.ras.rases.openvpn as openvpn_mod
        openvpn_mod.init()
        assert factory.hasType("openvpn")
        assert factory.getClassFor("openvpn").__name__ == "OpenVPNRas"

    def test_auth_packet_translation(self):
        from core.ras.msgs import RasMsg
        ras = _make_ras()
        req, reply = _make_packets(is_auth=True)
        req["User-Name"] = "alice"
        req["User-Password"] = req.PwCrypt("pw")
        req["NAS-Port"] = 1234567
        req["Calling-Station-Id"] = "203.0.113.7"

        msg = RasMsg(req, reply, ras)
        ras.handleRadAuthPacket(msg)

        assert msg.getAction() == "INTERNET_AUTHENTICATE"
        assert msg["unique_id"] == "port"
        assert msg["port"] == "1234567"
        assert isinstance(msg["username"], str)
        assert msg["username"] == "alice"
        # pap_password stays the obfuscated wire bytes; password.py decrypts
        # it with PwDecrypt at login time
        assert isinstance(msg["pap_password"], bytes)
        assert req.PwDecrypt(msg["pap_password"]) == b"pw"
        assert msg["station_ip"] == "203.0.113.7"
        assert reply["Acct-Interim-Interval"] == [60]

    def test_acct_start_creates_online(self):
        from core.ras.msgs import RasMsg
        ras = _make_ras()
        req, reply = _make_packets(is_auth=False)
        req["User-Name"] = "alice"
        req["NAS-Port"] = 1234567
        req["Acct-Status-Type"] = 1  # Start, as the agent sends it
        req["Acct-Session-Id"] = "openvpn-deadbeef"
        req["Framed-IP-Address"] = "10.8.0.2"

        msg = RasMsg(req, reply, ras)
        ras.handleRadAcctPacket(msg)

        assert msg.getAction() == "INTERNET_UPDATE"
        assert msg["start_accounting"] is True
        assert msg["username"] == "alice"
        assert msg["session_id"] == "openvpn-deadbeef"
        assert msg["remote_ip"] == "10.8.0.2"
        assert "1234567" in ras.onlines
        assert ras.onlines["1234567"]["username"] == "alice"

    def test_acct_stop_finalizes_bytes(self):
        from core.ras.msgs import RasMsg
        ras = _make_ras()
        ras.onlines["1234567"] = {"username": "alice", "in_bytes": 0, "out_bytes": 0,
                                  "in_rate": 0, "out_rate": 0,
                                  "start_in_bytes": 0, "start_out_bytes": 0,
                                  "last_update": 0}

        req, reply = _make_packets(is_auth=False)
        req["User-Name"] = "alice"
        req["NAS-Port"] = 1234567
        req["Acct-Status-Type"] = 2  # Stop
        req["Acct-Session-Id"] = "openvpn-deadbeef"
        req["Acct-Input-Octets"] = 1111
        req["Acct-Output-Octets"] = 2222
        req["Acct-Terminate-Cause"] = 1  # User-Request

        msg = RasMsg(req, reply, ras)
        ras.handleRadAcctPacket(msg)

        assert msg.getAction() == "INTERNET_STOP"
        assert msg["in_bytes"] == 2222
        assert msg["out_bytes"] == 1111
        assert msg["terminate_cause"] == "User-Request"
        assert ras.onlines["1234567"]["in_bytes"] == 2222

    def test_acct_alive_updates_freshness_and_bytes(self, monkeypatch):
        from core.ras.msgs import RasMsg
        ras = _make_ras()
        monkeypatch.setattr(ras, "isUserOnline", lambda ras_msg: True)
        ras.onlines["1234567"] = {"username": "alice", "in_bytes": 10, "out_bytes": 20,
                                  "in_rate": 0, "out_rate": 0,
                                  "start_in_bytes": 0, "start_out_bytes": 0,
                                  "last_update": 0}

        req, reply = _make_packets(is_auth=False)
        req["User-Name"] = "alice"
        req["NAS-Port"] = 1234567
        req["Acct-Status-Type"] = 3  # Alive, as the agent sends it
        req["Acct-Input-Octets"] = 1111
        req["Acct-Output-Octets"] = 2222

        msg = RasMsg(req, reply, ras)
        ras.handleRadAcctPacket(msg)

        assert not msg.getAction()  # alive keeps the session, no engine action
        assert ras.onlines["1234567"]["in_bytes"] == 2222
        assert ras.onlines["1234567"]["out_bytes"] == 1111
        assert ras.onlines["1234567"]["last_update"] > 0

    def test_is_online_freshness_window(self, monkeypatch):
        ras = _make_ras()
        monkeypatch.setattr(ras, "getAttribute",
                            lambda name: {"openvpn_update_accounting_interval": 1,
                                          "openvpn_reonline_users": 1,
                                          "openvpn_mgmt_socket": "/tmp/x.sock",
                                          "openvpn_kill_timeout": 5}.get(name))
        ras.onlines["1234567"] = {"username": "alice", "in_bytes": 0, "out_bytes": 0,
                                  "last_update": __import__("time").time()}
        assert ras.isOnline({"port": "1234567"}) is True
        assert ras.isOnline({"port": "999999"}) is False

    def test_get_inout_bytes(self):
        ras = _make_ras()
        assert ras.getInOutBytes({"port": "42"}) == (0, 0, 0, 0)
        ras.onlines["42"] = {"username": "alice", "in_bytes": 100, "out_bytes": 200,
                             "in_rate": 1, "out_rate": 2, "last_update": 0}
        assert ras.getInOutBytes({"port": "42"}) == (100, 200, 1, 2)


# ---------------------------------------------------------------- py3 port regressions
# (gaps found while building the openvpn agent: engine-bound RADIUS strings
#  arrived as bytes, PAP compare rejected decrypted bytes, agent skipped PAP
#  obfuscation)

def test_password_eq_accepts_bytes():
    from core.lib.password_lib import Password
    assert Password("s3cret") == b"s3cret"
    assert Password("s3cret") == "s3cret"
    assert not (Password("s3cret") == b"wrong")


def test_rasmsg_decodes_string_attrs_but_keeps_binary(clean_env):
    from core.ras.msgs import RasMsg
    from radius_server.pyrad import client, packet, dictionary

    dict_obj = dictionary.Dictionary(os.path.join(REPO_ROOT, "radius_server", "dictionary"))
    srv = client.Client("127.0.0.1", 1812, 1813, b"secret", dict_obj)
    req = srv.CreateAuthPacket()
    reply = req.CreateReply()
    reply.dict = dict_obj

    req["User-Name"] = "alice"
    req["User-Password"] = req.PwCrypt("pw")
    req["NAS-Port"] = 7
    req["CHAP-Password"] = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10"

    class FakeRas:
        def getRasID(self):
            return 1

    msg = RasMsg(req, reply, FakeRas())
    msg.setInAttrs({"User-Name": "username"})
    msg.setInAttrsIfExists({"User-Password": "pap_password",
                            "CHAP-Password": "chap_password"})

    assert isinstance(msg["username"], str) and msg["username"] == "alice"
    assert isinstance(msg["pap_password"], bytes)   # obfuscated, decrypt later
    assert isinstance(msg["chap_password"], bytes)  # octets type stays binary
    assert req.PwDecrypt(msg["pap_password"]) == b"pw"


def test_agent_send_pap_obfuscates_password(clean_env, monkeypatch):
    monkeypatch.setenv("IBSNG_RADIUS_SECRET", "s3cr3t")
    monkeypatch.setenv("IBSNG_AGENT_ENV", "/nonexistent/env")

    from radius_server.pyrad import client as pyrad_client
    captured = {}

    def fake_send(self, pkt):
        captured["pkt"] = pkt
        return FakeReply(2)  # AccessAccept

    monkeypatch.setattr(pyrad_client.Client, "SendPacket", fake_send)

    cfg = agent.env_config()
    reply = agent.send(cfg, True, {"User-Name": "alice",
                                   "User-Password": "pw",
                                   "NAS-Port": 5})
    assert reply.code == 2
    pkt = captured["pkt"]
    assert pkt.PwDecrypt(pkt["User-Password"][0]) == b"pw"
    assert pkt["User-Password"][0] != b"pw"


# ---------------------------------------------------------------- cross-hook identity
# auth sees the PAP username; connect/disconnect/status hooks only see the
# certificate common_name - a mapping keyed by (ip, port) keeps one identity

def test_identity_mapping_roundtrip(clean_env, monkeypatch, tmp_path):
    monkeypatch.setenv("IBSNG_AUTH_DIR", str(tmp_path))
    agent.save_auth_identity("alice", "203.0.113.7", "50100")
    assert agent.load_auth_identity("203.0.113.7", "50100") == "alice"
    assert agent.load_auth_identity("203.0.113.7", "50101") is None
    agent.drop_auth_identity("203.0.113.7", "50100")
    assert agent.load_auth_identity("203.0.113.7", "50100") is None


def test_connect_hook_uses_authenticated_username(clean_env, monkeypatch, tmp_path):
    monkeypatch.setenv("IBSNG_AUTH_DIR", str(tmp_path))
    # auth accepted for username alice from 203.0.113.7:50100
    agent.save_auth_identity("alice", "203.0.113.7", "50100")

    # connect hook: certificate CN differs, same 5-tuple
    env = {"common_name": "cert-cn-ignored",
           "trusted_ip": "203.0.113.7", "trusted_port": "50100"}
    attrs = agent.base_attrs(env)
    assert attrs["User-Name"] == "alice"
    # and it matches what auth computed for the same username+ip
    auth_attrs = agent.base_attrs({"common_name": "alice",
                                   "untrusted_ip": "203.0.113.7",
                                   "untrusted_port": "50100"})
    assert attrs["NAS-Port"] == auth_attrs["NAS-Port"]
    assert attrs["Acct-Session-Id"] == auth_attrs["Acct-Session-Id"]


def test_cmd_auth_accept_saves_mapping(clean_env, monkeypatch, tmp_path):
    monkeypatch.setenv("IBSNG_RADIUS_SECRET", "x")
    monkeypatch.setenv("IBSNG_AUTH_DIR", str(tmp_path))
    monkeypatch.setenv("untrusted_ip", "203.0.113.7")
    monkeypatch.setenv("untrusted_port", "50100")
    from radius_server.pyrad import packet as rad_packet
    monkeypatch.setattr(agent, "send",
                        lambda *a, **k: FakeReply(rad_packet.AccessAccept))
    rc = agent.cmd_auth(agent.env_config(), ["--username", "alice", "pw"])
    assert rc == 0
    assert agent.load_auth_identity("203.0.113.7", "50100") == "alice"


def test_cmd_stop_drops_mapping(clean_env, monkeypatch, tmp_path):
    monkeypatch.setenv("IBSNG_RADIUS_SECRET", "x")
    monkeypatch.setenv("IBSNG_AUTH_DIR", str(tmp_path))
    monkeypatch.setenv("trusted_ip", "203.0.113.7")
    monkeypatch.setenv("trusted_port", "50100")
    agent.save_auth_identity("alice", "203.0.113.7", "50100")
    monkeypatch.setattr(agent, "send", lambda *a, **k: FakeReply(5))
    rc = agent.cmd_stop(agent.env_config(), [])
    assert rc == 0
    assert agent.load_auth_identity("203.0.113.7", "50100") is None
