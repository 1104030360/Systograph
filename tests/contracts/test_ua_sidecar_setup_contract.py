from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
UA_ROOT = REPO_ROOT / "ref-opensource" / "Understand-Anything"
PATCH_PATH = (
    REPO_ROOT / "sidecar" / "patches" / "compute-batches-workdir.patch"
)
SETUP_SCRIPT = REPO_ROOT / "scripts" / "setup_ua_sidecar.sh"
EXPECTED_UA_PIN = "73559a160645359c57be44c174935899dec9f9f2"


def test_compute_batches_patch_applies_to_pinned_submodule() -> None:
    # Given: the canonical UA pin is in either supported setup state.
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=UA_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert head == EXPECTED_UA_PIN

    # When: forward and reverse checks probe the current idempotent state.
    forward = subprocess.run(
        ["git", "apply", "--unidiff-zero", "--check", str(PATCH_PATH)],
        cwd=UA_ROOT,
        capture_output=True,
        text=True,
    )
    reverse = subprocess.run(
        [
            "git",
            "apply",
            "--unidiff-zero",
            "--reverse",
            "--check",
            str(PATCH_PATH),
        ],
        cwd=UA_ROOT,
        capture_output=True,
        text=True,
    )

    # Then: setup recognizes exactly one valid direction without gitlink drift.
    assert (forward.returncode == 0) != (reverse.returncode == 0), (
        forward.stderr + reverse.stderr
    )


def test_setup_script_is_pin_checked_and_idempotent() -> None:
    # Given/When: setup is inspected as an installation boundary.
    source = SETUP_SCRIPT.read_text(encoding="utf-8")

    # Then: it rejects drift and recognizes both unapplied and applied states.
    assert EXPECTED_UA_PIN in source
    assert "apply --unidiff-zero --check" in source
    assert "apply --unidiff-zero --reverse --check" in source
    assert source.count("apply --unidiff-zero") == 3
    assert "pnpm approve-builds" not in source


def test_setup_script_has_valid_bash_syntax() -> None:
    result = subprocess.run(
        ["bash", "-n", str(SETUP_SCRIPT)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
