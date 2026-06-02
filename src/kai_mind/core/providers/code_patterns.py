"""Conservative regex catalog for deterministic code pattern scanning."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class PatternRule:
    """One source pattern rule emitted as a provider-local scan fact."""

    rule_id: str
    languages: tuple[str, ...]
    extensions: tuple[str, ...]
    regex: re.Pattern[str]
    fact_kind: str


PYTHON_EXTENSIONS: Final = (".py",)
JAVASCRIPT_EXTENSIONS: Final = (".js", ".jsx", ".mjs", ".cjs")
TYPESCRIPT_EXTENSIONS: Final = (".ts", ".tsx")
SOURCE_EXTENSIONS: Final = (
    *PYTHON_EXTENSIONS,
    *JAVASCRIPT_EXTENSIONS,
    *TYPESCRIPT_EXTENSIONS,
)

CODE_PATTERN_RULES: Final[tuple[PatternRule, ...]] = (
    PatternRule(
        rule_id="code_pattern_embedding_openai",
        languages=("python",),
        extensions=PYTHON_EXTENSIONS,
        regex=re.compile(r"\bOpenAIEmbeddings\s*\("),
        fact_kind="embedding",
    ),
    PatternRule(
        rule_id="code_pattern_embedding_openai_sdk_create",
        languages=("python", "javascript", "typescript"),
        extensions=SOURCE_EXTENSIONS,
        regex=re.compile(
            r"\b(?:[A-Za-z_][A-Za-z0-9_]*\.)?embeddings\.create\s*\("
        ),
        fact_kind="embedding",
    ),
    PatternRule(
        rule_id="code_pattern_vector_store_qdrant",
        languages=("python",),
        extensions=PYTHON_EXTENSIONS,
        regex=re.compile(r"\bQdrantClient\s*\("),
        fact_kind="vector_store_client",
    ),
    PatternRule(
        rule_id="code_pattern_vector_store_chroma",
        languages=("python",),
        extensions=PYTHON_EXTENSIONS,
        regex=re.compile(r"\bChroma\s*\("),
        fact_kind="vector_store_client",
    ),
    PatternRule(
        rule_id="code_pattern_retriever_as_retriever",
        languages=("python",),
        extensions=PYTHON_EXTENSIONS,
        regex=re.compile(r"\.as_retriever\s*\("),
        fact_kind="retriever",
    ),
    PatternRule(
        rule_id="code_pattern_prompt_template",
        languages=("python",),
        extensions=PYTHON_EXTENSIONS,
        regex=re.compile(r"\bPromptTemplate\b"),
        fact_kind="prompt_template",
    ),
    PatternRule(
        rule_id="code_pattern_llm_chat_openai",
        languages=("python",),
        extensions=PYTHON_EXTENSIONS,
        regex=re.compile(r"\bChatOpenAI\b"),
        fact_kind="llm_call",
    ),
    PatternRule(
        rule_id="code_pattern_route_fastapi",
        languages=("python",),
        extensions=PYTHON_EXTENSIONS,
        regex=re.compile(
            r"@(?:[A-Za-z_][A-Za-z0-9_]*\.)"
            r"(?:get|post|put|delete|patch|options|head)"
            r"\s*\(\s*['\"][^'\"]+['\"]"
        ),
        fact_kind="route_endpoint",
    ),
    PatternRule(
        rule_id="code_pattern_route_flask",
        languages=("python",),
        extensions=PYTHON_EXTENSIONS,
        regex=re.compile(
            r"@(?:[A-Za-z_][A-Za-z0-9_]*\.)route"
            r"\s*\(\s*['\"][^'\"]+['\"]"
        ),
        fact_kind="route_endpoint",
    ),
    PatternRule(
        rule_id="code_pattern_route_express",
        languages=("javascript", "typescript"),
        extensions=(*JAVASCRIPT_EXTENSIONS, *TYPESCRIPT_EXTENSIONS),
        regex=re.compile(
            r"\b(?:app|router)\."
            r"(?:get|post|put|delete|patch|options|head)"
            r"\s*\(\s*['\"][^'\"]+['\"]"
        ),
        fact_kind="route_endpoint",
    ),
)
