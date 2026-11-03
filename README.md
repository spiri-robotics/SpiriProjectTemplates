# SpiriProjectTemplates

The copier template every Spiri project follows, so they stay consistent: one layout, one set of
tools and CI, docs as a controlled document like every Spiri manual, and versions that update in
one place for all of them.

It makes four kinds of project:

| Kind | Ships | Example |
| --- | --- | --- |
| `app` | a docker image, run on the robot (GHCR) | SpiriCamera, SpiriMav |
| `library` | a package on PyPI | SpiriSynq |
| `both` | an image and a PyPI package | SpiriConfig |
| `stack` | several images and compose apps; no Python package | SpiriDevelopmentKit |

## Starting a Project

```console
uvx copier copy gh:spiri-robotics/SpiriProjectTemplates ./SpiriSensor
cd SpiriSensor
uv sync          # creates uv.lock; commit it, CI and the Dockerfile need it
make check       # what CI runs
git init && git add -A && git commit -m "feat: generate from SpiriProjectTemplates"
```

Then on GitHub, once:

- **Settings → Pages → Source: GitHub Actions**, so the docs publish.
- **Settings → Actions → General → Allow GitHub Actions to create and approve pull requests**,
  for the weekly template update.

## Bringing an Existing Project onto the Template

Answer `scaffold: no` (a `stack` never scaffolds): the project keeps its own code and gets the
template's config, CI and docs.

1. On a branch, move the package under `src/` if it isn't already (`git mv Pkg src/Pkg`). Every
   project uses that layout.
2. Apply the template over the checkout:
   `uvx copier copy --overwrite gh:spiri-robotics/SpiriProjectTemplates .`
3. Go through `git status` file by file:
   - **Take the template's**: workflows, `Makefile`, `.vale.ini`, `styles/`, `docs/_static/`,
     `docs/revisions.md`, `revisions.yaml`, `.copier-answers.yml`.
   - **Keep the project's** (`git checkout -- <file>`): `README.md`, `CHANGES.md`, docs prose.
   - **Merge**: `pyproject.toml` (the project's dependencies and scripts, the template's tooling
     sections), `AGENTS.md` (the project's knowledge, the template's conventions),
     `docs/index.md` (the template's document-control cover, the project's chapters),
     `docs/conf.py`, `.gitignore`.
   - **Delete what the template replaces**: `.readthedocs.yaml`, `docs/requirements.txt`, old
     publish workflows, `docs/index.rst`.
4. `make check`. Expect ruff to have opinions about code that never had a linter: format and fix
   in their own commit, so the adoption diff stays readable.

After that, the project's own weekly `template-update.yml` keeps it current.

## Keeping Projects Current

Projects pull the template's latest **release** (tag), not `main`:

```console
uvx copier update
uv lock
```

Every project runs this weekly by itself (`.github/workflows/template-update.yml`) and opens a
PR: a draft, listing the files, if the template and the project changed the same lines.

The template releases itself: every push to `main` that passes Template Tests is tagged as the
next patch version (`.github/workflows/release.yml`). Tag a minor or major version by hand for
bigger changes.

## Questions

| Variable | Default | Description |
| --- | --- | --- |
| `project_name` | `SpiriExample` | Project and repo name; also the CLI command |
| `python_package_name` | from `project_name`, CamelCase | Import name: `SpiriSensor` stays as is, `my-sensor` becomes `MySensor` |
| `python_version` | `3.13` | Minimum Python version |
| `description`, `version` | | One-line description; starting version |
| `author_name`, `author_email` | empty | Package authors |
| `github_org` | `spiri-robotics` | Where the repo lives, for the docs URL and image name |
| `license` | `MIT` | `MIT`, `Apache-2.0`, `BSD-3-Clause` or `GPL-3.0-or-later` |
| `kind` | `app` | `app`, `library`, `both` or `stack` (above) |
| `scaffold` | yes | Starter code (package, CLI, tests). No when adopting an existing project |
| `spirisynq` | yes for apps | Depend on SpiriSynq; apps join the `spirisynq` docker network |
| `spiri_config_plugin` | no | Apps: a NiceGUI web UI served as a SpiriConfig container plugin |
| `include_tests` | yes | pytest in CI; with starter code, example tests |
| `include_docs` | yes | Sphinx docs as a controlled document (below) |
| `document_number`, `audience`, `distribution_statement`, `use_spiri_brand`, `use_vale` | | The docs questions, with spiri-docs-tooling's names and meanings |
| `include_nix` | yes | `nix/flake.nix` dev shell |

