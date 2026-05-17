# Codex Handoff

Use this file when opening the repository from another computer or another Codex session. It is the shared working memory for the current planning branch.

## Current Branch

```text
kai-mind-roadmap-issues
```

## Current Goal

Prepare the repository for KAI-Mind roadmap work:

- Open parent Epic issues on GitHub.
- Document the cross-platform architecture decision.
- Save public reference repositories for input-layer research.
- Document GitHub Codex review setup.
- Update README so future contributors know where to start.

## GitHub Issues Created

- #1 `[Epic 0] Project Foundation: Cross-platform Core, CLI, and Local Web UI`
- #2 `[Epic 1] System Map Builder: Discover AI Stack Inputs and Data Flow`
- #3 `[Epic 2] Runtime Readiness: Ollama, Docker, Native Services, and Qdrant`
- #4 `[Epic 3] Privacy & Exposure Guard: Secrets, Ports, and Cloud Endpoints`
- #5 `[Epic 4] Agent Tool Risk Guard: Tool Inventory, Permissions, and Auditability`
- #6 `[Epic 5] RAG Knowledge Trust: Collections, Metadata, Citations, and Grounding`
- #7 `[Epic 6] Release Report & CI Gate: Verdict, Evidence, JSON, and Exit Code`
- #8 `[Epic 7] Distribution & Integrations: Packaging, GitHub Action, and Developer Workflow`

## Files Added or Updated

- `README.md`
- `AGENTS.md`
- `CODEX_HANDOFF.md`
- `docs/kai-mind/README.md`
- `docs/kai-mind/cross-platform-strategy.md`
- `docs/kai-mind/public-reference-repos.md`
- `docs/kai-mind/github-codex-review.md`

## Product Decision Snapshot

KAI-Mind should not be a Windows-only `.exe`.

The recommended architecture is:

```text
Core Engine + CLI + Local Backend + Local Web UI + thin platform launchers
```

The CLI is the stable contract. Launchers are convenience wrappers.

## Next Suggested Development Step

Start from Epic 1 only:

1. Create sub-issues under #2.
2. Define `ai_system_map.json` schema.
3. Add a small sample AI stack fixture.
4. Implement folder/config scanner.
5. Export the first system map.

Do not split all epics into detailed tasks yet.

## Important Constraints

- Scanners should be read-only by default.
- Do not print full secret values.
- Keep scanner logic in the core, not in the launcher.
- Local Web UI should call local backend/CLI, not scan sensitive files directly from browser-only code.
- Codex Cloud is not enabled yet, so this handoff file is the cross-device sync mechanism for now.

## How Another Codex Session Should Resume

1. Read `README.md`.
2. Read this file.
3. Read `docs/kai-mind/README.md`.
4. Check `git status --short --branch`.
5. If continuing implementation, start with Epic 1 schema work.
