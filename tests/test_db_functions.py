"""
Golden tests for the SQL functions the accounting engine depends on.

These pin down the exact semantics existing IBSng releases rely on:
  - change_user_credit applies a *relative* credit change (called exactly
    once per logout by the engine - it is deliberately not idempotent)
  - insert_connection_log writes one connection_log row plus name/value
    details (bytes_in / bytes_out / ...) as TEXT

Everything runs inside a rolled-back transaction.
"""


def _add_user(dbtx, user_id, credit):
    dbtx.query("select add_user(%d, %s, 0, 0)" % (user_id, credit))


def _insert_connection_log(dbtx, user_id, credit, login_time, logout_time,
                           successful, service, ras_id, names, values):
    """
        call insert_connection_log with explicit casts - integer literals do
        not implicitly match the smallint parameter of the function
    """
    names_sql = "array[%s]::text[]" % ",".join(
        "'%s'" % n.replace("'", "''") for n in names)
    values_sql = "array[%s]::text[]" % ",".join(
        "'%s'" % v.replace("'", "''") for v in values)
    dbtx.query(
        "select insert_connection_log(%d::bigint, %s::numeric, "
        "'%s'::timestamp, '%s'::timestamp, %s::boolean, "
        "%d::smallint, %d::integer, %s, %s)" %
        (user_id, credit, login_time, logout_time,
         "true" if successful else "false", service, ras_id,
         names_sql, values_sql))


def _credit(dbtx, user_id):
    return dbtx.query("select credit from users where user_id=%d" % user_id).getresult()[0][0]


def test_change_user_credit_is_relative(dbtx):
    _add_user(dbtx, 9001, "100.00")
    assert float(_credit(dbtx, 9001)) == 100.0

    dbtx.query("select change_user_credit(9001, -30.00)")
    assert float(_credit(dbtx, 9001)) == 70.0

    # second application deducts again: callers must invoke it exactly once
    dbtx.query("select change_user_credit(9001, -30.00)")
    assert float(_credit(dbtx, 9001)) == 40.0

    # negative (top-up) direction works too
    dbtx.query("select change_user_credit(9001, 10.00)")
    assert float(_credit(dbtx, 9001)) == 50.0


def test_change_user_credit_rounds_to_cents(dbtx):
    _add_user(dbtx, 9003, "10.00")
    dbtx.query("select change_user_credit(9003, -0.005)")
    assert float(_credit(dbtx, 9003)) == 9.99 or float(_credit(dbtx, 9003)) == 10.00


def test_insert_connection_log(dbtx):
    _add_user(dbtx, 9002, "0.00")
    _insert_connection_log(dbtx, 9002, "1.50",
                           "2026-01-01 10:00:00", "2026-01-01 10:30:00",
                           True, 1, 1,
                           ["username", "bytes_in", "bytes_out"],
                           ["testuser", "100", "200"])

    logs = dbtx.query(
        "select connection_log_id, credit_used, successful, service, ras_id "
        "from connection_log where user_id=9002").getresult()
    assert len(logs) == 1
    log_id, credit_used, successful, service, ras_id = logs[0]
    assert float(credit_used) == 1.5
    assert successful in (True, "t", "true")  # driver bool representation varies
    assert service == 1
    assert ras_id == 1

    details = dict(dbtx.query(
        "select name, value from connection_log_details where connection_log_id=%d"
        % log_id).getresult())
    assert details == {"username": "testuser", "bytes_in": "100", "bytes_out": "200"}
    # details are stored as TEXT exactly as supplied
    assert details["bytes_in"] == "100"


def test_connection_log_times_roundtrip(dbtx):
    _add_user(dbtx, 9004, "0.00")
    _insert_connection_log(dbtx, 9004, "0",
                           "2026-06-15 08:30:00", "2026-06-15 09:45:00",
                           True, 1, 1, ["x"], ["y"])
    row = dbtx.query(
        "select login_time, logout_time from connection_log where user_id=9004"
    ).getresult()[0]
    login_time, logout_time = row
    # the driver returns timestamps as text (the engine treats them as text
    # too, e.g. dbTimeFromEpoch()); duration must survive exactly: 75 minutes
    from datetime import datetime
    fmt = "%Y-%m-%d %H:%M:%S"
    duration = (datetime.strptime(logout_time, fmt) -
                datetime.strptime(login_time, fmt))
    assert duration.total_seconds() == 75 * 60
