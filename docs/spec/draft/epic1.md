# Epic 1 Spec: RAG System Map Builder

> Status: Spec overview
> Detailed implementation contract: `docs/design/epic1.md`

## Goal

Epic 1 makes KAI-Mind able to scan an existing RAG project folder and produce a stable, evidence-based `ai_system_map.json`.

The output should let later epics answer:

- What components exist?
- Which files or settings prove they exist?
- Which endpoints were detected?
- Which risks need later checks?
- Which RAG slots are missing or not configured?

Epic 1 does not decide release readiness.

## User Story

As a developer preparing a local RAG project for review, I can run:

```bash
kai-mind map ./my-rag-project
```

and receive:

```text
outputs/
  ai_system_map.json
  ai_system_map.md
```

The JSON is for tools and later checks. The Markdown is for humans.

## In Scope

- Project folder discovery.
- `.env`, config, Docker Compose, dependency manifest, and bounded source scan.
- RAG-oriented component slots.
- Endpoint detection.
- Evidence-backed risk hints.
- Secret-safe output.
- Synthetic fixtures and contract tests.

## Out of Scope

- Runtime health checks.
- Full security scanning.
- Agent tool policy.
- RAG answer groundedness.
- CI gate verdicts.
- Query trace / replay by default.
- Full interactive dashboard.

## RAG Slots

Initial `rag-core-v1` slots:

- data source
- document loader
- chunking
- embedding model
- vector store
- app API or orchestrator
- query processing
- retriever
- prompt builder
- LLM
- citation or response composer
- guardrails
- observability

Each slot can be:

- `detected`
- `missing`
- `not_configured`
- `not_applicable`

Detected slots require evidence.

## Required Map Concepts

`ai-system-map/v1` should include:

- project metadata
- selected reference architecture
- components by slot
- component instances
- endpoints
- flows and edges
- evidence
- risk hints
- recommended next checks

The map must not use `confidence`. If evidence is weak or missing, the status should say so directly.

## Privacy Rules

- Scanner is read-only.
- Secret-like values are masked before output.
- Full secret values must not appear in JSON, Markdown, logs, snapshots, or UI.
- Raw retrieved chunks are not part of the default map contract.
- External endpoints are hints for later checks, not proof of data exposure.

## Fixture Strategy

Use synthetic fixtures, not vendored public repositories.

Initial fixtures:

- basic Qdrant + Ollama RAG stack
- external OpenAI provider signal
- malformed config for partial map behavior
- minimal project with missing RAG slots

Public repos can inform fixture patterns, but tests must run only on local fixtures.

## Acceptance Criteria

- `kai-mind map <project_path>` creates valid `ai_system_map.json`.
- JSON validates against `ai-system-map/v1`.
- Markdown summary is generated from the same map.
- Malformed config produces a partial map with parse-error evidence.
- Missing project produces `map-error.md` and exits non-zero.
- Detected components include evidence.
- Output uses project-relative POSIX paths.
- No full secret is present in outputs.
- Tests cover schema, fixtures, masking, path normalization, and partial failure.

## Follow-up Work

- Viewer prototype after schema is stable.
- Query trace as explicit opt-in after privacy and side-effect boundaries are defined.
- Runtime readiness checks in Epic 2.
- Privacy and exposure guard in Epic 3.
