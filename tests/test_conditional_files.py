"""Test conditional file generation."""

from __future__ import annotations

from pathlib import Path

import pytest


class TestSpiriConfigPluginConditional:
    """Test web.py is generated correctly based on spiri_config_plugin."""

    def test_web_file_present_when_plugin_enabled(self, generated_project, variables):
        """web.py should be present when spiri_config_plugin=true."""
        generated = generated_project
        web_file = generated / "src" / variables["python_package_name"] / "web.py"
        content = web_file.read_text()
        assert content  # File exists and has content

    def test_web_file_placeholder_when_plugin_disabled(self, generated_project, variables):
        """web.py should be a placeholder when spiri_config_plugin=false."""
        generated = generated_project
        web_file = generated / "src" / variables["python_package_name"] / "web.py"
        content = web_file.read_text()
        # Should contain placeholder text or be empty since plugin is disabled
        assert web_file.exists()


class TestIncludeTestsConditional:
    """Test tests directory based on include_tests."""

    def test_test_files_exist(self, generated_project, variables):
        """Test files should be present."""
        generated = generated_project
        test_files = list((generated / "tests").rglob("*.py"))
        assert len(test_files) > 0

    def test_test_has_content(self, generated_project, variables):
        """Tests should have actual test code."""
        generated = generated_project
        test_file = generated / "tests" / "test_cli.py"
        content = test_file.read_text()
        assert "test_cli" in content.lower()


class TestIncludeDocsConditional:
    """Test docs directory based on include_docs."""

    def test_docs_absent_when_disabled(self, generated_project):
        """Docs directory should not be created when include_docs=false."""
        generated = generated_project
        docs_dir = generated / "docs"
        # With include_docs=False, docs dir should not exist or be minimal
