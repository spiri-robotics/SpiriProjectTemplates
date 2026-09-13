"""Test output validity - rendered configs are parseable."""

from __future__ import annotations

import pytest
import toml
import yaml

from tests.conftest import _render_jinja_file


class TestTOMLParsing:
    """Tests that rendered TOML files parse correctly."""

    def test_pyproject_parses(self, variables):
        """pyproject.toml should parse as valid TOML."""
        content = _render_jinja_file("pyproject.toml.jinja", variables)
        result = toml.loads(content)
        assert result
        assert "project" in result

    def test_pyproject_project_name(self, variables):
        """pyproject.toml should have correct project name."""
        content = _render_jinja_file("pyproject.toml.jinja", variables)
        result = toml.loads(content)
        assert result["project"]["name"] == variables["project_name"]

    def test_pyproject_project_version(self, variables):
        """pyproject.toml should have correct version."""
        content = _render_jinja_file("pyproject.toml.jinja", variables)
        result = toml.loads(content)
        assert result["project"]["version"] == variables["version"]


class TestYAMLParsing:
    """Tests that rendered YAML files parse correctly."""

    def test_compose_parses(self, variables):
        """compose.yaml should parse as valid YAML."""
        content = _render_jinja_file("docker/compose.yaml.jinja", variables)
        result = yaml.safe_load(content)
        assert result
        assert "services" in result

    def test_compose_dev_parses(self, variables):
        """compose.dev.yaml should parse as valid YAML."""
        content = _render_jinja_file("docker/compose.dev.yaml.jinja", variables)
        result = yaml.safe_load(content)
        assert result
        assert "services" in result

    def test_compose_test_parses(self, variables):
        """compose.test.yaml should parse as valid YAML."""
        content = _render_jinja_file("docker/compose.test.yaml.jinja", variables)
        result = yaml.safe_load(content)
        assert result
        assert "services" in result

    def test_docker_publish_workflow_parses(self, variables):
        """docker-publish.yml should parse as valid YAML."""
        content = _render_jinja_file(
            ".github/workflows/docker-publish.yml.jinja", variables
        )
        result = yaml.safe_load(content)
        assert result
        assert "jobs" in result
        assert "build-and-push" in result["jobs"]

    def test_docker_publish_workflow_no_app_store_job_when_disabled(self, variables):
        """update-app-store job should be absent when app_store_repo is blank."""
        content = _render_jinja_file(
            ".github/workflows/docker-publish.yml.jinja", variables
        )
        result = yaml.safe_load(content)
        assert "update-app-store" not in result["jobs"]

    def test_docker_publish_workflow_app_store_job_when_enabled(self, variables):
        """update-app-store job should appear, and reference the right repo/path, when app_store_repo is set."""
        variables = {
            **variables,
            "app_store_repo": "spiri-robotics/spiri-apps",
            "app_store_path": "my-sensor",
        }
        content = _render_jinja_file(
            ".github/workflows/docker-publish.yml.jinja", variables
        )
        result = yaml.safe_load(content)
        assert "update-app-store" in result["jobs"]
        job = result["jobs"]["update-app-store"]
        assert job["steps"][1]["with"]["repository"] == "spiri-robotics/spiri-apps"
        assert job["steps"][3]["env"]["SEARCH_ROOT"] == "app-store/my-sensor"

    def test_docker_publish_workflow_app_store_searches_whole_repo_by_default(
        self, variables
    ):
        """A blank app_store_path should search the whole app store checkout."""
        variables = {
            **variables,
            "app_store_repo": "spiri-robotics/spiri-apps",
            "app_store_path": "",
        }
        content = _render_jinja_file(
            ".github/workflows/docker-publish.yml.jinja", variables
        )
        result = yaml.safe_load(content)
        job = result["jobs"]["update-app-store"]
        assert job["steps"][3]["env"]["SEARCH_ROOT"] == "app-store"

    def test_docker_publish_workflow_references_existing_bump_script(self, variables):
        """The run step's script path should point at a file that actually exists."""
        from pathlib import Path

        variables = {**variables, "app_store_repo": "spiri-robotics/spiri-apps"}
        content = _render_jinja_file(
            ".github/workflows/docker-publish.yml.jinja", variables
        )
        result = yaml.safe_load(content)
        run_step = result["jobs"]["update-app-store"]["steps"][3]
        assert "bump_app_store_compose.py" in run_step["run"]

        template_dir = Path(__file__).resolve().parent.parent / "_project_template"
        script_path = (
            template_dir / ".github" / "scripts" / "bump_app_store_compose.py"
        )
        assert script_path.is_file()
