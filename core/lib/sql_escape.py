"""
Shared SQL text escaping for IBSng.

Used by:
  - core.lib.general (dbText and friends, consumed by every query builder
    via `from core.lib.general import *`)
  - core.defs_lib.defs2sql (install-time generation of db/defs.sql)

Escaping rules target PostgreSQL >= 9.1, where standard_conforming_strings
defaults to on (true for every supported platform, including CentOS 7's
PostgreSQL 9.2):
  - single quotes are doubled ("'" -> "''")
  - backslashes pass through verbatim

The historical implementation also doubled backslashes. Under
standard_conforming_strings=on that stored *two* backslash characters for
every one supplied, corrupting any value containing a backslash. The
backslash doubling is intentionally not performed.

HTML tags are stripped from stored text (except <br>), preserving the
long-standing IBSng behavior of escapeTags().
"""
import re

escape_tags = re.compile("<(?!br( /){0,1}>)(.*?)>")


def escapeTags(_str):
    return escape_tags.sub(r" - \2 - ", _str)


def escapeSlashes(_str):
    return _str.replace("'", "''")


def escapeStr(_str):
    if isinstance(_str, bytes):
        # Python-2 era callers passed byte strings; latin-1 preserves the
        # byte values 1:1 for best-effort compatibility.
        _str = _str.decode("latin-1")
    elif not isinstance(_str, str):
        _str = str(_str)
    return escapeSlashes(escapeTags(_str))


def dbText(text):
    return "'%s'" % escapeStr(text)
