"""
Installer smoke tests (phase 6): the script must parse, expose its CLI, and
refuse to run unprivileged. The full provisioning path runs in the P7 CI
container (root, ubuntu:24.04); here we also verify the embedded admin
password-hash step against the real repository tree.
"""
import os
import subprocess
import sys

import pytest

from tests.conftest import REPO_ROOT

INSTALL_SH = os.path.join(REPO_ROOT, "install.sh")


def run(*args):
    return subprocess.run(["bash", INSTALL_SH] + list(args),
                          capture_output=True, text=True, timeout=30)


def test_install_sh_syntax():
    proc = subprocess.run(["bash", "-n", INSTALL_SH],
                          capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr


def test_help_exits_zero():
    proc = run("--help")
    assert proc.returncode == 0
    assert "usage: install.sh" in proc.stdout
    assert "--yes" in proc.stdout


def test_unknown_argument_rejected():
    proc = run("--bogus")
    assert proc.returncode != 0
    assert "unknown argument" in proc.stderr


@pytest.mark.skipif(os.geteuid() == 0, reason="running as root")
def test_refuses_non_root():
    proc = run()
    assert proc.returncode == 1
    assert "root" in proc.stderr


def test_admin_password_hash_step():
    # same invocation the installer uses after copy_tree
    script = (
        "import sys\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "import os\n"
        "from core.lib import password_lib\n"
        "print(password_lib.Password(os.environ['IBS_ADMIN_PASSWORD']).getMd5Crypt())\n"
    )
    env = dict(os.environ, IBS_ADMIN_PASSWORD="s3cret")
    proc = subprocess.run([sys.executable, "-", REPO_ROOT],
                          input=script, capture_output=True, text=True,
                          env=env, timeout=30)
    assert proc.returncode == 0, proc.stderr
    hash_value = proc.stdout.strip()
    assert hash_value.startswith("$1$")
    # and it verifies against the plaintext (this is what the web login does)
    verify = (
        "import sys\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "from core.lib import password_lib\n"
        "assert password_lib.Password('s3cret') == password_lib.Password(%r)\n"
        "print('OK')\n" % hash_value
    )
    proc = subprocess.run([sys.executable, "-", REPO_ROOT],
                          input=verify, capture_output=True, text=True,
                          timeout=30)
    assert proc.stdout.strip() == "OK", proc.stderr


def test_help_lists_uninstall_flags():
    proc = run("--help")
    assert proc.returncode == 0
    for flag in ("--uninstall", "--keep-db", "--purge-packages"):
        assert flag in proc.stdout


@pytest.mark.skipif(os.geteuid() == 0, reason="running as root")
def test_uninstall_refuses_non_root():
    proc = run("--uninstall")
    assert proc.returncode == 1
    assert "root" in proc.stderr


def test_uninstall_is_a_full_purge():
    # lock the destructive pieces in place: the purge must cover engine,
    # unit, cron, web config, firewall, tree, credentials and the database
    with open(INSTALL_SH) as fh:
        script = fh.read()
    for needle in (
        "drop database if exists",      # database goes (unless --keep-db)
        "drop role if exists ibs",
        "a2disconf ibsng",              # web config
        "rm -f /etc/cron.d/ibsng-openvpn-interim",
        "rm -f /etc/systemd/system/ibsng.service",
        'pkill -f "${PREFIX}/ibs[.]py"',
        "rm -rf /var/log/IBSng /etc/ibsng",
        "ufw --force delete allow",     # firewall rules
        'rm -rf "$PREFIX"',
        "apt-get purge",                # only behind --purge-packages
    ):
        assert needle in script, needle
    # the DB drop must be skippable, package purge must be opt-in
    assert 'if [ "$KEEP_DB" -eq 1 ]' in script
    assert 'if [ "$PURGE_PKGS" -eq 1 ]' in script
    # run_uninstall runs before any interactive prompt and exits immediately
    assert script.index("run_uninstall") < script.index("Proceed with full uninstall")
    dispatch = 'if [ "$UNINSTALL" -eq 1 ]; then\n    run_uninstall\n    exit $?\nfi'
    assert dispatch in script
    # dispatch must come before the interactive prompts, not after
    assert script.index(dispatch) < script.index("# ---------------------------------------------------------------- prompts")


def test_copy_tree_permission_guards():
    # mktemp creates the clone dir 0700 and rsync -a propagates the mode
    # to $PREFIX top dir; without normalization www-data cannot traverse
    # the tree and every /IBSng URL returns 403 (AH00035).
    with open(INSTALL_SH) as fh:
        script = fh.read()
    assert 'chmod 755 "$TMP_CLONE"' in script
    assert 'chmod -R u=rwX,go=rX "$PREFIX"' in script
    # normalization must run before the explicit executable bits are set
    assert script.index('chmod -R u=rwX,go=rX "$PREFIX"') < \
        script.index('chmod 755 "$PREFIX/ibs.py"')
