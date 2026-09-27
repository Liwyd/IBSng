"""
Phase 7 delivery artifacts: the container entrypoint must parse, the compose
file must expose exactly the app+db scope with sane settings, and the CI
workflow must stay valid YAML. These are static checks; the real container
path is exercised by .github/workflows/ci.yml (container e2e job).
"""
import os
import subprocess

import pytest

from tests.conftest import REPO_ROOT

yaml = pytest.importorskip("yaml")


def test_entrypoint_syntax():
    proc = subprocess.run(["bash", "-n", os.path.join(REPO_ROOT, "docker/entrypoint.sh")],
                          capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr


def test_entrypoint_executable():
    path = os.path.join(REPO_ROOT, "docker/entrypoint.sh")
    assert os.access(path, os.X_OK)


def test_compose_scope_and_settings():
    with open(os.path.join(REPO_ROOT, "docker-compose.yml")) as fh:
        compose = yaml.safe_load(fh)
    assert set(compose["services"]) == {"db", "ibsng"}
    db = compose["services"]["db"]
    app = compose["services"]["ibsng"]
    assert db["image"].startswith("postgres:")
    assert "healthcheck" in db
    assert app["depends_on"]["db"]["condition"] == "service_healthy"
    env = app["environment"]
    assert env["IBS_DB_HOST"] == "db"
    assert env["IBS_DB_SUPERUSER"] == "postgres"
    ports = set(app["ports"])
    assert "80:80" in ports
    assert "1812:1812/udp" in ports
    assert "1813:1813/udp" in ports


def test_dockerfile_basics():
    with open(os.path.join(REPO_ROOT, "Dockerfile")) as fh:
        dockerfile = fh.read()
    assert "FROM ubuntu:24.04" in dockerfile
    assert "ENTRYPOINT" in dockerfile
    assert "EXPOSE 80 1812/udp 1813/udp" in dockerfile
    assert "HEALTHCHECK" in dockerfile


def test_ci_workflow_valid():
    with open(os.path.join(REPO_ROOT, ".github/workflows/ci.yml")) as fh:
        workflow = yaml.safe_load(fh)
    assert "jobs" in workflow
    assert set(workflow["jobs"]) == {"test", "container"}
    steps = workflow["jobs"]["test"]["steps"]
    names = [s.get("name", "") for s in steps]
    assert any("pytest" in n for n in names)
    assert any("php lint" in n for n in names)
    assert any("installer" in n for n in names)
