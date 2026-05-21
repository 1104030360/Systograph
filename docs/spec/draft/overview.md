# KAI-Mind Spec Overview

KAI-Mind is a release-readiness tool for AI Agent and RAG systems. It does not build RAG apps. It inspects an existing project and produces evidence-backed artifacts that humans and CI can use.

Core workflow:

```text
Read -> Map -> Check -> Risk -> Recommend -> Gate
```

## Product Direction

KAI-Mind should keep scanner behavior in a shared core:

```text
Core Engine + CLI
        |
        +-- Local Web UI
        +-- Windows launcher
        +-- macOS launcher
        +-- CI / GitHub Actions
```

Launchers and UI should call the same core engine. They should not duplicate scanner logic.

## Epic Order

| Epic | Purpose |
|---|---|
| Epic 1 | Build `ai_system_map.json` from a project folder |
| Epic 2 | Runtime readiness checks |
| Epic 3 | Privacy and exposure guard |
| Epic 4 | Agent tool risk guard |
| Epic 5 | RAG knowledge trust |
| Epic 6 | Release report and CI gate |
| Epic 7 | Distribution and integrations |

## Current Focus

Start with Epic 1. The first implementation should stabilize:

- schema
- scanner boundaries
- normalization layer
- evidence model
- fixture tests
- CLI output contract

Do not start with a full dashboard or CI gate.
