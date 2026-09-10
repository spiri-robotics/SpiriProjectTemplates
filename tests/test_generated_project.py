"""E2E test: generate a project via copier."""

from __future__ import annotations

import pytest


@pytest.mark.slow
@pytest.mark.integration
class TestGeneratedProject:

    def test_project_files_created(self, generated_project, variables):
        """Generated project should have key files in expected locations."""
        nested_project = generated_project / variables["project_name"]
        
        assert (nested_project / "pyproject.toml").exists()
        assert (nested_project / "README.md").exists()
        assert (nested_project / "src").is_dir()
        assert (nested_project / "tests").is_dir()
        
        src_files = list((nested_project / "src").rglob("*.py"))
        assert len(src_files) >= 2  # __init__.py and cli.py
        
        test_files = list((nested_project / "tests").rglob("*.py"))
        assert len(test_files) >= 1  # test_cli.py

    def test_pyproject_toml_valid(self, generated_project, variables):
        """Generated pyproject.toml should be valid TOML with correct metadata."""
        import toml
        
        nested_project = generated_project / variables["project_name"]
        toml_content = toml.load(nested_project / "pyproject.toml")
        
        assert toml_content["project"]["name"] == variables["project_name"]
        assert "scripts" in toml_content["project"]

    def test_compose_files_creatable(self, generated_project, variables):
        """Generated compose files should exist when templates are present."""
        import yaml
        
        nested_project = generated_project / variables["project_name"]
        compose_path = nested_project / "templates" / "compose.yaml"
        
        if compose_path.exists():
            content = yaml.safe_load(compose_path.read_text())
            assert "services" in content
