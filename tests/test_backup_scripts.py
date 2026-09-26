"""
End-to-end tests for the backup_ibs / restore_ibs shell scripts.

The scripts run against the test database with IBS_BACKUP_NO_SU=1 and
IBS_BACKUP_SKIP_SERVICE=1, so neither root ("su postgres") nor a system
service manager is required. Restore is exercised against a scratch
database; the primary test database is never dropped.
"""
import os
import shutil
import subprocess

import pytest

from conftest import DB_CONF, REPO_ROOT

SCRATCH_DB = "IBSng_restore_test"
PG_TOOLS = ("pg_dump", "psql", "dropdb", "createdb")

pytestmark = pytest.mark.skipif(
    not all(shutil.which(tool) for tool in PG_TOOLS),
    reason="postgresql client tools (pg_dump/psql) not available")


def _script(name):
    return os.path.join(REPO_ROOT, name)


def _base_env(db_name):
    env = dict(os.environ)
    env.update({
        "PGHOST": DB_CONF["host"],
        "PGPORT": str(DB_CONF["port"]),
        "PGUSER": DB_CONF["user"],
        "PGPASSWORD": DB_CONF["passwd"],
        "IBS_BACKUP_NO_SU": "1",
        "IBS_BACKUP_SKIP_SERVICE": "1",
        "IBS_BACKUP_DB": db_name,
    })
    return env


def _run(script, env, *args):
    return subprocess.run(["bash", script] + list(args), env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, timeout=120)


def _query(db_name, sql, env):
    proc = subprocess.run(
        ["psql", "-h", env["PGHOST"], "-p", env["PGPORT"],
         "-U", env["PGUSER"], "-d", db_name, "-tAc", sql],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def _drop_scratch(env):
    subprocess.run(["dropdb", "--if-exists", SCRATCH_DB],
                   env=env, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=60)


@pytest.fixture
def source_counts(db):
    """row counts from the live test database, used as restore oracle"""
    counts = {}
    for table in ("admins", "admin_perms", "ibs_states"):
        res = db.query("select count(*) from %s" % table)
        counts[table] = int(res.getresult()[0][0])
    return counts


def _verify_restored(env, counts):
    for table, expected in counts.items():
        got = _query(SCRATCH_DB, "select count(*) from %s" % table, env)
        assert got == str(expected), \
            "table %s: restored %s rows, source has %s" % (table, got, expected)


def test_restore_never_touches_source_db(db):
    """guard: the scratch database name must not collide with the live one"""
    assert SCRATCH_DB != DB_CONF["dbname"]


def test_backup_restore_roundtrip(db, source_counts, tmp_path):
    env = _base_env(DB_CONF["dbname"])
    dump = str(tmp_path / "ibs_backup.sql")

    proc = _run(_script("backup_ibs"), env, dump)
    assert proc.returncode == 0, proc.stderr
    assert os.path.getsize(dump) > 0
    with open(dump) as fd:
        body = fd.read()
    assert "CREATE TABLE" in body
    assert "insert into admins" in body.lower() or \
        "COPY public.admins" in body or "COPY admins" in body

    scratch_env = _base_env(SCRATCH_DB)
    _drop_scratch(scratch_env)
    try:
        proc = _run(_script("restore_ibs"), scratch_env, dump)
        assert proc.returncode == 0, proc.stderr + proc.stdout
        assert "completed successfully" in proc.stdout
        _verify_restored(scratch_env, source_counts)
    finally:
        _drop_scratch(scratch_env)


def test_backup_restore_roundtrip_gzip(db, source_counts, tmp_path):
    env = _base_env(DB_CONF["dbname"])
    dump = str(tmp_path / "ibs_backup.sql.gz")

    proc = _run(_script("backup_ibs"), env, dump)
    assert proc.returncode == 0, proc.stderr
    # the file must really be gzip-compressed
    with open(dump, "rb") as fd:
        assert fd.read(2) == b"\x1f\x8b"

    scratch_env = _base_env(SCRATCH_DB)
    _drop_scratch(scratch_env)
    try:
        proc = _run(_script("restore_ibs"), scratch_env, dump)
        assert proc.returncode == 0, proc.stderr + proc.stdout
        _verify_restored(scratch_env, source_counts)
    finally:
        _drop_scratch(scratch_env)


def test_backup_requires_argument():
    proc = _run(_script("backup_ibs"), _base_env(DB_CONF["dbname"]))
    assert proc.returncode != 0
    assert "Usage:" in proc.stdout + proc.stderr


def test_backup_rejects_bad_db_name(tmp_path):
    env = _base_env("IBSng; rm -rf /")
    proc = _run(_script("backup_ibs"), env, str(tmp_path / "x.sql"))
    assert proc.returncode != 0
    assert "invalid database name" in proc.stderr
    assert not os.path.exists(str(tmp_path / "x.sql"))


def test_restore_missing_file():
    proc = _run(_script("restore_ibs"), _base_env(DB_CONF["dbname"]),
                "/nonexistent/backup.sql")
    assert proc.returncode != 0
    assert "not found" in proc.stderr


def test_restore_reports_failure_on_broken_dump(db, tmp_path):
    """a broken dump must fail loudly and never claim success"""
    broken = tmp_path / "broken.sql"
    broken.write_text("this is not valid sql;\n")
    env = _base_env(SCRATCH_DB)
    _drop_scratch(env)
    try:
        proc = _run(_script("restore_ibs"), env, str(broken))
        assert proc.returncode != 0
        assert "completed successfully" not in proc.stdout
    finally:
        _drop_scratch(env)


def test_restore_strips_transaction_timeout_but_keeps_copy_data(tmp_path):
    """
    pg_dump >= 18 writes "SET transaction_timeout = 0;" which servers <= 16
    reject.  The restore filter must drop that SET line while preserving a
    COPY data row that happens to start with the very same text.
    """
    probe = tmp_path / "probe.sql"
    probe.write_text(
        "CREATE TABLE public.backup_filter_probe (v text);\n"
        "SET transaction_timeout = 0;\n"
        "COPY public.backup_filter_probe FROM stdin;\n"
        "SET transaction_timeout = 999;\n"
        "\\.\n"
        "SET transaction_timeout = 0;\n"
        "GRANT ALL ON public.backup_filter_probe TO public;\n")
    env = _base_env(SCRATCH_DB)
    _drop_scratch(env)
    try:
        proc = _run(_script("restore_ibs"), env, str(probe))
        assert proc.returncode == 0, proc.stderr + proc.stdout
        row = _query(SCRATCH_DB, "select v from public.backup_filter_probe", env)
        assert row == "SET transaction_timeout = 999;"
    finally:
        _drop_scratch(env)
