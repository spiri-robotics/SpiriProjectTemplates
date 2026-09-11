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
