# encoding: utf-8
"""Tests for pds.tf_sheriff.validator."""
import filecmp
import textwrap
import unittest
from pathlib import Path

from pds.tf_sheriff import validator


REPO_ROOT = Path(__file__).resolve().parents[3]


COMPLIANT_MAIN_TF = textwrap.dedent(
    """\
    provider "aws" {
      region = "us-west-2"
      default_tags {
        tags = {
          tenant    = "en"
          venue     = "pds-cds-dev"
          component = "example"
          managedby = "pds-operator@jpl.nasa.gov"
          cicd      = "iac"
        }
      }
    }

    resource "aws_s3_bucket" "logs" {
      bucket = "pds-dev-example-logs"
    }
    """
)

COMPLIANT_VARIABLES_TF = textwrap.dedent(
    """\
    variable "venue" {
      type        = string
      description = "Deployment venue: dev, test, or prod."
    }
    """
)

COMPLIANT_VERSIONS_TF = textwrap.dedent(
    """\
    terraform {
      required_version = ">= 1.9.0"
      required_providers {
        aws = {
          source  = "hashicorp/aws"
          version = "~> 6.0"
        }
      }
    }
    """
)

COMPLIANT_BACKEND_TF = textwrap.dedent(
    """\
    terraform {
      backend "s3" {
      }
    }
    """
)

COMPLIANT_BACKEND_DEV_HCL = textwrap.dedent(
    """\
    bucket       = "pds-dev-infra"
    key          = "example/terraform.tfstate"
    region       = "us-west-2"
    use_lockfile = true
    """
)


def _write_compliant_module(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "main.tf").write_text(COMPLIANT_MAIN_TF)
    (root / "variables.tf").write_text(COMPLIANT_VARIABLES_TF)
    (root / "outputs.tf").write_text('output "bucket" {\n  description = "The bucket."\n  value = aws_s3_bucket.logs.id\n}\n')
    (root / "versions.tf").write_text(COMPLIANT_VERSIONS_TF)
    (root / "backend.tf").write_text(COMPLIANT_BACKEND_TF)
    (root / "backend-dev.hcl").write_text(COMPLIANT_BACKEND_DEV_HCL)
    (root / "README.md").write_text("# example\n")
    (root / ".terraform.lock.hcl").write_text("# lock file stub\n")
    (root.parent / ".gitignore").write_text("*.tfstate\n.terraform/\n*.tfvars\n")


class ValidateTerraformTests(unittest.TestCase):
    """Tests for the validator's module-level checks."""

    def test_compliant_module_has_no_must_have_failures(self):
        """A module following every documented convention should report zero errors."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tf_root = Path(tmp) / "terraform"
            _write_compliant_module(tf_root)

            ignores = validator.load_ignores(tf_root)
            module_report = validator.check_module(tf_root, tf_root, ignores)
            repo_report = validator.check_repo_level(tf_root, ignores)

            errors = module_report.findings("error", "fail") + repo_report.findings("error", "fail")
            self.assertEqual([], errors, f"Unexpected Must-Have failures: {errors}")

    def test_missing_backend_is_a_must_have_failure(self):
        """A deployable module with no backend.tf should fail M5."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tf_root = Path(tmp) / "terraform"
            _write_compliant_module(tf_root)
            (tf_root / "backend.tf").unlink()

            ignores = validator.load_ignores(tf_root)
            report = validator.check_module(tf_root, tf_root, ignores)

            failed_ids = {c[0] for c in report.findings("error", "fail")}
            self.assertIn("M5", failed_ids)

    def test_tfvalidate_ignore_downgrades_a_failure_to_skip(self):
        """A check listed in .tfvalidate-ignore should be reported as skipped, not failed."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tf_root = Path(tmp) / "terraform"
            _write_compliant_module(tf_root)
            (tf_root / "backend.tf").unlink()
            (tf_root / ".tfvalidate-ignore").write_text("M5\n")

            ignores = validator.load_ignores(tf_root)
            report = validator.check_module(tf_root, tf_root, ignores)

            statuses = {c[0]: c[3] for c in report.checks}
            self.assertEqual("skip", statuses["M5"])


class StandaloneScriptSyncTests(unittest.TestCase):
    """Guards against the two distribution copies of the validator drifting apart.

    tf-sheriff ships the validator two ways: as an installable package
    (``pds.tf_sheriff.validator``) and as a single dependency-free file
    (``scripts/validate_terraform.py``) meant to be vendored into another
    repo's CI without a package install. Both must contain the same logic.
    """

    def test_standalone_script_matches_package_module(self):
        """scripts/validate_terraform.py must be identical to src/pds/tf_sheriff/validator.py."""
        standalone = REPO_ROOT / "scripts" / "validate_terraform.py"
        packaged = REPO_ROOT / "src" / "pds" / "tf_sheriff" / "validator.py"

        self.assertTrue(standalone.exists(), f"missing {standalone}")
        self.assertTrue(packaged.exists(), f"missing {packaged}")
        self.assertTrue(
            filecmp.cmp(standalone, packaged, shallow=False),
            "scripts/validate_terraform.py and src/pds/tf_sheriff/validator.py have drifted apart — "
            "keep them byte-for-byte identical (copy one over the other) or update this test if a "
            "deliberate divergence is introduced.",
        )


if __name__ == "__main__":
    unittest.main()
