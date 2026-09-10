"""Tests for spiri_branding conditional functionality."""

from __future__ import annotations

from tests.conftest import _render_jinja_file, DEFAULT_VARIABLES


class TestSpiriBrandingConditional:
    """Test that spiri_branding conditional works correctly."""

    def test_conf_no_branding_copyright(self, variables):
        """conf.py should use author copyright when spiri_branding=False."""
        content = _render_jinja_file("docs/conf.py.jinja", variables)
        assert "2026, Spiri" not in content
        assert "2026, Test Author" in content

    def test_conf_no_branding_logo(self, variables):
        """conf.py should not reference logo when spiri_branding=False."""
        content = _render_jinja_file("docs/conf.py.jinja", variables)
        assert "logo.svg" not in content
        assert "logo-dark.svg" not in content

    def test_conf_has_branding(self):
        """conf.py should use Spiri branding when spiri_branding=True."""
        branding_vars = {**DEFAULT_VARIABLES, "spiri_branding": True}
        content = _render_jinja_file("docs/conf.py.jinja", branding_vars)
        assert "2026, Spiri" in content
        assert "spiri-logo-light.svg" in content
        assert "spiri-logo-dark.svg" in content

    def test_getting_started_no_link(self, variables):
        """getting_started.md should not link to Spiri when spiri_branding=False."""
        content = _render_jinja_file("docs/getting_started.md.jinja", variables)
        assert "spiri-robotics" not in content
        assert "spiri-app-template" not in content
        assert "pyproject.toml" in content  # Should still have generic link

    def test_getting_started_has_link(self):
        """getting_started.md should link to Spiri when spiri_branding=True."""
        branding_vars = {**DEFAULT_VARIABLES, "spiri_branding": True}
        content = _render_jinja_file("docs/getting_started.md.jinja", branding_vars)
        assert "spiri-robotics" in content
        assert "spiri-app-template" in content

    def test_conf_no_static_path_without_branding(self, variables):
        """conf.py should not include static path when spiri_branding=False."""
        content = _render_jinja_file("docs/conf.py.jinja", variables)
        assert 'html_static_path: list[str] = []' in content

    def test_conf_static_path_with_branding(self):
        """conf.py should include static path when spiri_branding=True."""
        branding_vars = {**DEFAULT_VARIABLES, "spiri_branding": True}
        content = _render_jinja_file("docs/conf.py.jinja", branding_vars)
        assert 'html_static_path: list[str] = ["static"]' in content
