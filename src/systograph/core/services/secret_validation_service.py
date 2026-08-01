"""Independent fail-closed checks for credential-bearing output strings."""

from __future__ import annotations

import re
from typing import Final
from urllib.parse import urlsplit

MASKED_CREDENTIALS: Final = frozenset({"[MASKED]", "****"})
URL_WITH_AUTHORITY_RE: Final = re.compile(
    r"[A-Za-z][A-Za-z0-9+.-]*://[^\s'\"<>]+"
)


class SecretValidationService:
    """Detect raw URL credentials without relying on the masking service."""

    def contains_unmasked_url_credentials(self, value: str) -> bool:
        return any(
            self._has_unmasked_userinfo(match.group(0))
            for match in URL_WITH_AUTHORITY_RE.finditer(value)
        )

    def _has_unmasked_userinfo(self, raw_url: str) -> bool:
        try:
            netloc = urlsplit(raw_url).netloc
        except ValueError:
            netloc = self._fallback_netloc(raw_url)

        if "@" not in netloc:
            return False

        userinfo, host = netloc.rsplit("@", 1)
        if not userinfo or not host:
            return False

        if ":" in userinfo:
            _, _, password = userinfo.partition(":")
            return password not in MASKED_CREDENTIALS

        return userinfo not in MASKED_CREDENTIALS

    def _fallback_netloc(self, raw_url: str) -> str:
        _, separator, remainder = raw_url.partition("://")
        if not separator:
            return ""
        return re.split(r"[/ ?#]", remainder, maxsplit=1)[0]
