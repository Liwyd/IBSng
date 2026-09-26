"""
defs: the generated db/defs.sql must load on modern PostgreSQL, match
core/defs_lib/defs_defaults.py exactly (no drift), and unpickle to the
values the engine expects.
"""
import os
import pickle

from conftest import REPO_ROOT

from core.defs_lib.defs2sql import getInsertQuery, loadDefs

DEF_DEFAULTS = loadDefs(os.path.join(REPO_ROOT, "core", "defs_lib",
                                     "defs_defaults.py"))


def test_generated_sql_matches_committed_file(db):
    """
        db/defs.sql is a generated artifact - regenerating it must be a
        no-op, otherwise installs would seed different defaults than the
        repository defines
    """
    path = os.path.join(REPO_ROOT, "db", "defs.sql")
    with open(path) as fd:
        committed = fd.read()
    assert getInsertQuery(DEF_DEFAULTS) == committed, \
        "db/defs.sql is stale - run: python3 core/defs_lib/defs2sql.py -i " \
        "core/defs_lib/defs_defaults.py db/defs.sql"


def test_defs_load_and_unpickle(dbtx):
    dbtx.query("delete from defs")
    with open(os.path.join(REPO_ROOT, "db", "defs.sql")) as fd:
        dbtx.query(fd.read())

    rows = dbtx.query("select name, value from defs").getresult()
    loaded = {}
    for name, value in rows:
        if isinstance(value, str):
            value = value.encode("latin-1")
        loaded[name] = pickle.loads(value, encoding="latin-1")

    # every default must be present and round-trip unchanged
    assert set(loaded) == set(DEF_DEFAULTS), \
        "defs.sql and defs_defaults.py disagree: %s" % (
            set(loaded) ^ set(DEF_DEFAULTS))
    for name, expected in DEF_DEFAULTS.items():
        assert loaded[name] == expected, "%s: %r != %r" % (
            name, loaded[name], expected)


def test_security_sensitive_defaults(db):
    """
        regression guards: defaults that widen the attack surface must not
        change silently
    """
    assert DEF_DEFAULTS["TRUSTED_CLIENTS"] == ["127.0.0.1"]
    assert DEF_DEFAULTS["IBS_SERVER_IP"] == "127.0.0.1"
    assert DEF_DEFAULTS["IBS_SERVER_PORT"] == 1235
    assert DEF_DEFAULTS["RADIUS_SERVER_BIND_IP"] == ["0.0.0.0"]  # RADIUS must stay reachable


def test_expected_types(db):
    assert isinstance(DEF_DEFAULTS["IBS_SERVER_PORT"], int)
    assert isinstance(DEF_DEFAULTS["IBS_SERVER_IP"], str)
    assert isinstance(DEF_DEFAULTS["TRUSTED_CLIENTS"], list)
    assert isinstance(DEF_DEFAULTS["WEB_ANALYZER_PASSWORD"], str)
