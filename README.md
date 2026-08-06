# tf-sheriff

The org-wide source of truth for how PDS/PDC repositories write Terraform, plus a validator that enforces the checkable parts of it. Keeps the peace in `terraform/` — flags what's out of line, doesn't pretend to catch everything (see [What this does NOT do](#what-this-does-not-do)).

- **[`TERRAFORM_GUIDELINES.md`](./TERRAFORM_GUIDELINES.md)** — Must-Have requirements and Should-Have recommendations, with rationale, HashiCorp/AWS/PDS citations, and copy-paste code examples. Grew out of the org's "State of Terraform" audit across `pdc-cds-infra`, `registry`, `web-analytics`, `pdc-observability`, and the shared `pds-tf-modules`/template repos.
- **The validator** — a dependency-free Python check that statically verifies a `terraform/` directory against the mechanically-checkable Must-Haves (error) and Should-Haves (warning). Shipped two ways (see [Two ways to use the validator](#two-ways-to-use-the-validator)).


## Prerequisites

**Python 3.9+.** No third-party dependencies at runtime — only the `dev` extras (linting, tests) require anything beyond the standard library.


## User Quickstart

Install with:

```bash
pip install tf-sheriff
```

Run it against a `terraform/` directory:

```bash
tf-sheriff path/to/terraform/
```

Machine-readable output for tooling:

```bash
tf-sheriff path/to/terraform/ --json
```

GitHub Actions PR annotations:

```bash
tf-sheriff path/to/terraform/ --github
```

Exit codes: `0` clean, `1` Must-Have failure (or any warning with `--strict`), `2` usage/path error.


## Two ways to use the validator

**As a package** (this repo installed via pip): use the `tf-sheriff` console script above.

**Vendored, no install required**: copy `scripts/validate_terraform.py` into a consuming repo and call it directly — it has zero third-party dependencies by design, so it doesn't force a `pip install` into someone else's CI:

```bash
python3 scripts/validate_terraform.py terraform/ --github
```

Add it as a CI step, e.g. in `terraform_cicd.yaml`:

```yaml
- name: Validate Terraform conventions
  run: python3 scripts/validate_terraform.py terraform/ --github
```

If a specific check is a known, tracked exception for that repo, add a `.tfvalidate-ignore` file at the repo root or next to `terraform/` — see [`.tfvalidate-ignore.example`](./.tfvalidate-ignore.example).

Both distribution paths run the exact same logic — `src/pds/tf_sheriff/validator.py` (the package copy) and `scripts/validate_terraform.py` (the standalone copy) are kept byte-for-byte identical, enforced by a test (see `CLAUDE.md`).


## What this does NOT do

The validator only checks organizational convention (structure, state config, tagging, naming, version pinning) — it is not a substitute for `terraform validate`, TFLint, or Checkov, and it explicitly reports (rather than silently skips) the Must-Haves it cannot verify statically: repo ownership boundaries, semantic naming quality, runtime auth behavior, least-privilege IAM, and a handful of Should-Have backlog items. Those need a human reviewer — see the Terraform section of the [org PR template](https://github.com/NASA-PDS/.github/blob/main/.github/pull_request_template.md).


## Code of Conduct

All users and developers of the NASA-PDS software are expected to abide by our [Code of Conduct](https://github.com/NASA-PDS/.github/blob/main/CODE_OF_CONDUCT.md). Please read this to ensure you understand the expectations of our community.


## Development

For information on how to contribute to NASA-PDS codebases please take a look at our [Contributing guidelines](https://github.com/NASA-PDS/.github/blob/main/CONTRIBUTING.md).

### Installation

Install in editable mode with the dev dependencies:

```bash
pip install --editable '.[dev]'
```

Make a baseline for any secrets (email addresses, passwords, API keys, etc.) in the repository:

```bash
scripts/detect_secrets_baseline.sh scan
```

Review and classify each detected secret (mark as `is_secret: true/false`):

```bash
scripts/detect_secrets_baseline.sh audit
```

Commit the baseline:

```bash
git add .secrets.baseline
```

Then configure the `pre-commit` hooks:

```bash
pre-commit install
pre-commit install -t pre-push
pre-commit install -t prepare-commit-msg
pre-commit install -t commit-msg
```

### Testing

```bash
pytest              # run all tests
tox -e lint          # run all linters (flake8, mypy, pre-commit hooks)
tox                  # full build: tests + lint
```

### Logs

Runtime output in `pds.tf_sheriff` uses `print()` deliberately — this is a CLI tool whose entire job is producing stdout for a human or CI to read, not a service that should route through `logging`.


## Build

```bash
pip install build
python -m build .
```


## Publication

NASA PDS packages publish automatically using the [Roundup Action](https://github.com/NASA-PDS/roundup-action). `unstable-cicd.yaml` runs on push to `main` and publishes a SNAPSHOT release to Test PyPI; `stable-cicd.yaml` runs on push of a `release/<version>` tag and publishes to PyPI.


## Related

- Claude Code skill: `terraform-conventions`, packaged in [`NASA-PDS/pds-agent-skills`](https://github.com/NASA-PDS/pds-agent-skills) — primes an AI agent with `TERRAFORM_GUIDELINES.md` and runs the validator before calling Terraform work done.
- Companion "State of Terraform" report — the empirical audit this document is based on.
