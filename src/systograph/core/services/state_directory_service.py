from __future__ import annotations

import os
from pathlib import Path


def default_state_dir() -> Path:
    configured = os.environ.get("SYSTOGRAPH_STATE_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".systograph"
