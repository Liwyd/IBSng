#!/usr/bin/env python3
"""
defs2sql.py: convert an IBSng defs python file to a SQL script.

Usage: defs2sql.py <-i|-u> <python_file.py> <sql_file.sql>
       -i : use insert queries (fresh install)
       -u : use update queries  (upgrade)

       python_file.py : defs variables in python format
       sql_file.sql   : sql script to be created

The generated statements must stay loadable on PostgreSQL >= 9.1 and the
pickled values must stay loadable by core.defs_lib.def_loader (protocol 0,
ASCII-only text), so this tool pickles with protocol 0 and escapes through
core.lib.sql_escape.dbText - the same escaping the runtime uses.
"""
import importlib.util
import os
import pickle
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.lib.sql_escape import dbText


def loadDefs(python_file):
    """
        import "python_file" and return {def_name: def_value} for every
        module level definition that does not start with "__"
    """
    if not python_file.endswith(".py"):
        raise SystemExit("defs2sql.py: python modules should be .py")
    spec = importlib.util.spec_from_file_location("ibs_defs_source", python_file)
    if spec is None or spec.loader is None:
        raise SystemExit("defs2sql.py: can not load %s" % python_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return dict((name, value) for name, value in vars(module).items()
                if not name.startswith("__") and not callable(value))


def pickledText(value):
    """
        protocol 0 pickle of "value" as ASCII text - safe for a text column
        and round-trips through pickle.loads on python 3
    """
    return pickle.dumps(value, 0).decode("ascii")


def getInsertQuery(defs):
    return "".join("insert into defs (name,value) VALUES (%s,%s) ;\n" %
                   (dbText(name), dbText(pickledText(value)))
                   for name, value in sorted(defs.items()))


def getUpdateQuery(defs):
    return "".join("update defs set value = %s where name = %s ;\n" %
                   (dbText(pickledText(value)), dbText(name))
                   for name, value in sorted(defs.items()))


def printUsage():
    print(__doc__)


def main():
    if len(sys.argv) != 4 or (sys.argv[1] != "-i" and sys.argv[1] != "-u"):
        printUsage()
        sys.exit(1)
    defs = loadDefs(sys.argv[2])
    if sys.argv[1] == "-i":
        query = getInsertQuery(defs)
    else:
        query = getUpdateQuery(defs)
    with open(sys.argv[3], "w") as fd:
        fd.write(query)


if __name__ == "__main__":
    main()
