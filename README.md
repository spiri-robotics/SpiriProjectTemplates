# SpiriProjectTemplates

Copier template for generating Spiri projects — Python packages with Docker composable deployment, CLI interfaces, and optional SpiriConfig plugin support.

## Quick Start

Install copier:

```console
uv tool install copier
```

Generate a new project:

```console
copier copy https://github.com/spiri-robotics/SpiriProjectTemplates ./my-project
```

Or with explicit variables:

```console
copier copy https://github.com/spiri-robotics/SpiriProjectTemplates ./my-project \\
  --data="project_name=my-sensor" \\
  --data="spiri_config_plugin=true" \\
  --data="include_docs=true" \\
  --data="author_name=Your Name"
```

After generation:

```console
cd my-project
uv sync
uv lock
my-sensor --help
```

## Variables

| Variable | Type | Default | Description |
| --- | --- | --- | --- |
| `project_name` | str | `"my-spiri-project"` | Project/package name (e.g. `my-sensor-pipeline`) |
| `python_version` | str | `"3.13"` | Minimum Python version |
| `python_package_name` | str | `""` | Python package name. Auto-populated from `project_name` when left blank. |
| `description` | str | `"A Spiri project"` | Short one-line project description |
| `version` | str | `"0.1.0"` | Starting version |
| `author_name` | str | `""` | Author name |
| `author_email` | str | `""` | Author email |
| `license` | str | `"MIT"` | Software license. Choices: `MIT`, `Apache-2.0`, `BSD-3-Clause`, `GPL-3.0-or-later` |
| `spiri_config_plugin` | bool | `false` | Generate a SpiriConfig plugin interface (entry point, web UI, compose labels)? |
| `include_tests` | bool | `true` | Include `tests/` directory with pytest setup? |
| `include_docs` | bool | `false` | Include `docs/` directory with Sphinx setup? |
| `include_nix` | bool | `true` | Include `nix/flake.nix` for reproducible builds? |

## Generated Structure

```
my-project/
├── pyproject.toml          # Python project config (Hatchling)
├── README.md
├── .python-version
├── .gitignore
│
├── src/
│   └── my_project/         # Python package from python_package_name
│       ├── __init__.py
│       ├── cli.py          # Typer CLI app
│       ├── main.py         # Main entry point with pydantic-settings
│       └── web.py          # NiceGUI web page (conditional)
│
├── docker/
│   ├── Dockerfile
│   ├── compose.yaml        # Production: pulls image from registry
│   ├── compose.dev.yaml    # Development: builds from source + mounts src/
│   └── compose.test.yaml   # CI: runs pytest inside container
│
├── docker/
│   └── Dockerfile          # Multi-stage build (builder → runtime)
│
├── tests/                  # Conditional
│   ├── __init__.py
│   └── test_cli.py
│
├── docs/                   # Conditional
│   └── index.md
│
├── nix/                    # Conditional
│   └── flake.nix
│
├── .vscode/
│   ├── launch.json         # Run + Debug configurations
│   └── settings.json       # Python path to .venv
│
└── .devcontainer/
    └── devcontainer.json   # VSCode dev container (docker-in-docker)
```

## SpiriConfig Plugin Mode

Set `spiri_config_plugin=true` to generate a SpiriConfig-compatible plugin:

- **pyproject.toml**: Registers a `spiriconfig.plugins` entry point under the project name
- **compose.yaml**: Adds `spiriconfig.plugin.*` labels for discovery
- **web.py**: Includes a NiceGUI web UI page with status/configuration cards
- **pyproject.toml**: Adds `rich` and optional `nicegui` dependencies

The generated plugin follows SpiriConfig conventions:

- CLI via `typer.Typer`
- Web UI via `nicegui` (in `page()`)
- Settings via `pydantic_settings` with `{PACKAGE}_` env prefix
- Logging via `loguru` with `plugin="{package_name}"`

To run as a SpiriConfig plugin:

```console
cd my-project
uv sync
docker compose -f docker/compose.yaml -f docker/compose.dev.yaml up --build
docker compose -f docker/compose.yaml -f docker/compose.dev.yaml ps
```

## Docker Compose Split

The template uses the same pattern as SpiriConfig for managing deployments:

### Production (`compose.yaml`)

Pulls a published image from a registry:

```console
docker compose -f docker/compose.yaml up -d
```

Variables:
- `COMPONENT_IMAGE` — registry-qualified image name (e.g. `my-registry.com/my-sensor:v1.0.0`)
- `GREETING` — runtime greeting message
- `ENVIRONMENT` — `production`, `development`, `test`
- `LOG_LEVEL` — logging verbosity

### Development (`compose.dev.yaml`)

Builds from local source and mounts `src/` for hot-reloading:

```console
docker compose -f docker/compose.yaml -f docker/compose.dev.yaml up --build
```

- Overrides `image` to `:dev` tag
- Mounts `./src:/app/src:ro` for live code changes
- Sets `ENVIRONMENT=development` and `LOG_LEVEL=DEBUG`

### Testing (`compose.test.yaml`)

Runs pytest inside the container to catch environment differences from local dev:

```console
docker compose -f docker/compose.yaml -f docker/compose.test.yaml run --rm test
```

### Combined Development + Testing

```console
docker compose -f docker/compose.yaml -f docker/compose.dev.yaml -f docker/compose.test.yaml run test
```

## VSCode Integration

### Local Development

The `.vscode/` directory provides:
- **launch.json**: Two configurations — `Run` (standard) and `Debug` (with DEBUG env)
- **settings.json**: Points Python interpreter to `.venv`, configures pytest

### Remote Development (Dev Container)

The `.devcontainer/devcontainer.json` configures VSCode to develop inside a container that mirrors a real Spiri robot:

1. Uses `compose.dev.yaml` to build the same image that ships to production
2. Includes Docker-in-Docker for SpiriConfig and other tools
3. Forwards port 8337 for SpiriConfig web UI access
4. Runs `uv sync --no-dev` on container creation

To use:
1. Open the project in VSCode
2. Click "Reopen in Container" when prompted
3. Or: **Ctrl+Shift+P** → "Remote-Containers: Reopen in Container"

## Nix Development Environment

When `include_nix=true`, a `flake.nix` provides a reproducible development shell:

```console
nix develop
# Runs uv sync and sets PYTHONPATH=src/
```

The shell includes `python313`, `uv`, `pytest`, `pytest-asyncio`, and `pytest-cov`.

## Updates

After initial generation, the project tracks its template origin. To update from a newer template version:

```console
cd my-project
copier update  # Uses answers stored in .copier-answers.yaml
```

## License

Template code is available under the same license as your generated project. Choose your license when copying.
