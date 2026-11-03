"""Generated projects pull later template releases: `copier update`, and the
weekly workflow (.github/workflows/template-update.yml) that runs it."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import copier
import pytest
import yaml

from tests.conftest import BASE_ANSWERS, TEMPLATE_ROOT, run


def _commit(repo: Path, message: str, tag: str | None = None) -> None:
    run(["git", "add", "-A"], cwd=repo)
    run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", message], cwd=repo)
    if tag:
        run(["git", "tag", tag], cwd=repo)


@pytest.fixture
def released(tmp_path) -> tuple[Path, Path]:
    """A copy of the template released as v1.0.0, and a project generated from it."""
    template = tmp_path / "template"
    shutil.copytree(
        TEMPLATE_ROOT,
        template,
        ignore=shutil.ignore_patterns(".git", ".venv", "*cache*", "__pycache__"),
    )
    run(["git", "init", "-q"], cwd=template)
    _commit(template, "v1", tag="v1.0.0")

    project = tmp_path / "project"
    copier.run_copy(str(template), project, data=BASE_ANSWERS, defaults=True, quiet=True)
    run(["git", "init", "-q"], cwd=project)
    _commit(project, "generated")
    return template, project


def _release_v2(template: Path) -> None:
    agents = template / "_project_template/AGENTS.md.jinja"
    agents.write_text(agents.read_text() + "- A convention added in v2.\n")
    _commit(template, "v2", tag="v2.0.0")


def test_copier_update(released):
    template, project = released
    _release_v2(template)

    copier.run_update(project, defaults=True, quiet=True, overwrite=True)
    assert "A convention added in v2." in (project / "AGENTS.md").read_text()
    changed = run(["git", "status", "--porcelain"], cwd=project).stdout.split("\n")
    assert sorted(line[3:] for line in changed if line) == [".copier-answers.yml", "AGENTS.md"]


def test_untagged_changes_are_not_pulled(released):
    """Why the template auto-releases: `copier update` follows tags, not main."""
    template, project = released
    agents = template / "_project_template/AGENTS.md.jinja"
    agents.write_text(agents.read_text() + "- Merged but never tagged.\n")
    _commit(template, "untagged")

    copier.run_update(project, defaults=True, quiet=True, overwrite=True)
    assert "never tagged" not in (project / "AGENTS.md").read_text()


def _run_pull_step(project: Path, tmp_path: Path) -> dict[str, str]:
    """Run the workflow's "Pull the latest template" step as Actions would, with
    `uvx copier` served by this environment's copier instead of the network."""
    workflow = yaml.safe_load((project / ".github/workflows/template-update.yml").read_text())
    step = next(s for s in workflow["jobs"]["update"]["steps"] if s.get("id") == "copier")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    uvx = bin_dir / "uvx"
    uvx.write_text(f'#!/bin/sh\nshift\nexec "{sys.executable}" -m copier "$@"\n')
    uvx.chmod(0o755)

    output = tmp_path / "github_output"
    output.touch()
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "GITHUB_OUTPUT": str(output),
        "RUNNER_TEMP": str(tmp_path),
    }
    result = subprocess.run(
        ["bash", "-e", "-c", step["run"]],
        check=False,
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return dict(line.split("=", 1) for line in output.read_text().splitlines())


def test_workflow_pulls_new_release(released, tmp_path):
    template, project = released
    _release_v2(template)

    outputs = _run_pull_step(project, tmp_path)
    assert outputs == {"from": "v1.0.0", "to": "v2.0.0", "conflicts": "false"}
    assert "A convention added in v2." in (project / "AGENTS.md").read_text()


def test_workflow_flags_conflicts(released, tmp_path):
    """A line changed in both the project and the template is left for a person."""
    template, project = released
    for path, line in [
        (project / "CHANGES.md", "- Project's own first entry."),
        (template / "_project_template/CHANGES.md.jinja", "- Template's new first entry."),
    ]:
        path.write_text(
            path.read_text().replace("- Project generated from SpiriProjectTemplates.", line)
        )
    _commit(project, "local edit")
    _commit(template, "v2", tag="v2.0.0")

    outputs = _run_pull_step(project, tmp_path)
    assert outputs["conflicts"] == "true"
    assert (tmp_path / "conflicts").read_text().split() == ["CHANGES.md"]
