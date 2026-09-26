"""
SQL text escaping (core.lib.sql_escape).

Guards two historic pitfalls:
  - quoting must work with standard_conforming_strings=on (modern default)
  - backslashes must NOT be doubled (the old escapeSlashes corrupted them)
Also pins the long-standing escapeTags() HTML-stripping behavior.
"""
from core.lib.sql_escape import dbText, escapeSlashes, escapeStr, escapeTags


def test_quote_doubling():
    assert dbText("it's") == "'it''s'"
    assert dbText("a'b'c") == "'a''b''c'"
    assert dbText("'") == "''''"


def test_backslash_not_doubled():
    """
        regression: the pre-modern implementation returned 'a\\\\b' here,
        which PostgreSQL >= 9.1 stores as TWO backslashes
    """
    assert dbText("a\\b") == "'a\\b'"
    assert dbText("C:\\path\\to\\x") == "'C:\\path\\to\\x'"
    assert escapeSlashes("a\\b") == "a\\b"


def test_non_string_values():
    assert dbText(123) == "'123'"
    assert dbText(45.25) == "'45.25'"
    assert dbText(None) == "'None'"  # historic behavior: None -> 'None'
    assert dbText(True) == "'True'"


def test_bytes_latin1():
    assert dbText(b"plain") == "'plain'"
    # latin-1 preserves raw bytes 1:1
    assert dbText(b"\xe9") == "'\xe9'"


def test_escape_tags_strips_html_except_br():
    assert escapeTags("hello <b>world</b>") == "hello  - b - world - /b - "
    assert escapeTags("line<br>next") == "line<br>next"
    assert escapeTags("line<br />next") == "line<br />next"
    # only bare <br> and <br /> survive; <br/> is stripped (historic regex)
    assert escapeTags("line<br/>next") == "line - br/ - next"
    assert "<script>" not in escapeTags("<script>alert(1)</script>hi")


def test_combined():
    assert dbText("O'Brien's \"path\"") == "'O''Brien''s \"path\"'"
    assert dbText("multi\nline\tvalue") == "'multi\nline\tvalue'"


def test_roundtrip_through_postgres(dbtx):
    """
        actual proof against the live server: what we write is what we read
    """
    dbtx.query("create temp table esc_roundtrip (v text)")
    samples = [
        "plain",
        "it's a 'quoted' value",
        "back\\slash\\and\\more",
        "new\nline\r\ntab\there",
        "unicode: \u00e9\u03b1\u20ac",
        "mixed ' \\ \n end",
    ]
    for i, sample in enumerate(samples):
        dbtx.query("insert into esc_roundtrip values (%s)" % dbText(sample))
    rows = [r[0] for r in dbtx.query(
        "select v from esc_roundtrip").getresult()]
    assert rows == samples
