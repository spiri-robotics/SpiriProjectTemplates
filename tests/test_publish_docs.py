"""The generated projects' .github/scripts/publish_docs.py: the versioned docs site.

The script is copied into projects verbatim, so it's loaded straight from the
template rather than from a generated project.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

from tests.conftest import TEMPLATE_ROOT, generate

SCRIPT = (
    TEMPLATE_ROOT
    / "_project_template/.github/[% if include_docs %]scripts[% endif %]/publish_docs.py"
)
_spec = importlib.util.spec_from_file_location("publish_docs", SCRIPT)
pd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pd)


@pytest.fixture
def site(tmp_path):
    site = tmp_path / "site"
    site.mkdir()
    return site


def publish(site: Path, version: str, *, pages=("index.html",), pdf=True) -> None:
    """Publish a fake build of *version*: each page says which version it is."""
    build = site.parent / f"build-{version}"
    build.mkdir()
    for page in pages:
        (build / page).parent.mkdir(parents=True, exist_ok=True)
        (build / page).write_text(version)
    pdf_file = None
    if pdf:
        pdf_file = site.parent / f"DOC-001_rev{version}.pdf"
        pdf_file.write_text("%PDF")
    pd.publish(site, version, build, pdf_file)


def versions(site: Path) -> dict:
    return json.loads((site / "versions.json").read_text())


def test_dev_is_latest_until_a_release(site):
    publish(site, "dev")

    assert versions(site) == {
        "latest": "dev",
        "versions": [{"name": "dev", "path": "dev/", "pdf": "dev/DOC-001_revdev.pdf"}],
    }
    assert (site / "latest/index.html").read_text() == "dev"
    assert (site / "latest/DOC-001_revdev.pdf").is_file()


def test_newest_release_is_latest_whatever_the_order_published(site):
    publish(site, "dev")
    publish(site, "v0.10.0")
    publish(site, "v0.9.0")  # e.g. a docs fix on an old release, published after

    data = versions(site)
    assert data["latest"] == "v0.10.0"
    assert [v["name"] for v in data["versions"]] == ["v0.10.0", "v0.9.0", "dev"]
    assert (site / "latest/index.html").read_text() == "v0.10.0"


def test_a_pre_release_is_published_but_never_latest(site):
    publish(site, "v1.0.0")
    publish(site, "v1.1.0-rc1")

    data = versions(site)
    assert data["latest"] == "v1.0.0"
    assert [v["name"] for v in data["versions"]] == ["v1.1.0-rc1", "v1.0.0"]

    publish(site, "v1.1.0")
    assert versions(site)["latest"] == "v1.1.0"
    assert [v["name"] for v in versions(site)["versions"]] == ["v1.1.0", "v1.1.0-rc1", "v1.0.0"]


def test_republishing_replaces_the_version_and_leaves_the_others(site):
    publish(site, "v0.1.0", pages=("index.html", "old.html"))
    publish(site, "dev", pages=("index.html", "old.html"))
    (site.parent / "build-dev").rename(site.parent / "build-dev-1")
    publish(site, "dev", pages=("index.html",))

    assert not (site / "dev/old.html").exists()
    assert (site / "v0.1.0/old.html").is_file()
    assert (site / "latest/old.html").is_file()  # latest is v0.1.0, untouched


def test_a_version_without_a_pdf(site):
    publish(site, "dev", pdf=False)
    assert versions(site)["versions"][0]["pdf"] is None


def test_root_pages(site):
    publish(site, "dev")

    assert 'url=latest/"' in (site / "index.html").read_text()
    assert (site / ".nojekyll").exists()
    # The 404 page knows every published version, to tell an old link from a missing page.
    assert '["latest", "dev"].includes(first)' in (site / "404.html").read_text()


@pytest.mark.parametrize("version", ["main", "1.0.0", "v1.0", "latest", "../x", "v1.0.0/x"])
def test_rejects_anything_but_a_release_or_dev(site, version):
    build = site.parent / "build"
    build.mkdir()
    with pytest.raises(ValueError):
        pd.publish(site, version, build)
    assert not any(site.iterdir())


class TestTheWorkflowStep:
    """The publish step's shell, run for real against a local remote."""

    @pytest.fixture
    def repo(self, tmp_path):
        """A generated project's clone, with a bare origin that has no gh-pages yet."""
        project = generate(tmp_path / "project", kind="library", spirisynq=False)
        env = self.env(tmp_path)
        origin = tmp_path / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", origin], check=True, env=env)
        for args in (
            ["init", "-q", "-b", "main"],
            ["add", "-A"],
            ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
            ["remote", "add", "origin", f"file://{origin}"],
            ["push", "-q", "origin", "main"],
        ):
            subprocess.run(["git", *args], cwd=project, check=True, env=env)
        return project

    @staticmethod
    def env(tmp_path: Path, **extra) -> dict:
        # The step sets a git identity with --global: keep that out of the real one.
        home = tmp_path / "home"
        home.mkdir(exist_ok=True)
        return {**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home), **extra}

    def run_step(self, repo: Path, ref_type: str, ref_name: str, content: str) -> None:
        tmp_path = repo.parent
        workflow = yaml.safe_load((repo / ".github/workflows/docs.yml").read_text())
        steps = workflow["jobs"]["publish"]["steps"]
        script = next(s["run"] for s in steps if "publish_docs.py" in s.get("run", ""))
        temp = tmp_path / f"runner-{ref_name}-{content}"
        (temp / "html").mkdir(parents=True)
        (temp / "html/index.html").write_text(content)
        (temp / "DOC.pdf").write_text("%PDF")
        env = self.env(
            tmp_path,
            GITHUB_REF_TYPE=ref_type,
            GITHUB_REF_NAME=ref_name,
            GITHUB_SHA="abc123",
            RUNNER_TEMP=str(temp),
            HTML=str(temp / "html"),
            PDF=str(temp / "DOC.pdf"),
        )
        # How Actions runs a `run:` step.
        subprocess.run(["bash", "-e", "-c", script], cwd=repo, check=True, env=env)
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(temp / "site")],
            cwd=repo,
            check=True,
            env=env,
        )

    def published(self, repo: Path, path: str) -> str:
        return subprocess.run(
            ["git", "--git-dir", str(repo.parent / "origin.git"), "show", f"gh-pages:{path}"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    def test_creates_the_branch_then_adds_to_it(self, repo):
        self.run_step(repo, "branch", "main", "first")
        assert self.published(repo, "dev/index.html") == "first"
        assert json.loads(self.published(repo, "versions.json"))["latest"] == "dev"

        self.run_step(repo, "tag", "v1.0.0", "release")
        assert self.published(repo, "v1.0.0/DOC.pdf") == "%PDF"
        assert self.published(repo, "latest/index.html") == "release"
        assert self.published(repo, "dev/index.html") == "first"

    def test_publishing_the_same_build_again_succeeds(self, repo):
        self.run_step(repo, "branch", "main", "same")
        (repo.parent / "runner-main-same").rename(repo.parent / "runner-main-same-1")
        self.run_step(repo, "branch", "main", "same")
        assert self.published(repo, "dev/index.html") == "same"
