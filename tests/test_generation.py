"""What copier generates, for each option combo. Fast: no network, no docker."""

from __future__ import annotations

import json
import re
import shutil
import sys
import tomllib

import pytest
import yaml

from tests.conftest import generate, run

PKG = "SpiriTestApp"

ALWAYS = [
    ".copier-answers.yml",
    ".gitignore",
    ".python-version",
    "AGENTS.md",
    "CHANGES.md",
    "Makefile",
    "README.md",
    "pyproject.toml",
    ".github/workflows/lint-test.yml",
    ".github/workflows/template-update.yml",
]


def _image(a):
    return a["kind"] in ("app", "both")


def _package(a):
    return a["kind"] in ("library", "both")


# Files that exist only under a condition on the answers. Questions skipped by
# their `when` are absent from the answers file, hence `.get`.
CONDITIONAL = {
    "docs": (
        lambda a: a["include_docs"],
        [
            "docs/conf.py",
            "docs/index.md",
            "docs/revisions.md",
            "docs/_static/custom.css",
            "revisions.yaml",
            ".github/workflows/docs.yml",
            ".github/scripts/publish_docs.py",
            "docs/_templates/versions.html",
        ],
    ),
    "image": (
        _image,
        [
            "docker/Dockerfile",
            "docker/compose.yaml",
            "docker/compose.dev.yaml",
            ".github/workflows/docker-publish.yml",
            ".devcontainer/devcontainer.json",
        ],
    ),
    "package": (_package, [".github/workflows/pypi-publish.yml"]),
    "api docs": (lambda a: a["include_docs"] and a["kind"] != "stack", ["docs/api/index.md"]),
    "scaffold": (lambda a: a.get("scaffold"), [f"src/{PKG}/__init__.py", f"src/{PKG}/cli.py"]),
    "scaffold app": (lambda a: a.get("scaffold") and _image(a), [f"src/{PKG}/main.py"]),
    "tests": (lambda a: a["include_tests"] and a.get("scaffold"), ["tests/test_cli.py"]),
    "app tests": (
        lambda a: a["include_tests"] and a.get("scaffold") and _image(a),
        ["tests/test_main.py"],
    ),
    "image tests": (lambda a: a["include_tests"] and _image(a), ["docker/compose.test.yaml"]),
    "nix": (lambda a: a["include_nix"], ["nix/flake.nix"]),
    "plugin": (lambda a: a.get("spiri_config_plugin"), [f"src/{PKG}/web.py"]),
    "brand": (
        lambda a: a.get("use_spiri_brand"),
        ["docs/_static/spiri-logo-light.svg", "docs/_static/spiri-logo-dark.svg"],
    ),
    "vale": (
        lambda a: a.get("use_vale"),
        [".vale.ini", "styles/config/vocabularies/Spiri/accept.txt"],
    ),
}

# Gone for good; a regression if they reappear.
NEVER = [".readthedocs.yaml", "docs/requirements.txt"]


def test_always_present(project):
    missing = [f for f in ALWAYS if not (project / f).is_file()]
    assert not missing


@pytest.mark.parametrize("condition", list(CONDITIONAL))
def test_conditional_files(project, answers, condition):
    applies, files = CONDITIONAL[condition]
    for f in files:
        assert (project / f).is_file() == bool(applies(answers)), f


def test_removed_files_stay_removed(project):
    assert not [f for f in NEVER if (project / f).exists()]


def test_no_empty_files_or_dirs(project):
    """A conditional that rendered to nothing should have skipped the file."""
    empty = [
        p.relative_to(project)
        for p in project.rglob("*")
        if (p.is_file() and p.stat().st_size == 0 and p.name != "__init__.py")
        or (p.is_dir() and not any(p.iterdir()))
    ]
    assert not empty


def test_no_unrendered_jinja(project):
    """No template tag survives into the output, in a file or a path.

    The template's delimiters are `[[ ]]` and `[% %]`, so a literal `{{ }}` (GitHub
    expressions, MyST substitutions) is legitimate output. A TOML `[[table]]` isn't a
    leftover either: it has a dot or no closing pattern a variable would.
    """
    tag = re.compile(r"\[%|%\]|\[\[\s*[A-Za-z_]+\s*(\|[^\]]*)?\]\]")
    leftovers = [str(p.relative_to(project)) for p in project.rglob("*") if tag.search(p.name)]
    for p in project.rglob("*"):
        if p.is_file() and p.suffix != ".svg":
            for n, line in enumerate(p.read_text().splitlines(), 1):
                if tag.search(line):
                    leftovers.append(f"{p.relative_to(project)}:{n}: {line}")
    assert not leftovers


def test_config_files_parse(project):
    for p in [*project.rglob("*.yml"), *project.rglob("*.yaml")]:
        assert yaml.safe_load(p.read_text()), p
    for p in project.rglob("*.toml"):
        tomllib.loads(p.read_text())
    for p in project.rglob("*.json"):
        json.loads(p.read_text())


def test_python_version_rendered(project, answers):
    assert (project / ".python-version").read_text().strip() == answers["python_version"]
    pyproject = tomllib.loads((project / "pyproject.toml").read_text())
    assert pyproject["project"]["requires-python"] == f">={answers['python_version']}"


