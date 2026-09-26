"""
IBSng test harness.

Database tests run against a real PostgreSQL instance. Connection settings
come from the environment (defaults match core/db_conf.py):

    IBSNG_TEST_DB_HOST       default 127.0.0.1
    IBSNG_TEST_DB_PORT       default 5432
    IBSNG_TEST_DB_USER       default ibs
    IBSNG_TEST_DB_PASSWORD   default ibsdbpass
    IBSNG_TEST_DB_NAME       default IBSng

If the target database exists but has no schema, the standard db/*.sql files
are loaded (same order as the installer). An already-provisioned database is
never dropped or recreated. All mutating tests run inside an explicit
transaction that is rolled back.

Tests that need the IBSng engine skip themselves with an explanatory reason
until the engine is importable under python 3 (phase 1 of the port).
"""
import importlib.util
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

DB_CONF = {
    "host": os.environ.get("IBSNG_TEST_DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("IBSNG_TEST_DB_PORT", "5432")),
    "user": os.environ.get("IBSNG_TEST_DB_USER", "ibs"),
    "passwd": os.environ.get("IBSNG_TEST_DB_PASSWORD", "ibsdbpass"),
    "dbname": os.environ.get("IBSNG_TEST_DB_NAME", "IBSng"),
}

SCHEMA_FILES = ("tables.sql", "functions.sql", "initial.sql", "defs.sql")


def _connect():
    pg = pytest.importorskip(
        "pg", reason="PyGreSQL (python3-pygresql / pip 'PyGreSQL') is required")
    return pg.connect(dbname=DB_CONF["dbname"], host=DB_CONF["host"],
                      port=DB_CONF["port"], user=DB_CONF["user"],
                      passwd=DB_CONF["passwd"])


def _table_exists(conn, table):
    res = conn.query(
        "select 1 from pg_catalog.pg_tables where schemaname='public' and tablename='%s'"
        % table)
    return len(res.getresult()) == 1


def _load_schema(conn):
    db_dir = os.path.join(REPO_ROOT, "db")
    for name in SCHEMA_FILES:
        with open(os.path.join(db_dir, name)) as fd:
            conn.query(fd.read())


@pytest.fixture(scope="session")
def db():
    """
        session-wide connection; ensures the schema exists on first use
    """
    try:
        conn = _connect()
    except Exception as exc:
        pytest.skip("database not reachable (%s:%s): %s" %
                    (DB_CONF["host"], DB_CONF["port"], exc))
    if not _table_exists(conn, "users"):
        _load_schema(conn)
        if not _table_exists(conn, "users"):
            pytest.skip("schema could not be loaded into %s" % DB_CONF["dbname"])
    yield conn


@pytest.fixture()
def dbtx(db):
    """
        transactional connection: every statement is rolled back on teardown,
        so tests never leave data behind and can be re-run at will
    """
    db.query("BEGIN")
    yield db
    db.query("ROLLBACK")


def engine_importable():
    """
        True once the IBSng engine imports under python 3 (phase 1 done)
    """
    for module_name in ("core.main", "core.user.online", "core.charge.charge"):
        if importlib.util.find_spec(module_name) is None:
            return False
        try:
            __import__(module_name)
        except SyntaxError:
            return False
        except Exception:
            # module exists and parses but its import graph is not fully
            # ported yet - keep skipping until the port lands
            return False
    return True


requires_engine = pytest.mark.skipif(
    not engine_importable(),
    reason="IBSng engine not yet importable under python 3 (python 3 port pending)")
