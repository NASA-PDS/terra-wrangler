# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

terra-wrangler is two things in one repo:

1. **`TERRAFORM_GUIDELINES.md`** — the org's living Must-Have/Should-Have Terraform Development Guidelines for PDS/PDC repos.
2. **A validator** — a static checker for the mechanically-checkable subset of those guidelines, shipped two ways: a dependency-free standalone script (`scripts/validate_terraform.py`) meant to be vendored into another repo's CI, and an installable package (`pds.terra_wrangler`, console script `terra-wrangler`).

Built from NASA-PDS's `template-repo-python`, trimmed down for a single-purpose CLI tool (no Sphinx docs build — see [Deviations from the template](#deviations-from-the-template)).

## Commands

### Setup

```bash
python -m venv venv
source venv/bin/activate
pip install --editable '.[dev]'
```

Or via tox:

```bash
tox --devenv venv -e dev
```

### Running the validator

```bash
terra-wrangler path/to/terraform/                 # after pip install
python3 scripts/validate_terraform.py path/to/terraform/   # standalone, no install needed
```

Flags: `--json`, `--github` (GitHub Actions annotations), `--strict` (Should-Have warnings also fail).

### Testing

```bash
pytest                                              # run all tests
pytest tests/pds/terra_wrangler/test_validate_terraform.py
pytest -k "test_name"
ptw                                                  # watch mode
```

`test_standalone_script_matches_package_module` fails if `scripts/validate_terraform.py` and `src/pds/terra_wrangler/validator.py` drift apart — **when you edit the validator logic, edit `src/pds/terra_wrangler/validator.py` and then copy it verbatim over `scripts/validate_terraform.py`** (or vice versa), don't hand-edit both independently.

### Linting

```bash
tox -e lint                   # all linters (flake8, mypy, pre-commit hooks)
flake8 src
mypy src
```

### Full build (tests + lint)

```bash
tox
```

### Secrets detection

```bash
scripts/detect_secrets_baseline.sh scan   # regenerate .secrets.baseline
scripts/detect_secrets_baseline.sh audit  # interactively review/classify detected secrets
scripts/detect_secrets_baseline.sh        # check for new secrets vs baseline (run by pre-commit)
```

## Architecture

### Package layout

```
terra-wrangler/
├── TERRAFORM_GUIDELINES.md          # the guidelines document itself
├── .tfvalidate-ignore.example       # example tracked-exception file for consumers
├── scripts/validate_terraform.py    # standalone, vendorable copy of the validator
├── src/pds/terra_wrangler/
│   ├── __init__.py                  # version, read from VERSION.txt
│   ├── VERSION.txt
│   ├── main.py                      # `terra-wrangler` console script entry point
│   └── validator.py                 # canonical validator implementation (== scripts/validate_terraform.py)
└── tests/pds/terra_wrangler/
    └── test_validate_terraform.py   # functional tests + the drift guard above
```

Source lives under `src/pds/terra_wrangler/` using a [PEP 420 namespace package](https://peps.python.org/pep-0420/) (`src/pds/__init__.py` is intentionally minimal), matching every other PDS Python package's `pds.*` namespace.

### Why the validator is duplicated on purpose

Most consuming repos will just copy `scripts/validate_terraform.py` into their own `scripts/` directory and call it from CI — no `pip install` required, since the script has zero third-party dependencies. Repos that already manage a Python environment can instead `pip install terra-wrangler` and use the `terra-wrangler` console script. Both need to run the same logic, so `src/pds/terra_wrangler/validator.py` and `scripts/validate_terraform.py` are kept byte-for-byte identical; `test_standalone_script_matches_package_module` enforces that with `filecmp`.

### CI/CD

Two standard GitHub Actions workflows drive releases via [NASA-PDS/roundup-action](https://github.com/NASA-PDS/roundup-action):

- **`unstable-cicd.yaml`** — triggers on push to `main`; publishes a SNAPSHOT release to Test PyPI
- **`stable-cicd.yaml`** — triggers on push to `release/<version>` branches; publishes stable releases to PyPI
- **`branch-cicd.yaml`** — runs `tox` on every other branch push
- **`secrets-detection.yaml`** — runs `scripts/detect_secrets_baseline.sh` on push/PR to `main`
- **`codeql-analysis.yml`** — weekly CodeQL scan

Required repository secrets: `ADMIN_GITHUB_TOKEN`, `TEST_PYPI_USERNAME`/`TEST_PYPI_PASSWORD` (unstable), `PYPI_USERNAME`/`PYPI_PASSWORD` (stable), `SONAR_TOKEN`.

### Code style

- **flake8** enforces PEP8 + docstrings (Google convention) + bugbear; max line length 120
- **mypy** enforces type annotations across `src/`
- Pre-commit hooks run mypy + flake8 + detect-secrets on commit; pytest runs on push

## Deviations from the template

- **No Sphinx docs build.** `template-repo-python` wires up a `docs` tox env and Sphinx dev dependency; terra-wrangler dropped both since the guidelines document and README are the documentation — there's no API surface worth generating reference docs for. If that changes (e.g. the package grows beyond one CLI), reintroduce `docs/source/` and the `sphinx`/`sphinx-rtd-theme` deps from the template.
- **No `terraform/` or `docker/` directories**, so the corresponding `dependabot.yml` ecosystem entries from the template were dropped (they'd point at directories that don't exist).

`python_requires` matches the template default (`>= 3.13`) — the validator itself is pure-stdlib and would run fine on older interpreters, but this repo follows the org standard rather than carving out an exception. If terra-wrangler needs to run inside another repo's CI on an older pinned Python, use the vendored `scripts/validate_terraform.py` copy directly with whatever `python3` is on that runner rather than relying on the packaged `terra-wrangler` console script (which is installed by whatever environment invokes `pip install terra-wrangler`, not constrained by this repo's own `python_requires`).
