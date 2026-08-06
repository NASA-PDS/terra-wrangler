# tf-sheriff

The org-wide source of truth for how PDS/PDC repositories write Terraform, plus a validator that enforces the checkable parts of it. Keeps the peace in `terraform/` — flags what's out of line, doesn't pretend to catch everything (see [What this does NOT do](#what-this-does-not-do)).

- **[`TERRAFORM_GUIDELINES.md`](./TERRAFORM_GUIDELINES.md)** — Must-Have requirements and Should-Have recommendations, with rationale, HashiCorp/AWS citations, and copy-paste code examples. Grew out of the org's "State of Terraform" audit across `pdc-cds-infra`, `registry`, `web-analytics`, `pdc-observability`, and the shared `pds-tf-modules`/template repos.
- **[`scripts/validate_terraform.py`](./scripts/validate_terraform.py)** — a dependency-free Python script that statically checks a `terraform/` directory against the mechanically-checkable Must-Haves (error) and Should-Haves (warning). Run it locally, in pre-commit, or in CI.

## Quick start

```bash
python3 scripts/validate_terraform.py path/to/terraform/
```

Machine-readable output for tooling:

```bash
python3 scripts/validate_terraform.py path/to/terraform/ --json
```

GitHub Actions PR annotations:

```bash
python3 scripts/validate_terraform.py path/to/terraform/ --github
```

Exit codes: `0` clean, `1` Must-Have failure (or any warning with `--strict`), `2` usage/path error.

## Using this in another repo

Vendor `scripts/validate_terraform.py` (and ideally a copy or symlink of `TERRAFORM_GUIDELINES.md`) into the consuming repo, then add a step to its `terraform_cicd.yaml`:

```yaml
- name: Validate Terraform conventions
  run: python3 scripts/validate_terraform.py terraform/ --github
```

If a specific check is a known, tracked exception for that repo, add a `.tfvalidate-ignore` file at the repo root or next to `terraform/` — see [`.tfvalidate-ignore.example`](./.tfvalidate-ignore.example).

## What this does NOT do

The validator only checks organizational convention (structure, state config, tagging, naming, version pinning) — it is not a substitute for `terraform validate`, TFLint, or Checkov, and it explicitly reports (rather than silently skips) the Must-Haves it cannot verify statically: repo ownership boundaries, semantic naming quality, runtime auth behavior, least-privilege IAM, and a handful of Should-Have backlog items. Those need a human reviewer — see the Terraform section of the org PR template.

## Related

- Claude Code skill: `terraform-conventions`, packaged in [`NASA-PDS/pds-agent-skills`](https://github.com/NASA-PDS/pds-agent-skills) — primes an AI agent with this document and runs the validator before calling Terraform work done.
- Companion "State of Terraform" report — the empirical audit this document is based on.
