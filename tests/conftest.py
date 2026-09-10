"""Fixtures for testing SpiriProjectTemplates."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import copier
import jinja2
import pytest

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "{{project_name}}"

DEFAULT_VARIABLES = {
    "project_name": "my-sensor",
    "python_package_name": "my_sensor",
    "description": "A test sensor project",
    "version": "1.2.3",
    "author_name": "Test Author",
    "author_email": "test@example.com",
    "license": "MIT",
    "spiri_config_plugin": False,
    "spiri_branding": False,
    "include_tests": True,
    "include_docs": False,
    "include_nix": False,
}


JINJA_FILES = [
    # Top-level files
    "pyproject.toml.jinja",
    "README.md.jinja",
    "Makefile.jinja",
    "python-version.jinja",  # placeholder - actual file may differ
    # Source files (nested under src/{{python_package_name}}/)
    "src/__init.py.jinja",  # placeholder
    "src/cli.py.jinja",
    "src/main.py.jinja",
    "src/web.py.jinja",
    # Test files
    "tests/test_cli.py.jinja",
    # Docker
    "docker/Dockerfile.jinja",
    # Compose files
    "templates/compose.yaml.jinja",
    "templates/compose.dev.yaml.jinja",
    "templates/compose.test.yaml.jinja",
]


def _resolve_template_path(filename, variables):
    """Resolve a template file path with variables substituted in content, not path.
    
    Template files use Jinja variables in both:
    - File names/paths (e.g., src/{{python_package_name}}/)
    - Content (e.g., name = "{{project_name}}")
    
    For finding files, we use the literal path as stored in the template repo.
    """
    filepath = TEMPLATE_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Template file not found: {filepath}")
    return filepath


def _render_jinja_file(filename, variables):
    """Render a single Jinja template file."""
    filepath = _resolve_template_path(filename, variables)
    
    env = jinja2.Environment(
        loader=jinja2.BaseLoader(),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.from_string(filepath.read_text())
    return template.render(**variables)


def _render_all_jinja_files(variables):
    """Render all Jinja template files in the template directory."""
    rendered = {}
    for root, dirs, files in os.walk(TEMPLATE_DIR):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for filename in files:
            filepath = Path(root) / filename
            rel_path = filepath.relative_to(TEMPLATE_DIR)
            
            # Render path components with variables
            env = jinja2.Environment(
                loader=jinja2.BaseLoader(),
                trim_blocks=True,
                lstrip_blocks=True,
            )
            
            try:
                if filepath.name.endswith('.jinja'):
                    rendered_parts = []
                    for part in rel_path.with_suffix('').parts:
                        template = env.from_string(part)
                        rendered_parts.append(template.render(**variables))
                    rendered_key = '/'.join(rendered_parts)
                    
                    template = env.from_string(filepath.read_text())
                    rendered[rendered_key] = template.render(**variables)
                else:
                    rendered_parts = []
                    for part in rel_path.parts:
                        template = env.from_string(part)
                        rendered_parts.append(template.render(**variables))
                    rendered['/'.join(rendered_parts)] = filepath.read_text()
            except Exception as e:
                rendered[f"ERROR:{rel_path}"] = str(e)
    return rendered


@pytest.fixture
def variables():
    """Default variables for testing."""
    return DEFAULT_VARIABLES


@pytest.fixture
def rendered_template(variables):
    """Render a single Jinja template file."""
    return lambda filename: _render_jinja_file(filename, variables)


@pytest.fixture
def rendered_all(variables):
    """Render all Jinja template files in the template directory."""
    return _render_all_jinja_files(variables)


@pytest.fixture
def generated_project(variables):
    """Generate a project using copier and return the temp directory."""
    import shutil
    
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir) / "test-project"
        
        copier.run_copy(
            str(Path(__file__).resolve().parent.parent),
            dest,
            data={
                "project_name": variables["project_name"],
                "python_package_name": variables["python_package_name"],
                "description": variables["description"],
                "version": variables["version"],
                "author_name": variables.get("author_name", ""),
                "author_email": variables.get("author_email", ""),
                "license": variables.get("license", "MIT"),
                "spiri_config_plugin": variables.get("spiri_config_plugin", False),
                "spiri_branding": variables.get("spiri_branding", False),
                "include_tests": variables.get("include_tests", True),
                "include_docs": variables.get("include_docs", False),
                "include_nix": variables.get("include_nix", False),
            },
            unsafe=True,
            defaults=True,
            overwrite=True,
            cleanup_on_error=False,
            quiet=True,
        )
        yield dest
        
        # Cleanup is handled by tempfile
