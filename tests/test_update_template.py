"""scripts/update_template.py's rewriting, offline: the lookups are stubbed."""

from __future__ import annotations

import shutil

import pytest

from scripts import update_template as ut
from tests.conftest import TEMPLATE_ROOT

PYPI = {"loguru": "0.8.1", "nicegui": "3.14.0", "uv": "0.11.3", "ruff": "0.20.0"}
GITHUB = {"actions/checkout": "5.0.1", "astral-sh/setup-uv": "6.4.0", "rhysd/actionlint": "1.8.0"}

# For whole-template runs: newer than anything the template will ever pin, so
# the weekly bumps can't overtake these tests.
FUTURE_PYPI = {"loguru": "99.0.1", "uv": "99.11.3"}
FUTURE_GITHUB = {"actions/checkout": "99.0.1", "rhysd/actionlint": "99.0.0"}


def test_requirements_bumped_only_when_newer():
    text = '    "loguru>=0.7.3",\n    "nicegui>=3.14.0",\n    "uvicorn[standard]>=0.1",\n'
    new, changes = ut.bump_requirements(text, {**PYPI, "uvicorn": "0.40.0"}.__getitem__)
    assert '"loguru>=0.8.1"' in new
    assert '"nicegui>=3.14.0"' in new
    assert '"uvicorn[standard]>=0.40.0"' in new
    assert changes == [("loguru", "0.7.3", "0.8.1"), ("uvicorn", "0.1", "0.40.0")]


def test_requires_python_untouched():
    text = 'requires-python = ">=3.13"\n'
    assert ut.bump_requirements(text, PYPI.__getitem__) == (text, [])


def test_actions_bumped_to_latest_major():
    text = "      - uses: actions/checkout@v4\n      - uses: astral-sh/setup-uv@v6\n"
    new, changes = ut.bump_actions(text, GITHUB.__getitem__)
    assert "actions/checkout@v5" in new
    assert "astral-sh/setup-uv@v6" in new
    assert changes == [("actions/checkout", "v4", "v5")]


def test_uv_image_keeps_major_minor():
    text = "COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv\n"
    new, changes = ut.bump_pattern(
        text, ut.UV_IMAGE, "uv image", "0.11.3", lambda v: f"{v.major}.{v.minor}"
    )
    assert "ghcr.io/astral-sh/uv:0.11 /uv" in new
    assert changes == [("uv image", "0.9", "0.11")]


@pytest.fixture
def stubbed(monkeypatch):
    monkeypatch.setattr(ut, "latest_pypi", lambda name: FUTURE_PYPI.get(name, "0.0.1"))
    monkeypatch.setattr(ut, "latest_github", lambda repo: FUTURE_GITHUB.get(repo, "1.0.0"))


def test_update_rewrites_the_template(tmp_path, stubbed):
    root = tmp_path / "repo"
    shutil.copytree(
        TEMPLATE_ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", "*cache*", "__pycache__"),
    )
    changes = ut.update(root)

    assert '"loguru>=99.0.1"' in (root / "_project_template/pyproject.toml.jinja").read_text()
    assert "ghcr.io/astral-sh/uv:99.11 " in next(root.glob(ut.DOCKERFILE_GLOB)).read_text()
    template_ci = (root / ".github/workflows/test-template.yml").read_text()
    assert "actions/checkout@v99" in template_ci
    assert 'ACTIONLINT_VERSION: "99.0.0"' in template_ci
    # The Python base image is a deliberate upgrade, never bumped.
    assert "FROM python:3.14-slim" in next(root.glob(ut.DOCKERFILE_GLOB)).read_text()
    # Reported once, though checkout is pinned in several workflows.
    assert len([c for c in changes if c[0] == "actions/checkout"]) == 1
    assert "| `loguru` |" in ut.summarize(changes)


def test_update_is_idempotent(tmp_path, stubbed):
    root = tmp_path / "repo"
    shutil.copytree(
        TEMPLATE_ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", "*cache*", "__pycache__"),
    )
    ut.update(root)
    assert ut.update(root) == []
