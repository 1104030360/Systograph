"""Environment isolation for git subprocesses run against a scan target."""

from __future__ import annotations

import os
from collections.abc import Mapping

GIT_ENVIRONMENT_PREFIX = "GIT_"


def scoped_git_environment(
    base: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return ``base`` without the variables that repoint git at another repo.

    Git exports ``GIT_DIR``, ``GIT_INDEX_FILE`` and friends to every hook it
    runs, and CI steps export them too. A git subprocess that inherits them
    resolves against the exporting repository and ignores its own ``cwd``, so a
    scan launched from such an environment would enumerate the wrong project,
    and any write plumbing would land in the wrong index. Dropping the whole
    ``GIT_`` namespace fails closed: the scanner only runs local read-only
    plumbing (``rev-parse``, ``ls-files``, ``check-ignore``), which needs no
    inherited git configuration, and denying by prefix keeps new git variables
    from reopening the hole.
    """

    source = os.environ if base is None else base
    return {
        key: value
        for key, value in source.items()
        if not key.startswith(GIT_ENVIRONMENT_PREFIX)
    }