## What You Get

```
SpiriSensor/
├── pyproject.toml          # hatchling (or a tooling-only project for a stack); ruff; dev and docs groups
├── Makefile                # check / lint / format / test / docs / pdf / lint-docs / docker
├── AGENTS.md               # commands and conventions, for people and agents
├── CHANGES.md              # categorized entries under "## Unreleased"
├── .copier-answers.yml     # lets `copier update` pull template changes
├── revisions.yaml          # the docs' revision history: document number, revisions, approvals
├── .vale.ini, styles/      # prose linting: Microsoft style, Spiri vocabulary
├── src/SpiriSensor/
│   ├── cli.py              # typer: version (run for apps, web with the plugin)
│   ├── main.py             # apps: pydantic-settings Settings (SPIRISENSOR_*), SpiriSynq session, serve()
│   └── web.py              # NiceGUI page (spiri_config_plugin)
├── tests/
├── docs/                   # Sphinx + MyST + furo + spiri-docs
├── docker/                 # apps: Dockerfile (builder, dev, runtime) and compose files
├── .github/workflows/
│   ├── lint-test.yml       # ruff, pytest (and pytest in the image)
│   ├── docs.yml            # HTML to Pages, the controlled PDF, Vale
│   ├── docker-publish.yml  # apps: image to GHCR
│   ├── pypi-publish.yml    # libraries: package to PyPI (trusted publishing)
│   └── template-update.yml # weekly `copier update` PR
├── .devcontainer/          # apps
└── nix/flake.nix
```

## SpiriSynq

With `spirisynq` (the default for apps), the app is wired the way SpiriCamera and SpiriMav are:

- it depends on `spirisynq`, and `main.serve()` opens a client session on
  `SPIRISENSOR_ZENOH_CONNECT` when that's set;
