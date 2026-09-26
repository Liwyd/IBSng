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
