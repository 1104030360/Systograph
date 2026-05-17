# KAI-Mind / Local AI Health Doctor

KAI-Mind is an AI Agent / RAG Release Readiness Gate. It helps a team inspect whether a local AI system is safe, reliable, trustworthy, and ready for demo, handoff, deployment, or CI/CD.

The project is not an AI chatbot, RAG builder, or full observability platform. Its job is to scan an existing AI Agent / RAG system, build an AI System Map, run readiness checks, and produce a report with a clear verdict:

- `READY`
- `RISKY`
- `NOT READY`

## Product Direction

KAI-Mind should be built as a cross-platform core first:

```text
Core Engine + CLI
        |
        +-- Local Web UI
        +-- Windows launcher
        +-- macOS launcher
        +-- CI / GitHub Actions
```

This avoids a Windows-only `.exe` architecture and keeps the core scanner usable on Windows, macOS, Linux, local development, and CI.

## MVP Modules

The current roadmap is organized as parent Epic issues:

- [Epic 0: Project Foundation](https://github.com/1104030360/Local-AI-Health-Doctor/issues/1)
- [Epic 1: System Map Builder](https://github.com/1104030360/Local-AI-Health-Doctor/issues/2)
- [Epic 2: Runtime Readiness](https://github.com/1104030360/Local-AI-Health-Doctor/issues/3)
- [Epic 3: Privacy & Exposure Guard](https://github.com/1104030360/Local-AI-Health-Doctor/issues/4)
- [Epic 4: Agent Tool Risk Guard](https://github.com/1104030360/Local-AI-Health-Doctor/issues/5)
- [Epic 5: RAG Knowledge Trust](https://github.com/1104030360/Local-AI-Health-Doctor/issues/6)
- [Epic 6: Release Report & CI Gate](https://github.com/1104030360/Local-AI-Health-Doctor/issues/7)
- [Epic 7: Distribution & Integrations](https://github.com/1104030360/Local-AI-Health-Doctor/issues/8)

Start development from Epic 1. Keep other epics as roadmap-level parent issues until System Map Builder can produce the first usable `ai_system_map.json`.

## Key Documents

- [KAI-Mind roadmap](docs/kai-mind/README.md)
- [Cross-platform architecture strategy](docs/kai-mind/cross-platform-strategy.md)
- [Public reference repositories](docs/kai-mind/public-reference-repos.md)
- [GitHub Codex code review setup](docs/kai-mind/github-codex-review.md)
- [Codex handoff file](CODEX_HANDOFF.md)

## Suggested First Development Flow

1. Pick Epic 1: System Map Builder.
2. Split only Epic 1 into sub-issues.
3. Create one branch per sub-issue.
4. Open PRs into `main`.
5. Require human review plus Codex review before merge.
6. After Epic 1 is usable, start decomposing Epic 2.

## Working Principles

- Read-only scanners by default.
- Local-first privacy posture.
- Do not print full secret values.
- Output evidence, not just scores.
- Keep packaging separate from the core scanner.
- Make CLI and JSON report stable before polishing the launcher.
