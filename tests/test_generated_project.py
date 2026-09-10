"""E2E test: generate a project via copier."""

from __future__ import annotations

import pytest


@pytest.mark.slow
@pytest.mark.integration
class TestGeneratedProject:

    def test_project_files_created(self, generated_project, variables):
        """Generated project should have key files in expected locations."""
        generated = generated_project
        
        assert (generated / "pyproject.toml").exists()
        assert (generated / "README.md").exists()
        assert (generated / "src").is_dir()
        assert (generated / "tests").is_dir()
        
        src_files = list((generated / "src").rglob("*.py"))
        assert len(src_files) >= 2  # __init__.py and cli.py
        
        test_files = list((generated / "tests").rglob("*.py"))
        assert len(test_files) >= 1  # test_cli.py

    def test_pyproject_toml_valid(self, generated_project, variables):
        """Generated pyproject.toml should be valid TOML with correct metadata."""
        import toml
        
        generated = generated_project
        toml_content = toml.load(generated / "pyproject.toml")
        
        assert toml_content["project"]["name"] == variables["project_name"]
        assert "scripts" in toml_content["project"]

    def test_compose_files_creatable(self, generated_project, variables):
        """Generated compose files should exist when templates are present."""
        import yaml
        
        generated = generated_project
        compose_path = generated / "templates" / "compose.yaml"
        
        if compose_path.exists():
            content = yaml.safe_load(compose_path.read_text())
            assert "services" in content
