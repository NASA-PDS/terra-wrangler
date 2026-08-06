# encoding: utf-8
"""CLI entry point for the ``tf-sheriff`` console script.

This module exists only to give the package a stable entry point per
NASA-PDS's Python packaging convention (``setup.cfg``'s
``console_scripts``). The actual validation logic lives in
:mod:`pds.tf_sheriff.validator`, which is also kept, byte-for-byte, as
the standalone ``scripts/validate_terraform.py`` in the repository root
so it can be vendored into another repo's CI without a package
dependency. See ``tests/pds/tf_sheriff/test_validate_terraform.py``'s
``test_standalone_script_matches_package_module`` for the check that
keeps the two copies from drifting apart.
"""
import sys

from pds.tf_sheriff.validator import main as _validator_main


def main() -> None:
    """Entry point installed as the ``tf-sheriff`` console script."""
    sys.exit(_validator_main())


if __name__ == "__main__":
    main()