- `docker/compose.yaml` puts it on the external `spirisynq` network with
  `ZENOH_CONNECT=tcp/zenoh-router:7447`, so the zenoh-router app bridges it to the rest of
  SpiriSynq (a docker bridge doesn't pass multicast scouting);
- the host's `/etc/hostname` is mounted at `/etc/spirisynq_base_topic`, so SpiriSynq names
  objects after the robot, not the container.

## SpiriConfig Plugin

With `spiri_config_plugin`, `docker/compose.yaml` gets a second service, `ui`, that runs
`SpiriSensor web` (NiceGUI on port 8080) with the `spiriconfig.plugin.*` labels. SpiriConfig
discovers it from those labels and proxies it into its shell. That's a
[container plugin](https://github.com/spiri-robotics/SpiriConfig/blob/main/docs/container-plugins.md),
so it doesn't share SpiriConfig's interpreter or dependency pins.

## Docs

Every project's docs are a controlled document, built with the same
[spiri-docs](https://github.com/spiri-robotics/spiri-docs-tooling) extension and house theme as
every Spiri manual. `revisions.yaml` is the single source of the document number, revision and
approvals: spiri-docs fills the cover from it, stamps it into the PDF footer, names the PDF after
it, and fails the build if a regulator-facing revision has no approver.

`.github/workflows/docs.yml`:

- builds the HTML on every PR with `sphinx-build -W` (warnings are errors) and publishes it to
  GitHub Pages from `main`, at `https://<github_org>.github.io/<project_name>/`;
- builds the PDF with LaTeX on every run, and attaches it to the release on a `vX.Y.Z` tag. That
  release asset is the controlled copy; it says DRAFT if the revision is one;
- checks prose with Vale (Microsoft style, Spiri vocabulary). Advisory: it never blocks.

The document's revision is separate from the software's version: revise it when what the docs
say changes. Locally: `make docs`, `make pdf` (needs LaTeX), `make lint-docs` (needs Vale).

## Keeping Dependencies Current

The template owns the versions it ships: the dependency minimums in `pyproject.toml`, the action
versions in the workflows, and the uv image in the Dockerfile. Projects get new ones by pulling
the template, not from per-project bots:

```console
uvx copier update
uv lock
```

Every Monday, `.github/workflows/update-template.yml` runs `scripts/update_template.py` to bump
all of them (and the template's own `uv.lock` and actionlint) to their latest releases. It then
runs the full test suite, every combo, slow and docker included, and opens or refreshes a single
PR, `chore(deps): update template dependencies`, with a table of what changed. If the tests
fail, the PR opens as a draft with the failures in its description: a bump that needs template
changes too. Run it on demand from the Actions tab (**Run workflow**).

Two deliberate exceptions: the Python base image and `requires-python` are never bumped. A new
Python is an upgrade to decide on.

One-time setup:

- **Settings → Actions → General → Allow GitHub Actions to create and approve pull requests.**
- Optionally, a `TEMPLATE_UPDATE_TOKEN` secret: a fine-grained token with contents and
  pull-requests write on this repo. PRs opened with the default token don't trigger other
  workflows, so without it the PR only carries the update job's own test result.

## Docker Image Publishing

`.github/workflows/docker-publish.yml` builds the image on every PR without pushing it. It pushes
on every push to `main` (tagged `edge`) and on version tags matching `v*.*.*` (tagged with the
semver, e.g. `1.2.3` and `1.2`, and `latest`).

It publishes to GHCR by default using the built-in `GITHUB_TOKEN`, so there's nothing to set up.
To publish elsewhere instead, set repository variables (**Settings → Secrets and variables →
Actions → Variables**) without editing the workflow:

- `REGISTRY`: e.g. `docker.io` (default: `ghcr.io`)
- `IMAGE_NAME`: e.g. `myorg/my-project` (default: the GitHub repo name, lowercased)

If `REGISTRY` is `docker.io`, also add `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets.

### Getting Releases into an App Store

The generated project doesn't touch any app store itself, so it needs no credentials for one.
Instead, the app store tracks the published image with Dependabot, which opens a version-bump PR
there whenever a new release tag appears:

```yaml
# .github/dependabot.yml, in the app store repo
version: 2
updates:
  - package-ecosystem: docker-compose
    directories: ["/my-project*"]
    schedule:
      interval: daily
```

For this to work:

- Each app's `compose.yaml` pins a version tag (`ghcr.io/my-org/my-project:1.2.3`), not `:latest`. Dependabot only bumps version tags.
- The image is public, or the app store's Dependabot config has a registry credential for it.
- Leave `x-spiri-config-version` out of those apps. Dependabot won't update it, and without it [SpiriConfig](https://github.com/spiri-robotics/SpiriConfig/blob/main/docs/appstore.md) shows the date of the last commit that touched the app, which the bump PRs keep current.

## Working on the Template

Every test generates real projects with copier, from this checkout (uncommitted changes
included), in six option combos: `minimal`, `default`, `library`, `stack`, `adopted` (no starter
code) and `full`.

```console
uv sync
uv run pytest              # fast: files per option, parsing, ruff, actionlint, copier update
uv run pytest -m slow      # each project's uv sync, pytest, docs, PDF and Vale (needs network;
                           # the PDF and Vale tests skip without LaTeX and Vale installed)
uv run pytest -m docker    # each project's image build, and its tests run in the image
uv run pytest -m slow -k full   # one combo
```

CI (`.github/workflows/test-template.yml`) runs them all: fast on every push, and the slow and
docker tests per combo. A change to the template isn't done until a generated project passes its
own CI.
