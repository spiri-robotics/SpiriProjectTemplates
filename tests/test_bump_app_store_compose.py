"""Tests for the app-store compose.yaml bump script.

This is the only part of the docker-publish workflow with real logic in
it (matching + rewriting YAML) rather than just wiring together
third-party actions, so it gets exercised directly here instead of only
through a GitHub Actions run.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "_project_template"
    / ".github"
    / "scripts"
    / "bump_app_store_compose.py"
)


def run_bump(search_root: Path, image_ref: str, version: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--search-root",
            str(search_root),
            "--image-ref",
            image_ref,
            "--version",
            version,
        ],
        capture_output=True,
        text=True,
    )


def write_compose(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content))


class TestBumpAppStoreCompose:
    def test_bumps_matching_image_and_sets_version(self, tmp_path):
        compose = tmp_path / "my-app" / "compose.yaml"
        write_compose(
            compose,
            """\
            services:
              app:
                image: ghcr.io/org/my-app:1.0.0
            """,
        )

        result = run_bump(tmp_path, "ghcr.io/org/my-app", "v1.2.3")

        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "my-app/compose.yaml"

        content = compose.read_text()
        assert "ghcr.io/org/my-app:1.2.3" in content
        assert 'x-spiri-config-version: "1.2.3"' in content or "x-spiri-config-version: 1.2.3" in content

    def test_leaves_non_matching_images_untouched(self, tmp_path):
        compose = tmp_path / "other-app" / "compose.yaml"
        write_compose(
            compose,
            """\
            services:
              app:
                image: ghcr.io/org/other-app:9.9.9
            """,
        )

        result = run_bump(tmp_path, "ghcr.io/org/my-app", "1.2.3")

        assert result.returncode == 1
        assert "No compose.yaml" in result.stderr
        assert "ghcr.io/org/other-app:9.9.9" in compose.read_text()

    def test_bumps_multiple_matching_files_under_search_root(self, tmp_path):
        write_compose(
            tmp_path / "debug-ui" / "compose.yaml",
            """\
            services:
              app:
                image: ghcr.io/org/my-app:1.0.0
            """,
        )
        write_compose(
            tmp_path / "headless" / "compose.yaml",
            """\
            services:
              app:
                image: ghcr.io/org/my-app:1.0.0
            """,
        )
        write_compose(
            tmp_path / "unrelated" / "compose.yaml",
            """\
            services:
              app:
                image: ghcr.io/org/unrelated:1.0.0
            """,
        )

        result = run_bump(tmp_path, "ghcr.io/org/my-app", "2.0.0")

        assert result.returncode == 0, result.stderr
        changed = sorted(result.stdout.strip().split(","))
        assert changed == ["debug-ui/compose.yaml", "headless/compose.yaml"]
        assert "ghcr.io/org/my-app:2.0.0" in (tmp_path / "debug-ui" / "compose.yaml").read_text()
        assert "ghcr.io/org/my-app:2.0.0" in (tmp_path / "headless" / "compose.yaml").read_text()
        assert "ghcr.io/org/unrelated:1.0.0" in (tmp_path / "unrelated" / "compose.yaml").read_text()

    def test_only_bumps_service_matching_image_within_a_file(self, tmp_path):
        compose = tmp_path / "compose.yaml"
        write_compose(
            compose,
            """\
            services:
              app:
                image: ghcr.io/org/my-app:1.0.0
              sidecar:
                image: ghcr.io/org/unrelated:5.0.0
            """,
        )

        result = run_bump(tmp_path, "ghcr.io/org/my-app", "1.1.0")

        assert result.returncode == 0, result.stderr
        content = compose.read_text()
        assert "ghcr.io/org/my-app:1.1.0" in content
        assert "ghcr.io/org/unrelated:5.0.0" in content

    def test_preserves_other_compose_content(self, tmp_path):
        compose = tmp_path / "compose.yaml"
        write_compose(
            compose,
            """\
            x-spiri-config-version: "0.9.0"
            services:
              app:
                image: ghcr.io/org/my-app:1.0.0
                restart: unless-stopped
                environment:
                  - LOG_LEVEL=INFO
                labels:
                  spiriconfig.plugin.name: my-app
            """,
        )

        result = run_bump(tmp_path, "ghcr.io/org/my-app", "1.1.0")

        assert result.returncode == 0, result.stderr
        content = compose.read_text()
        assert "restart: unless-stopped" in content
        assert "LOG_LEVEL=INFO" in content
        assert "spiriconfig.plugin.name: my-app" in content

    def test_v_prefix_is_stripped_from_version(self, tmp_path):
        compose = tmp_path / "compose.yaml"
        write_compose(
            compose,
            """\
            services:
              app:
                image: ghcr.io/org/my-app:1.0.0
            """,
        )

        result = run_bump(tmp_path, "ghcr.io/org/my-app", "v3.4.5")

        assert result.returncode == 0, result.stderr
        content = compose.read_text()
        assert "ghcr.io/org/my-app:3.4.5" in content
        assert "v3.4.5" not in content
