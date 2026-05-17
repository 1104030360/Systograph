# KAI-Mind Roadmap

This folder contains the current roadmap and workflow notes for turning Local AI Health Doctor into KAI-Mind: an AI Agent / RAG Release Readiness Gate.

## Parent Epic Issues

| Issue | Epic | Purpose |
| --- | --- | --- |
| [#1](https://github.com/1104030360/Local-AI-Health-Doctor/issues/1) | Project Foundation | Decide cross-platform core, CLI, Local Web UI, repo workflow, and report contracts. |
| [#2](https://github.com/1104030360/Local-AI-Health-Doctor/issues/2) | System Map Builder | Scan project inputs and produce `ai_system_map.json`. |
| [#3](https://github.com/1104030360/Local-AI-Health-Doctor/issues/3) | Runtime Readiness | Check Ollama, Docker, native services, Qdrant, and app/API health. |
| [#4](https://github.com/1104030360/Local-AI-Health-Doctor/issues/4) | Privacy & Exposure Guard | Check secrets, ports, cloud endpoints, and Data Leaves Device risk. |
| [#5](https://github.com/1104030360/Local-AI-Health-Doctor/issues/5) | Agent Tool Risk Guard | Inventory agent tools, permissions, approval, policy, and audit logs. |
| [#6](https://github.com/1104030360/Local-AI-Health-Doctor/issues/6) | RAG Knowledge Trust | Check collections, metadata, citations, and answer grounding. |
| [#7](https://github.com/1104030360/Local-AI-Health-Doctor/issues/7) | Release Report & CI Gate | Generate verdict, evidence, JSON report, exit code, and CI gate behavior. |
| [#8](https://github.com/1104030360/Local-AI-Health-Doctor/issues/8) | Distribution & Integrations | Plan launchers, GitHub Action, Codex review, and future integrations. |

## Recommended Development Order

1. Keep all parent epics open as roadmap anchors.
2. Split only Epic 1 into sub-issues first.
3. Build System Map Builder until it can scan a sample AI stack.
4. Use the first `ai_system_map.json` as the shared input contract for later modules.
5. Move to Runtime Readiness after Epic 1 is usable end to end.

## Epic 1 Suggested Sub-Issues

- Define AI System Map schema.
- Create sample AI system project.
- Implement project folder scanner.
- Implement config / `.env` scanner.
- Implement `docker-compose.yml` scanner.
- Export `ai_system_map.json`.

## Branch Naming

Use branch names that map clearly to the issue:

```text
feature/system-map-schema
feature/system-map-sample-project
feature/project-folder-scanner
feature/config-env-scanner
feature/docker-compose-scanner
feature/system-map-json-export
```

## Definition of Done for a Parent Epic

An epic is done only when:

- The feature produces evidence, not just a pass/fail label.
- The result can be represented in JSON.
- The report can explain what the user should fix first.
- Risky checks are read-only by default.
- The README or relevant docs are updated.
