from __future__ import annotations

from pathlib import Path

from systograph.core.services.path_safety_service import (
    normalize_project_relative_path,
)

SECRET_LIKE_FILENAMES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".env.test",
}
SECRET_LIKE_SUFFIXES = {
    ".key",
    ".pem",
    ".p12",
    ".pfx",
    ".keystore",
    ".jks",
}
SECRET_LIKE_MARKERS = (
    "secret",
    "token",
    "credential",
    "apikey",
    "api_key",
    "password",
)
# The name-marker heuristic asks "is this a secret-bearing artifact?".
# A program source file answers no by construction: "token" is core AI
# vocabulary (TokenChunker.py, tokenizers/, tokenizer_config.py) and a
# module named credentials_loader.go implements handling rather than
# storing a secret. Source CONTENT is still protected -- values are
# masked by SecretMaskingService and never leave the boundary raw.
# Shell scripts stay under the heuristic: they routinely inline
# `export API_KEY=...`.
PROGRAM_SOURCE_SUFFIXES = {
    ".c",
    ".cc",
    ".cjs",
    ".cpp",
    ".cs",
    ".go",
    ".h",
    ".hpp",
    ".ipynb",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".kts",
    ".m",
    ".mjs",
    ".mm",
    ".php",
    ".py",
    ".pyi",
    ".rb",
    ".rs",
    ".scala",
    ".svelte",
    ".swift",
    ".ts",
    ".tsx",
    ".vue",
}
VECTOR_PERSISTENCE_MARKERS = {
    "chroma",
    "faiss",
    "milvus",
    "qdrant",
    "weaviate",
    "vector",
    "vectors",
    "vector_store",
    "vectorstore",
}
VECTOR_PERSISTENCE_SUFFIXES = {
    ".ann",
    ".db",
    ".duckdb",
    ".faiss",
    ".hnsw",
    ".index",
    ".npy",
    ".npz",
    ".sqlite",
    ".sqlite3",
}
SOURCE_OR_DOC_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".go",
    ".h",
    ".hpp",
    ".java",
    ".js",
    ".jsx",
    ".json",
    ".kt",
    ".md",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".scala",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}


class InventoryRiskService:
    def risk_type(self, path: str) -> str | None:
        safe = normalize_project_relative_path(path)
        if self._is_secret_like(safe):
            return "secret_like_config"
        if self._is_vector_persistence(safe):
            return "model_or_vector_persistence"
        return None

    def _is_secret_like(self, path: str) -> bool:
        path_obj = Path(path)
        name = path_obj.name.lower()
        if name in SECRET_LIKE_FILENAMES:
            return True
        if any(name.endswith(suffix) for suffix in SECRET_LIKE_SUFFIXES):
            return True
        if path_obj.suffix.lower() in PROGRAM_SOURCE_SUFFIXES:
            return False
        normalized = path.lower().replace("-", "_")
        return any(marker in normalized for marker in SECRET_LIKE_MARKERS)

    def _is_vector_persistence(self, path: str) -> bool:
        path_obj = Path(path)
        suffix = path_obj.suffix.lower()
        if suffix in SOURCE_OR_DOC_SUFFIXES:
            return False
        path_parts = {
            part.lower().replace("-", "_").lstrip(".")
            for part in path_obj.parts
        }
        stem = path_obj.stem.lower().replace("-", "_")
        has_marker = bool(
            VECTOR_PERSISTENCE_MARKERS.intersection(path_parts)
        ) or any(marker in stem for marker in VECTOR_PERSISTENCE_MARKERS)
        return has_marker and (
            suffix in VECTOR_PERSISTENCE_SUFFIXES or suffix == ""
        )
