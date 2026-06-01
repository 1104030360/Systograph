"""Mask secret-like values before they enter reports or logs."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

SECRET_KEY_MARKERS: Final = (
    "API_KEY",
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "BEARER",
    "AUTH",
)
MASK: Final = "[MASKED]"
SHORT_SECRET_MAX_LENGTH: Final = 8
VISIBLE_EDGE_LENGTH: Final = 4

KEY_VALUE_RE: Final = re.compile(
    r"(?P<key_quote>['\"]?)"
    r"(?P<key>\b(?=[A-Za-z_][A-Za-z0-9_]*)"
    r"(?=[A-Za-z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD|BEARER|AUTH))"
    r"[A-Za-z_][A-Za-z0-9_]*)"
    r"(?P=key_quote)"
    r"(?P<separator>\s*[:=]\s*)"
    r"(?:(?P<quote>['\"])(?P<quoted_value>.*?)(?P=quote)|"
    r"(?P<value>[^'\"\s]+))",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SecretPattern:
    id: str
    regex: re.Pattern[str]
    group: str = "value"


SECRET_PATTERNS: Final = (
    SecretPattern(
        id="authorization-bearer",
        regex=re.compile(
            r"\bAuthorization\s*:\s*Bearer\s+(?P<value>\S+)",
            re.IGNORECASE,
        ),
    ),
    SecretPattern(
        id="openai-key",
        regex=re.compile(r"\b(?P<value>sk-[A-Za-z0-9_-]{8,})\b"),
    ),
    SecretPattern(
        id="github-token",
        regex=re.compile(r"\b(?P<value>gh[pousr]_[A-Za-z0-9_]{8,})\b"),
    ),
    SecretPattern(
        id="gitlab-token",
        regex=re.compile(r"\b(?P<value>glpat-[A-Za-z0-9_-]{8,})\b"),
    ),
    SecretPattern(
        id="slack-token",
        regex=re.compile(r"\b(?P<value>xox[baprs]-[A-Za-z0-9-]{8,})\b"),
    ),
    SecretPattern(
        id="slack-webhook",
        regex=re.compile(
            r"(?P<value>https://hooks\.slack\.com/services/"
            r"[A-Za-z0-9_/+-]{20,})"
        ),
    ),
    SecretPattern(
        id="aws-access-key-id",
        regex=re.compile(r"\b(?P<value>AKIA[0-9A-Z]{16})\b"),
    ),
    SecretPattern(
        id="private-key-block",
        regex=re.compile(
            r"-----BEGIN (?P<kind>[A-Z ]*PRIVATE KEY)-----\s*"
            r"(?P<value>.*?)"
            r"\s*-----END (?P=kind)-----",
            re.DOTALL,
        ),
    ),
)

JsonLike = Mapping[str, Any] | Sequence[Any] | str | int | float | bool | None


class SecretMaskingService:
    """Apply one masking policy to strings and JSON-like values."""

    def mask_value(self, value: str, key: str | None = None) -> str:
        if not self._should_mask_value(value, key):
            return value

        return self._mask_secret_value(value)

    def _mask_secret_value(self, value: str) -> str:
        if len(value) <= SHORT_SECRET_MAX_LENGTH:
            return MASK

        return (
            f"{value[:VISIBLE_EDGE_LENGTH]}...{value[-VISIBLE_EDGE_LENGTH:]}"
        )

    def mask_text(self, text: str) -> str:
        masked = KEY_VALUE_RE.sub(self._mask_key_value_match, text)
        for pattern in SECRET_PATTERNS:
            masked = self._mask_text_pattern(masked, pattern)
        return masked

    def mask_json_like(self, value: JsonLike) -> JsonLike:
        if isinstance(value, str):
            return self.mask_text(value)

        if isinstance(value, Mapping):
            sibling_key = value.get("key")
            return {
                key: self._mask_json_dict_value(
                    key, child, sibling_key=sibling_key
                )
                for key, child in value.items()
            }

        if isinstance(value, Sequence) and not isinstance(
            value, bytes | bytearray
        ):
            return [self.mask_json_like(child) for child in value]

        return value

    def _mask_json_dict_value(
        self,
        key: str,
        value: Any,
        *,
        sibling_key: Any = None,
    ) -> JsonLike:
        if isinstance(value, str) and self._is_secret_key(key):
            return self.mask_value(value, key=key)
        if (
            key == "value"
            and isinstance(value, str)
            and isinstance(sibling_key, str)
            and self._is_secret_key(sibling_key)
        ):
            return self.mask_value(value, key=sibling_key)
        return self.mask_json_like(value)

    def _mask_key_value_match(self, match: re.Match[str]) -> str:
        key = match.group("key")
        value = match.group("quoted_value") or match.group("value")
        key_quote = match.group("key_quote") or ""
        quote = match.group("quote") or ""
        if key.upper().startswith("AUTHORIZATION") and not quote:
            return match.group(0)

        return (
            f"{key_quote}{key}{key_quote}{match.group('separator')}{quote}"
            f"{self.mask_value(value, key=key)}{quote}"
        )

    def _should_mask_value(self, value: str, key: str | None) -> bool:
        return self._is_secret_key(key) or self._is_token_like(value)

    def _is_secret_key(self, key: str | None) -> bool:
        if key is None:
            return False

        normalized = key.upper()
        return any(marker in normalized for marker in SECRET_KEY_MARKERS)

    def _is_token_like(self, value: str) -> bool:
        return any(
            pattern.regex.fullmatch(value)
            for pattern in SECRET_PATTERNS
            if pattern.id != "private-key-block"
        )

    def _mask_pattern_match(
        self, match: re.Match[str], pattern: SecretPattern
    ) -> str:
        start, end = match.span(pattern.group)
        relative_start = start - match.start()
        relative_end = end - match.start()
        matched_text = match.group(0)
        secret_value = match.group(pattern.group)

        return (
            f"{matched_text[:relative_start]}"
            f"{self._mask_secret_value(secret_value)}"
            f"{matched_text[relative_end:]}"
        )

    def _mask_text_pattern(self, text: str, pattern: SecretPattern) -> str:
        def replace(match: re.Match[str]) -> str:
            return self._mask_pattern_match(match, pattern)

        return pattern.regex.sub(replace, text)
