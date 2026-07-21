from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
UNBRACED_VARIABLE_BEFORE_NON_ASCII = re.compile(
    r"\$[A-Za-z_][A-Za-z0-9_]*(?=[^\x00-\x7f])"
)


def test_shell_variables_before_non_ascii_text_are_braced() -> None:
    offenders: list[str] = []

    for script in sorted((REPO_ROOT / "scripts").rglob("*.sh")):
        for line_number, line in enumerate(
            script.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            matches = UNBRACED_VARIABLE_BEFORE_NON_ASCII.findall(line)
            offenders.extend(
                f"{script.relative_to(REPO_ROOT)}:{line_number}:{match}"
                for match in matches
            )

    assert offenders == [], (
        "Brace shell variables before non-ASCII text for macOS Bash 3.2: "
        + ", ".join(offenders)
    )
