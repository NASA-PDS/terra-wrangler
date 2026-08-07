# encoding: utf-8
"""Tests for pds.terra_wrangler.validator."""
import filecmp
import textwrap
import unittest
from pathlib import Path

from pds.terra_wrangler import validator


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

    module "data_bucket" {
      source      = "git@github.com:NASA-PDS/pds-tf-modules.git//terraform/modules/s3/bucket?ref=v1.2.0"
      bucket_name = "pds-dev-example-data"
      required_tags = local.tags
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
    (root / "outputs.tf").write_text(
        'output "bucket_name" {\n  description = "The S3 bucket name."\n  value = module.data_bucket.bucket_name\n}\n'
    )
    (root / "versions.tf").write_text(COMPLIANT_VERSIONS_TF)
    (root / "backend.tf").write_text(COMPLIANT_BACKEND_TF)
    (root / "backend-dev.hcl").write_text(COMPLIANT_BACKEND_DEV_HCL)
    (root / "README.md").write_text("# example\n")
    (root / ".terraform.lock.hcl").write_text("# lock file stub\n")
    (root / "tfvars").mkdir(exist_ok=True)
    (root / "tfvars" / "dev.tfvars.example").write_text('venue      = "dev"\ncomponent_name = "example"\n')
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
        """A deployable module with no backend.tf should fail A5."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tf_root = Path(tmp) / "terraform"
            _write_compliant_module(tf_root)
            (tf_root / "backend.tf").unlink()

            ignores = validator.load_ignores(tf_root)
            report = validator.check_module(tf_root, tf_root, ignores)

            failed_ids = {c[0] for c in report.findings("error", "fail")}
            self.assertIn("A5", failed_ids)

    def test_direct_s3_bucket_resource_is_a_must_have_failure(self):
        """A direct aws_s3_bucket resource in a deployable module should fail P20."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tf_root = Path(tmp) / "terraform"
            _write_compliant_module(tf_root)
            (tf_root / "main.tf").write_text(
                COMPLIANT_MAIN_TF + '\nresource "aws_s3_bucket" "bad" {\n  bucket = "bad-bucket"\n}\n'
            )

            ignores = validator.load_ignores(tf_root)
            report = validator.check_module(tf_root, tf_root, ignores)

            failed_ids = {c[0] for c in report.findings("error", "fail")}
            self.assertIn("P20", failed_ids)

    def test_direct_ec2_resource_is_a_must_have_failure(self):
        """A direct aws_instance resource in a deployable module should fail P21."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tf_root = Path(tmp) / "terraform"
            _write_compliant_module(tf_root)
            (tf_root / "main.tf").write_text(
                COMPLIANT_MAIN_TF + '\nresource "aws_instance" "bad" {\n  instance_type = "t3.micro"\n}\n'
            )

            ignores = validator.load_ignores(tf_root)
            report = validator.check_module(tf_root, tf_root, ignores)

            failed_ids = {c[0] for c in report.findings("error", "fail")}
            self.assertIn("P21", failed_ids)

    def test_iam_resource_outside_iam_module_is_a_must_have_failure(self):
        """An aws_iam_* resource declared in a non-iam root module should fail P19."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tf_root = Path(tmp) / "terraform"
            _write_compliant_module(tf_root)
            (tf_root / "main.tf").write_text(
                COMPLIANT_MAIN_TF + '\nresource "aws_iam_role" "bad" {\n  name = "bad"\n}\n'
            )

            ignores = validator.load_ignores(tf_root)
            report = validator.check_module(tf_root, tf_root, ignores)

            failed_ids = {c[0] for c in report.findings("error", "fail")}
            self.assertIn("P19", failed_ids)

    def test_iam_resources_isolated_in_standalone_iam_module_pass(self):
        """An aws_iam_* resource declared inside a standalone iam/ root module should not fail P19."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tf_root = Path(tmp) / "terraform"
            iam_root = tf_root / "iam"
            iam_root.mkdir(parents=True)
            (iam_root / "main.tf").write_text('resource "aws_iam_role" "app" {\n  name = "app"\n}\n')
            (iam_root / "backend.tf").write_text(COMPLIANT_BACKEND_TF)

            ignores = validator.load_ignores(iam_root)
            report = validator.check_module(iam_root, tf_root, ignores)

            failed_ids = {c[0] for c in report.findings("error", "fail")}
            self.assertNotIn("P19", failed_ids)

    def test_missing_tfvars_example_is_a_must_have_failure(self):
        """A backend-<venue>.hcl with no matching tfvars/<venue>.tfvars.example should fail P23."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tf_root = Path(tmp) / "terraform"
            _write_compliant_module(tf_root)
            (tf_root / "tfvars" / "dev.tfvars.example").unlink()

            ignores = validator.load_ignores(tf_root)
            report = validator.check_module(tf_root, tf_root, ignores)

            failed_ids = {c[0] for c in report.findings("error", "fail")}
            self.assertIn("P23", failed_ids)

    def test_tfvalidate_ignore_downgrades_a_failure_to_skip(self):
        """A check listed in .tfvalidate-ignore should be reported as skipped, not failed."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tf_root = Path(tmp) / "terraform"
            _write_compliant_module(tf_root)
            (tf_root / "backend.tf").unlink()
            (tf_root / ".tfvalidate-ignore").write_text("A5\n")

            ignores = validator.load_ignores(tf_root)
            report = validator.check_module(tf_root, tf_root, ignores)

            statuses = {c[0]: c[3] for c in report.checks}
            self.assertEqual("skip", statuses["A5"])


class StandaloneScriptSyncTests(unittest.TestCase):
    """Guards against the two distribution copies of the validator drifting apart.

    terra-wrangler ships the validator two ways: as an installable package
    (``pds.terra_wrangler.validator``) and as a single dependency-free file
    (``scripts/validate_terraform.py``) meant to be vendored into another
    repo's CI without a package install. Both must contain the same logic.
    """

    def test_standalone_script_matches_package_module(self):
        """scripts/validate_terraform.py must be identical to src/pds/terra_wrangler/validator.py."""
        standalone = REPO_ROOT / "scripts" / "validate_terraform.py"
        packaged = REPO_ROOT / "src" / "pds" / "terra_wrangler" / "validator.py"

        self.assertTrue(standalone.exists(), f"missing {standalone}")
        self.assertTrue(packaged.exists(), f"missing {packaged}")
        self.assertTrue(
            filecmp.cmp(standalone, packaged, shallow=False),
            "scripts/validate_terraform.py and src/pds/terra_wrangler/validator.py have drifted apart — "
            "keep them byte-for-byte identical (copy one over the other) or update this test if a "
            "deliberate divergence is introduced.",
        )


if __name__ == "__main__":
    unittest.main()
