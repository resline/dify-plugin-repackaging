"""Regression tests for untrusted plugin requirement validation."""

from pathlib import Path

import pytest

from scripts.validate_requirements import (
    RequirementsValidationError,
    validate_requirements,
)


def test_accepts_canonical_pinned_index_requirements():
    requirements = validate_requirements(
        [
            "# plugin dependencies\n",
            "Requests == 2.31.0\n",
            "uvicorn[Standard]==0.34.0  # runtime server\n",
        ]
    )

    assert requirements == [
        "requests==2.31.0",
        "uvicorn[standard]==0.34.0",
    ]


@pytest.mark.parametrize(
    "unsafe_requirement",
    [
        "-r additional.txt",
        "--index-url https://example.invalid/simple",
        "--no-binary :all:",
        "-e ./local-project",
        "./local-project",
        "demo @ https://example.invalid/demo.whl",
        "demo @ https://example.invalid/demo.tar.gz",
        "demo @ git+https://example.invalid/demo.git",
        "demo>=1.0",
        "demo==1.*",
        'demo==1.0; python_version >= "3.12"',
    ],
)
def test_rejects_non_pinned_or_external_requirement_forms(unsafe_requirement):
    with pytest.raises(RequirementsValidationError):
        validate_requirements([unsafe_requirement])


def test_repackager_uses_validated_wheel_only_requirements():
    backend_dir = Path(__file__).resolve().parents[3]
    script = (backend_dir / "scripts" / "plugin_repackaging.sh").read_text()

    assert 'python3 -I "${CURR_DIR}/validate_requirements.py" requirements.txt' in script
    assert (
        'pip download "${PIP_PLATFORM[@]}" --only-binary=:all: '
        '-r "${VALIDATED_REQUIREMENTS}"'
    ) in script
