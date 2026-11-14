"""Validate untrusted plugin requirements before passing them to pip."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version


class RequirementsValidationError(ValueError):
    """Raised when a requirements file contains an unsafe requirement form."""


def _without_inline_comment(line: str) -> str:
    """Remove pip-style inline comments while preserving URL fragments for rejection."""
    comment = re.search(r"\s+#", line)
    if comment:
        return line[: comment.start()].strip()
    return line.strip()


def validate_requirements(lines: Iterable[str]) -> list[str]:
    """Return canonical pinned requirements or reject the complete input."""
    validated: list[str] = []

    for line_number, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        requirement_text = _without_inline_comment(raw_line)
        try:
            requirement = Requirement(requirement_text)
        except InvalidRequirement as exc:
            raise RequirementsValidationError(
                f"line {line_number} is not a package requirement"
            ) from exc

        if requirement.url is not None:
            raise RequirementsValidationError(
                f"line {line_number} uses a direct URL"
            )
        if requirement.marker is not None:
            raise RequirementsValidationError(
                f"line {line_number} uses an environment marker"
            )

        specifiers = list(requirement.specifier)
        if (
            len(specifiers) != 1
            or specifiers[0].operator != "=="
            or specifiers[0].version.endswith(".*")
        ):
            raise RequirementsValidationError(
                f"line {line_number} must pin exactly one version with =="
            )

        try:
            version = Version(specifiers[0].version)
        except InvalidVersion as exc:
            raise RequirementsValidationError(
                f"line {line_number} has an invalid pinned version"
            ) from exc

        name = canonicalize_name(requirement.name)
        if requirement.extras:
            extras = ",".join(
                sorted(canonicalize_name(extra) for extra in requirement.extras)
            )
            name = f"{name}[{extras}]"
        validated.append(f"{name}=={version}")

    return validated


def validate_requirements_file(path: Path) -> list[str]:
    """Read and validate a UTF-8 requirements file."""
    try:
        with path.open("r", encoding="utf-8") as requirements_file:
            return validate_requirements(requirements_file)
    except (OSError, UnicodeError) as exc:
        raise RequirementsValidationError(
            "requirements.txt must be a readable UTF-8 file"
        ) from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("requirements", type=Path)
    args = parser.parse_args()

    try:
        validated = validate_requirements_file(args.requirements)
    except RequirementsValidationError as exc:
        parser.exit(1, f"Unsafe requirements.txt: {exc}\n")

    for requirement in validated:
        print(requirement)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
