"""
Pure python md5crypt ($1$) compatible with the historic crypt.crypt() output.

The system "crypt" module is optional/removed on modern python versions
(gone in 3.13+), but IBSng stores user/admin passwords as $1$ hashes that
must keep verifying exactly as before.  This implements the FreeBSD
md5-crypt algorithm (see libxcrypt crypt-md5.c) which is what glibc,
openssl -1 and the original python "crypt" produced.
"""

import hashlib

ITOA64 = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_MAGIC = "$1$"


def _to64(value, count):
    out = []
    for _ in range(count):
        out.append(ITOA64[value & 0x3f])
        value >>= 6
    return "".join(out)


def _md5(*chunks):
    h = hashlib.md5()
    for c in chunks:
        h.update(c if isinstance(c, bytes) else c.encode("utf-8"))
    return h.digest()


def split_salt(salt):
    """
        accept "$1$abcdefgh$", "$1$abcdefgh" or "abcdefgh" and return
        the bare 8-char salt ("abcdefgh")
    """
    if salt.startswith(_MAGIC):
        salt = salt[len(_MAGIC):]
    return salt.rstrip("$")[:8]


def md5crypt(password, salt):
    """
        crypt "password" with md5crypt.
        "salt" may be a full "$1$salt$" spec or a bare salt string.
        returns the full "$1$salt$hash" string.
    """
    if isinstance(password, bytes):
        password = password.decode("utf-8", errors="surrogateescape")
    salt = split_salt(salt)
    pw = password.encode("utf-8")
    sa = salt.encode("utf-8")

    # step 1: md5(password + salt + password)
    final = _md5(pw, sa, pw)

    # main context: password + magic("$1$") + salt, then the truncated
    # digest fed back (step 2)
    ctx = hashlib.md5()
    ctx.update(pw)
    ctx.update(_MAGIC.encode("ascii"))
    ctx.update(sa)
    remaining = len(pw)
    while remaining > 0:
        ctx.update(final[:16 if remaining > 16 else remaining])
        remaining -= 16

    # step 3: bit loop over password length
    i = len(pw)
    while i:
        if i & 1:
            ctx.update(b"\x00")
        else:
            ctx.update(pw[:1])
        i >>= 1
    final = ctx.digest()

    # 1000 rounds
    for i in range(1000):
        ctx = hashlib.md5()
        if i & 1:
            ctx.update(pw)
        else:
            ctx.update(final)
        if i % 3:
            ctx.update(sa)
        if i % 7:
            ctx.update(pw)
        if i & 1:
            ctx.update(final)
        else:
            ctx.update(pw)
        final = ctx.digest()

    # base64-ish encoding of selected bytes (reversed order)
    h = []
    h.append(_to64((final[0] << 16) | (final[6] << 8) | final[12], 4))
    h.append(_to64((final[1] << 16) | (final[7] << 8) | final[13], 4))
    h.append(_to64((final[2] << 16) | (final[8] << 8) | final[14], 4))
    h.append(_to64((final[3] << 16) | (final[9] << 8) | final[15], 4))
    h.append(_to64((final[4] << 16) | (final[10] << 8) | final[5], 4))
    h.append(_to64(final[11], 2))
    return _MAGIC + salt + "$" + "".join(h)


def validate(password, hash_str):
    """
        verify "password" against a stored "$1$..." hash
    """
    if not hash_str.startswith(_MAGIC):
        return False
    try:
        salt = hash_str.rsplit("$", 2)[1]
    except IndexError:
        return False
    return md5crypt(password, _MAGIC + salt + "$") == hash_str
