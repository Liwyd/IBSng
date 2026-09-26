"""
Schema baseline: the db/*.sql files must load cleanly on modern PostgreSQL
and seed the objects IBSng needs. This runs against whatever server the
test environment provides (PostgreSQL 16+ targeted, 9.2+ supported).
"""
import pytest

REQUIRED_TABLES = [
    "users", "normal_users", "voip_users", "user_attrs",
    "admins", "admin_perms", "admin_locks", "user_audit_log",
    "connection_log", "connection_log_details",
    "defs", "ibs_states",
    "ras", "ras_ports", "ras_attrs", "ras_ippools",
    "charges", "charge_rules", "internet_charge_rules",
    "charge_rule_ports", "charge_rule_day_of_weeks",
    "groups", "group_attrs",
    "ippool", "ippool_ips",
    "credit_change", "credit_change_userid",
    "internet_bw_snapshot", "internet_onlines_snapshot",
    "ias_event",
    "user_messages", "admin_messages", "add_user_saves", "add_user_save_details",
]

REQUIRED_FUNCTIONS = [
    "add_user",
    "change_user_credit",
    "insert_connection_log",
    "insert_user_attr",
    "update_user_attr",
    "delete_user_attr",
]


# catalog relation, name column, and how to scope to the public schema
_CATALOG = {
    "tables": ("pg_tables", "tablename", "schemaname='public'"),
    "functions": ("pg_proc", "proname",
                  "pronamespace = (select oid from pg_namespace where nspname='public')"),
}


def _relation_exists(db, kind, name):
    relation, column, scope = _CATALOG[kind]
    res = db.query(
        "select 1 from pg_catalog.%s where %s and %s='%s'"
        % (relation, scope, column, name))
    return len(res.getresult()) == 1


@pytest.mark.parametrize("table", REQUIRED_TABLES)
def test_required_table_exists(db, table):
    assert _relation_exists(db, "tables", table), "missing table: %s" % table


@pytest.mark.parametrize("function", REQUIRED_FUNCTIONS)
def test_required_function_exists(db, function):
    assert _relation_exists(db, "functions", function), "missing function: %s" % function


def test_seed_admin_exists(db):
    rows = db.query("select admin_id, username from admins").getresult()
    assert (0, "system") in [(r[0], r[1]) for r in rows], \
        "initial.sql must seed admin_id=0 'system'"


def test_seed_god_perm_exists(db):
    rows = db.query("select count(*) from admin_perms where perm_name='GOD'").getresult()
    assert rows[0][0] >= 1


def test_ibs_states_seeded(db):
    # daily/lowload jobs must have state rows so startup checks work
    rows = db.query("select name from ibs_states").getresult()
    names = [r[0] for r in rows]
    assert "MIDNIGHT_JOBS" in names and "LOWLOAD_JOBS" in names
