from __future__ import annotations


def count_source_lines(content: bytes) -> int:
    if not content:
        return 0
    return content.count(b"\n") + int(not content.endswith(b"\n"))
