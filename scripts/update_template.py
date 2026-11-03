"""Bump every version the template ships to the latest release.

Generated projects get these through `copier update`, so the template is where
dependency updates happen, not in each project. Run weekly by
.github/workflows/update-template.yml, which then tests the result and opens a PR.

What it bumps:

- `name>=X` lower bounds in pyproject.toml files (latest release on PyPI)
- `uses: owner/repo@vN` in workflows (latest release's major version)
- the `ghcr.io/astral-sh/uv:X.Y` image in the Dockerfile (latest uv)
- `ACTIONLINT_VERSION` in the template's CI (latest actionlint)

Deliberately not the Python base image or `requires-python`: a new Python is an
upgrade to decide on, not a routine bump.

    uv run python scripts/update_template.py [--summary PATH]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from collections.abc import Callable
from functools import cache
from pathlib import Path

from packaging.version import Version

ROOT = Path(__file__).resolve().parent.parent

PYPROJECTS = ["_project_template/pyproject.toml.jinja", "pyproject.toml"]
WORKFLOW_DIRS = ["_project_template/.github/workflows", ".github/workflows"]
# Found rather than listed: their directories have templated names that change.
DOCKERFILE_GLOB = "_project_template/**/Dockerfile*.jinja"

REQUIREMENT = re.compile(
    r'"(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)(?P<extras>\[[^\]]*\])?>=(?P<version>[0-9][^",;\s]*)"'
)
ACTION = re.compile(r"(?P<prefix>uses:\s*)(?P<repo>[\w.-]+/[\w.-]+)@(?P<version>v\d+)\b")
UV_IMAGE = re.compile(r"(?P<prefix>ghcr\.io/astral-sh/uv:)(?P<version>\d+\.\d+)\b")
ACTIONLINT = re.compile(r'(?P<prefix>ACTIONLINT_VERSION:\s*")(?P<version>[\d.]+)(?=")')

Change = tuple[str, str, str]  # (what, old, new)


def _get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    if "api.github.com" in url and (token := os.environ.get("GITHUB_TOKEN")):
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


@cache
def latest_pypi(name: str) -> str:
    """Latest non-prerelease version of *name* on PyPI."""
    return _get_json(f"https://pypi.org/pypi/{name}/json")["info"]["version"]


@cache
def latest_github(repo: str) -> str:
    """Latest release tag of *repo*, without a leading v (prereleases excluded)."""
    return _get_json(f"https://api.github.com/repos/{repo}/releases/latest")["tag_name"].lstrip("v")


def bump_requirements(text: str, latest: Callable[[str], str]) -> tuple[str, list[Change]]:
    changes: list[Change] = []

    def replace(m: re.Match) -> str:
        new = latest(m["name"])
        if Version(new) <= Version(m["version"]):
            return m[0]
        changes.append((m["name"], m["version"], new))
        return f'"{m["name"]}{m["extras"] or ""}>={new}"'

    return REQUIREMENT.sub(replace, text), changes


def bump_actions(text: str, latest: Callable[[str], str]) -> tuple[str, list[Change]]:
    changes: list[Change] = []

    def replace(m: re.Match) -> str:
        major = f"v{Version(latest(m['repo'])).major}"
        if int(major[1:]) <= int(m["version"][1:]):
            return m[0]
        changes.append((m["repo"], m["version"], major))
        return f"{m['prefix']}{m['repo']}@{major}"

    return ACTION.sub(replace, text), changes


def bump_pattern(
    text: str, pattern: re.Pattern, what: str, latest: str, keep: Callable[[Version], str]
) -> tuple[str, list[Change]]:
    """Replace *pattern*'s `version` group with *latest*, trimmed by *keep*, if newer."""
    changes: list[Change] = []
    new = keep(Version(latest))

    def replace(m: re.Match) -> str:
        if Version(new) <= Version(m["version"]):
            return m[0]
        changes.append((what, m["version"], new))
        return f"{m['prefix']}{new}"

    return pattern.sub(replace, text), changes


def update(root: Path = ROOT) -> list[Change]:
    """Bump every version under *root*, rewriting files in place."""
    changes: list[Change] = []

    def rewrite(path: Path, *bumps: Callable[[str], tuple[str, list[Change]]]) -> None:
        text = original = path.read_text()
        for bump in bumps:
            text, found = bump(text)
            changes.extend(found)
        if text != original:
            path.write_text(text)

    for name in PYPROJECTS:
        rewrite(root / name, lambda t: bump_requirements(t, latest_pypi))
    for directory in WORKFLOW_DIRS:
        for path in sorted((root / directory).iterdir()):
            rewrite(
                path,
                lambda t: bump_actions(t, latest_github),
                lambda t: bump_pattern(
                    t, ACTIONLINT, "actionlint", latest_github("rhysd/actionlint"), str
                ),
            )
    for path in sorted(root.glob(DOCKERFILE_GLOB)):
        rewrite(
            path,
            lambda t: bump_pattern(
                t, UV_IMAGE, "uv image", latest_pypi("uv"), lambda v: f"{v.major}.{v.minor}"
            ),
        )

    # The same dependency is often bumped in several files; report it once.
    return sorted(set(changes))


def summarize(changes: list[Change]) -> str:
    if not changes:
        return "Everything the template ships is already at its latest version.\n"
    rows = "\n".join(f"| `{what}` | {old} | {new} |" for what, old, new in changes)
    return f"| Dependency | From | To |\n| --- | --- | --- |\n{rows}\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--summary", type=Path, help="also write the Markdown summary here")
    args = parser.parse_args()

    summary = summarize(update())
    sys.stdout.write(summary)
    if args.summary:
        args.summary.write_text(summary)


if __name__ == "__main__":
    main()