def test_dependencies_one_per_line(project, answers):
    """Each dependency on its own line: a stray `[%-` in the template glues them together,
    which is still valid TOML, so nothing else notices."""
    pyproject = (project / "pyproject.toml").read_text()
    deps = tomllib.loads(pyproject)["project"]["dependencies"]
    for dep in deps:
        assert f'    "{dep}",\n' in pyproject, dep
    assert bool(deps) == bool(answers.get("scaffold"))


def test_spirisynq_wiring(project, answers):
    pyproject = (project / "pyproject.toml").read_text()
    on = bool(answers.get("spirisynq"))
    assert ("spirisynq>=" in pyproject) == on
    if not _image(answers):
        return
    compose = yaml.safe_load((project / "docker/compose.yaml").read_text())
    main = (project / f"src/{PKG}/main.py").read_text()
    assert ("spirisynq" in compose.get("networks", {})) == on
    assert ("zenoh_connect" in main) == on
    if on:
        assert compose["networks"]["spirisynq"]["external"] is True
        assert "spirisynq" in compose["services"]["app"]["networks"]


def test_spiriconfig_plugin_labels(project, answers):
    if not _image(answers):
        pytest.skip("no image")
    services = yaml.safe_load((project / "docker/compose.yaml").read_text())["services"]
    labelled = [s for s in services.values() if "spiriconfig.plugin.name" in s.get("labels", {})]
    assert len(labelled) == (1 if answers["spiri_config_plugin"] else 0)
    for service in labelled:
        assert service["labels"]["spiriconfig.plugin.port"] == "8080"


def test_image_names_are_lowercase(project):
    """Docker rejects uppercase repository names, and the project name is CamelCase."""
    for p in (project / "docker").glob("compose*.yaml"):
        for service in yaml.safe_load(p.read_text())["services"].values():
            image = service.get("image", "").split("${COMPONENT_IMAGE:-")[-1].rstrip("}")
            assert image == image.lower(), f"{p.name}: {image}"


def test_docs_workflow_publishes_versions(project, answers):
    if not answers["include_docs"]:
        pytest.skip("no docs")
    workflow = yaml.safe_load((project / ".github/workflows/docs.yml").read_text())
    build_cmds = " ".join(s.get("run", "") for s in workflow["jobs"]["build"]["steps"])
    assert "sphinx-build -W" in build_cmds
    # Main and release tags publish; PRs don't. gh-pages is the site, so no
    # Actions Pages deployment.
    publish = workflow["jobs"]["publish"]
    assert "refs/heads/main" in publish["if"]
    assert "refs/tags/v" in publish["if"]
    assert "pull_request" in publish["if"]
    assert publish["permissions"] == {"contents": "write"}
    assert set(publish["needs"]) == {"build", "pdf"}
    steps = " ".join(s.get("run", "") for s in publish["steps"])
    assert ".github/scripts/publish_docs.py" in steps
    assert "deploy" not in workflow["jobs"]
    conf = (project / "docs/conf.py").read_text()
    assert '"versions.html"' in conf
    assert conf.count('html_baseurl = "') == 1 and '/latest/"' in conf


def test_docs_branding(project, answers):
    if not answers["include_docs"]:
        pytest.skip("no docs")
    conf = (project / "docs/conf.py").read_text()
    branded = answers["use_spiri_brand"]
    assert ('"light_logo": "spiri-logo-light.svg"' in conf) == branded
    assert ("spiri_docs_logo" in conf) == branded


def test_docs_are_a_controlled_document(project, answers):
    """Every project's docs use spiri_docs, as the manuals do, from one revisions.yaml."""
    if not answers["include_docs"]:
        pytest.skip("no docs")
    assert '"spiri_docs"' in (project / "docs/conf.py").read_text()
    revisions = yaml.safe_load((project / "revisions.yaml").read_text())
    assert revisions["document_number"] == answers["document_number"]
    assert revisions["regulator_facing"] == (answers["audience"] == "regulator")
    assert revisions["revisions"][0]["draft"] is True
    pyproject = tomllib.loads((project / "pyproject.toml").read_text())
    assert any(d.startswith("spiri-docs>=") for d in pyproject["dependency-groups"]["docs"])


def test_ruff_clean(project):
    """The generated project must pass its own lint job."""
    ruff = [sys.executable, "-m", "ruff"]
    run([*ruff, "format", "--check", "--diff", "."], cwd=project)
    run([*ruff, "check", "."], cwd=project)


@pytest.mark.skipif(not shutil.which("actionlint"), reason="actionlint not installed")
def test_workflows_lint(project):
    run(["actionlint", *map(str, (project / ".github/workflows").glob("*.yml"))], cwd=project)


@pytest.mark.parametrize(
    ("project_name", "package"),
    [
        ("SpiriSensor", "SpiriSensor"),
        ("my-sensor", "MySensor"),
        ("spiri.thing_two", "SpiriThingTwo"),
    ],
)
def test_package_name_defaults_to_camel_case(tmp_path, project_name, package):
    dest = generate(tmp_path / "p", project_name=project_name)
    assert (dest / "src" / package / "__init__.py").is_file()


def test_invalid_package_name_rejected(tmp_path):
    with pytest.raises(ValueError):
        generate(tmp_path / "p", python_package_name="not-valid")
