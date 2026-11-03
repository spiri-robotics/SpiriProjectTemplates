"""Generated projects pass their own CI: install, test, build docs, build the image.

Slow (resolves and installs dependencies) and needs network; the image builds
also need docker. Run with `pytest -m slow` / `pytest -m docker`.
"""

from __future__ import annotations

import shutil

import pytest
import yaml

from tests.conftest import run


@pytest.fixture(scope="session")
def synced(project):
    """*project* with uv.lock created and every dependency group installed."""
    answers = yaml.safe_load((project / ".copier-answers.yml").read_text())
    if answers["kind"] != "stack" and not answers["scaffold"]:
        pytest.skip("an adopted project's code isn't here to install")
    run(["uv", "sync", "--all-groups"], cwd=project, timeout=600)
    return project


def _needs_code(project):
    if not yaml.safe_load((project / ".copier-answers.yml").read_text()).get("scaffold"):
        pytest.skip("no starter code")


@pytest.mark.slow
def test_cli_runs(synced, answers):
    _needs_code(synced)
    out = run(["uv", "run", answers["project_name"], "version"], cwd=synced).stdout
    assert answers["version"] in out


@pytest.mark.slow
def test_entry_points_resolve(synced):
    """Every script and entry point the package declares imports and exists."""
    _needs_code(synced)
    check = (
        "from importlib.metadata import distribution, entry_points; "
        "import tomllib; "
        "name = tomllib.load(open('pyproject.toml', 'rb'))['project']['name']; "
        "eps = distribution(name).entry_points; "
        "assert eps, 'no entry points'; "
        "[ep.load() for ep in eps]; "
        "print(len(eps))"
    )
    run(["uv", "run", "python", "-c", check], cwd=synced)


@pytest.mark.slow
def test_generated_tests_pass(synced, answers):
    if not answers["include_tests"] or not answers.get("scaffold"):
        pytest.skip("no tests")
    run(["uv", "run", "pytest"], cwd=synced)


@pytest.mark.slow
def test_docs_build_without_warnings(synced, answers):
    if not answers["include_docs"]:
        pytest.skip("no docs")
    # The docs workflow's command.
    run(
        [
            "uv",
            "run",
            "sphinx-build",
            "-W",
            "--keep-going",
            "-b",
            "html",
            "docs",
            "docs/_build/html",
        ],
        cwd=synced,
        timeout=300,
    )
    html = synced / "docs/_build/html"
    assert (html / "index.html").is_file()
    if answers["kind"] != "stack":
        # The API page has autodoc output, not directives rendered as text.
        api = (html / "api/index.html").read_text()
        assert "automodule" not in api
        assert f'id="{answers["python_package_name"]}.cli.version"' in api
    # The cover's document control block is filled from revisions.yaml.
    index = (html / "index.html").read_text()
    assert answers["document_number"] in index
    assert "{{" not in index


@pytest.mark.slow
@pytest.mark.skipif(not shutil.which("latexmk"), reason="LaTeX not installed")
def test_pdf_builds(synced, answers):
    """The controlled PDF, named by spiri_docs for the document number and revision.

    Non-ASCII text, as docstrings have, must not stop the build: pdflatex did.
    """
    if not answers["include_docs"]:
        pytest.skip("no docs")
    index = synced / "docs/index.md"
    original = index.read_text()
    index.write_text(original + "\nT_child = T_parent ∘ T_mount → café, 50 µm, ±2°.\n")
    try:
        _build_pdf(synced)
    finally:
        index.write_text(original)
    name = run(["uv", "run", "python", "-m", "spiri_docs", "name"], cwd=synced).stdout.strip()
    assert name.startswith(answers["document_number"])
    assert (synced / "docs/_build/latex" / f"{name}.pdf").stat().st_size > 10_000


def _build_pdf(synced):
    # The docs workflow's commands.
    run(
        [
            "uv",
            "run",
            "sphinx-build",
            "-W",
            "--keep-going",
            "-b",
            "latex",
            "docs",
            "docs/_build/latex",
        ],
        cwd=synced,
        timeout=300,
    )
    run(["make", "-C", "docs/_build/latex", "all-pdf"], cwd=synced, timeout=600)


@pytest.mark.slow
@pytest.mark.skipif(not shutil.which("vale"), reason="Vale not installed")
def test_vale_has_no_errors(synced, answers):
    """Vale is advisory in CI, but the docs a project starts with should be clean of errors."""
    if not answers.get("use_vale"):
        pytest.skip("no vale")
    run(["vale", "sync"], cwd=synced, timeout=300)
    run(["vale", "--minAlertLevel=error", "docs/"], cwd=synced)


@pytest.mark.docker
@pytest.mark.skipif(not shutil.which("docker"), reason="docker not installed")
def test_image_builds_and_runs(synced, answers):
    if answers["kind"] not in ("app", "both"):
        pytest.skip("no image")
    tag = f"{answers['project_name'].lower()}:template-test"
    run(["docker", "build", "-f", "docker/Dockerfile", "-t", tag, "."], cwd=synced, timeout=900)
    out = run(["docker", "run", "--rm", tag, answers["project_name"], "version"], cwd=synced)
    assert answers["version"] in out.stdout
    # Runtime dependencies only: no test or docs tooling in the shipped image.
    tools = run(
        [
            "docker",
            "run",
            "--rm",
            tag,
            "python",
            "-c",
            "import importlib.util as u; print([m for m in ('pytest', 'sphinx', 'ruff') if u.find_spec(m)])",
        ],
        cwd=synced,
    ).stdout.strip()
    assert tools == "[]", tools


@pytest.mark.docker
@pytest.mark.skipif(not shutil.which("docker"), reason="docker not installed")
def test_tests_pass_in_image(synced, answers):
    if answers["kind"] not in ("app", "both"):
        pytest.skip("no image")
    if not answers["include_tests"]:
        pytest.skip("no tests")
    run(
        ["docker", "compose", "-f", "docker/compose.test.yaml", "run", "--rm", "--build", "test"],
        cwd=synced,
        timeout=900,
    )
