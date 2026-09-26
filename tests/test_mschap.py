"""
Known-answer tests for the Python 3 port of the crypto/auth stack:

  - MS-CHAPv2 hash chain against RFC 2759 section 9.2 / 9.3 vectors
  - well-known NT (MD4/UTF-16LE) password hashes
  - vendored DES against OpenSSL (legacy provider)
  - vendored $1$ md5crypt against `openssl passwd -1`

The OpenSSL cross-checks skip themselves when openssl is unavailable.
"""
import hashlib
import shutil
import subprocess

import pytest

from core.lib.mschap import mschap
from core.lib.mschap.des import DES
from core.lib.md5crypt import md5crypt

# RFC 2759 section 9.2 example values
RFC_USER = "User"
RFC_PASSWORD = "clientPass"
RFC_AUTH_CHALLENGE = bytes.fromhex("5B5D7C7D7B3F2F3E3C2C602132262628")
RFC_PEER_CHALLENGE = bytes.fromhex("21402324255E262A28295F2B3A337C7E")


def test_challenge_hash_rfc2759():
    got = mschap.challenge_hash(RFC_PEER_CHALLENGE, RFC_AUTH_CHALLENGE, RFC_USER)
    assert got == bytes.fromhex("D02E4386BCE91226")


def test_nt_password_hash_rfc2759():
    got = mschap.nt_password_hash(RFC_PASSWORD, pad_to_21_bytes=False)
    assert got == bytes.fromhex("44EBBA8D5312B8D611474411F56989AE")


def test_nt_response_rfc2759():
    got = mschap.generate_nt_response_mschap2(
        RFC_AUTH_CHALLENGE, RFC_PEER_CHALLENGE, RFC_USER, RFC_PASSWORD
    )
    assert got == bytes.fromhex(
        "82309ECD8D708B5EA08FAA3981CD83544233114A3D85D6DF"
    )


def test_hash_nt_password_hash_rfc2759():
    nt_hash = mschap.nt_password_hash(RFC_PASSWORD, pad_to_21_bytes=False)
    got = mschap.hash_nt_password_hash(nt_hash)
    # RFC byte list: 41 C0 0C 58 4B D2 D9 1C 40 17 A2 A1 2F A5 9F 3F
    assert got == bytes.fromhex("41C00C584BD2D91C4017A2A12FA59F3F")


def test_authenticator_response_rfc2759():
    nt_response = mschap.generate_nt_response_mschap2(
        RFC_AUTH_CHALLENGE, RFC_PEER_CHALLENGE, RFC_USER, RFC_PASSWORD
    )
    got = mschap.generate_authenticator_response(
        RFC_PASSWORD,
        nt_response,
        RFC_PEER_CHALLENGE,
        RFC_AUTH_CHALLENGE,
        RFC_USER,
    )
    assert got == "S=407A5589115FD0D6209F510FE9C04566932CDA56"


def test_mypw_hash_rfc2759_section_9_3():
    got = mschap.nt_password_hash("MyPw", pad_to_21_bytes=False)
    assert got == bytes.fromhex("FC156AF7EDCD6C0EDDE3337D427F4EAC")


def test_nt_hash_known_values():
    # MD4(UTF-16LE(password)); these values are widely published
    assert mschap.nt_password_hash("", pad_to_21_bytes=False).hex() == (
        "31d6cfe0d16ae931b73c59d7e0c089c0"
    )
    assert mschap.nt_password_hash("password", pad_to_21_bytes=False).hex() == (
        "8846f7eaee8fb117ad06bdd830b7586c"
    )


def test_challenge_response_length():
    nt_hash = mschap.nt_password_hash(RFC_PASSWORD, pad_to_21_bytes=False)
    resp = mschap.challenge_response(
        bytes.fromhex("D02E4386BCE91226"), nt_hash
    )
    assert len(resp) == 24


def test_des_matches_openssl():
    if not shutil.which("openssl"):
        pytest.skip("openssl not available")
    clear = b"testtest"
    key7 = bytes.fromhex("FC156AF7EDCD6C")
    mine = DES(key7).encrypt(clear)
    assert len(mine) == 8

    proc = subprocess.run(
        [
            "openssl", "enc", "-des-ecb",
            "-provider", "legacy", "-provider", "default",
            "-K", "fd0b5b5e7f6e34d9",
            "-nopad",
        ],
        input=clear,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        pytest.skip("openssl des-ecb unavailable: %s" % proc.stderr.decode())
    assert mine == proc.stdout


def test_des_decrypt_roundtrip():
    d = DES(b"IBSngKey")
    clear = b"12345678"
    assert d.decrypt(d.encrypt(clear)) == clear


def test_md5crypt_matches_openssl():
    if not shutil.which("openssl"):
        pytest.skip("openssl not available")
    for password, salt in (
        ("password", "saltX1"),
        ("clientPass", "abc123"),
        ("", "s"),
        ("myP@ssW0rd", "./xQyZ99"),
    ):
        proc = subprocess.run(
            ["openssl", "passwd", "-1", "-salt", salt, "-stdin"],
            input=password.encode("utf-8") + b"\n",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if proc.returncode != 0:
            pytest.skip("openssl passwd -1 unavailable")
        expected = proc.stdout.decode().strip()
        assert md5crypt(password, salt) == expected


def test_md5crypt_validate():
    h = md5crypt("hunter2", "abcdefgh")
    from core.lib.md5crypt import validate

    assert validate("hunter2", h)
    assert not validate("hunter3", h)


def test_utils_hex_roundtrip():
    from core.lib.mschap import utils

    data = bytes(range(16))
    assert utils.hex2str(utils.str2hex(data)) == data
    # historic output is upper-case hex
    assert utils.str2hex(b"\xde\xad\xbe\xef") == "DEADBEEF"
    # historic semantics: little-endian word
    assert utils.bytes2int(b"\x01\x00") == 1
    assert utils.bytes2int(b"\x00\x01") == 256
