"""Test basic template rendering correctness."""

from __future__ import annotations

import pytest


class TestRenderedContent:

    def test_pyproject_project_name(self, rendered_template, variables):
        """pyproject.toml should have correct project name."""
        content = rendered_template("pyproject.toml.jinja")
        assert f'name = "{variables["project_name"]}"' in content
        assert f'version = "{variables["version"]}"' in content
        assert f'description = "{variables["description"]}"' in content

    def test_readme_title(self, rendered_template, variables):
        """README should have project name as title."""
        content = rendered_template("README.md.jinja")
        assert f"# {variables['project_name']}" in content
        assert variables["description"] in content

    def test_cli_has_app(self, rendered_template, variables):
        """CLI should reference project name and package name."""
        content = rendered_template("src/{{python_package_name}}/cli.py.jinja")
        assert variables["python_package_name"] in content
        assert variables["project_name"] in content

    def test_main_settings(self, rendered_template, variables):
        """Main should have correct settings configuration."""
        content = rendered_template("src/{{python_package_name}}/main.py.jinja")
        expected_prefix = variables["python_package_name"].replace("-", "_").replace(".", "_").upper()
        assert f"env_prefix=\"{expected_prefix}_\"" in content
        assert variables["python_package_name"] in content
        assert variables["project_name"] in content

    def test_init_version(self, rendered_template, variables):
        """__init__.py should have version."""
        content = rendered_template("src/{{python_package_name}}/__init__.py.jinja")
        assert variables["version"] in content
        assert variables["project_name"] in content

    def test_dockerfile_content(self, rendered_template, variables):
        """Dockerfile should package the right code."""
        content = rendered_template("docker/Dockerfile.jinja")
        assert variables["python_package_name"] in content

    def test_compose_project_name(self, rendered_template, variables):
        """Compose YAML should have project name."""
        content = rendered_template("templates/compose.yaml.jinja")
        assert variables["project_name"] in content

    def test_compose_dev_project_name(self, rendered_template, variables):
        """Compose dev YAML should have project name."""
        content = rendered_template("templates/compose.dev.yaml.jinja")
        assert variables["project_name"] in content

    def test_compose_test_project_name(self, rendered_template, variables):
        """Compose test YAML should have project name."""
        content = rendered_template("templates/compose.test.yaml.jinja")
        assert variables["project_name"] in content

    def test_compose_greeting(self, rendered_template, variables):
        """Compose files should have correct greeting."""
        content = rendered_template("templates/compose.yaml.jinja")
        assert variables["project_name"] in content

    def test_makefile_target_name(self, rendered_template, variables):
        """Makefile should reference project name."""
        content = rendered_template("Makefile.jinja")
        assert variables["project_name"] in content
