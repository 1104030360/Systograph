# 2026-07-10 AI System Map V2 Compatibility Gate Report

Status: expand-phase gate for Plan 00A  
Audience: Plan 13 cutover owners, reviewers  
Last updated: 2026-07-10

## Purpose

Record the 00A compatibility gate outcome before any active output cutover to
`ai-system-map/v2`. Plan 13 must depend on this report.

## Gate Summary

| Check | Result |
|------|--------|
| v1 remains readable / test-covered | PASS |
| Dual-read loader owns schema branching | PASS (`CanonicalMapLoader`) |
| v1→v2 adapter deterministic / read-only / no evidence loss | PASS |
| v2 represents grounded RAG / LLM app / tool agent / workflow | PASS |
| Assessment five-state + activation six-state + evidence kinds | PASS (models + validation) |
| Fixed 10-plane / 52-node reference catalog + overlay | PASS |
| Active output still v1 (no silent cutover) | PASS |
| Windows absolute / backslash paths rejected | PASS |

## Consumer Compatibility Matrix

| Consumer | Status | Notes |
|----------|--------|-------|
| CLI `kai-mind map` | equivalent (v1 active) | Emits `active_schema_version` + migration warnings; v2 opt-in does not rewrite artifact |
| Web `/api/scans` | equivalent (v1 active) | Accepts optional `system_map_schema_version`; build artifact remains v1 |
| ViewerSessionService / GraphViewModel | deferred migration | Still consumes `RagSystemMap`; must switch via loader in Plan 13 |
| Markdown summary | deferred migration | Still renders v1 map |
| Mapping proposal / manual mapping | deferred migration | Still keyed to v1 unmapped / slots |
| Profile inference / readiness renderer | not migrated | Planned after 00A; must read normalized `AiSystemMapV2` only |
| Frontend sample / API clients expecting v1 | equivalent | Existing v1 payload shape unchanged |

Legend:

- **equivalent**: same external contract as before 00A
- **deferred migration**: still on v1; must not invent local schema branching
- **not migrated**: not yet implemented against normalized v2

## Equivalence Notes

- Same v1 fixture through `SystemMapV1ToV2Adapter.adapt_to_canonical()` preserves
  evidence ids and project-relative locations.
- Native v2 fixtures validate without RAG slot forcing.
- `MapBuildResult.active_schema_version` remains `ai-system-map/v1` during 00A
  even when `requested_schema_version=ai-system-map/v2`.

## Plan 13 Dependencies

Plan 13 may switch active output only after:

1. This gate remains green.
2. Viewer / mapping / profile / readiness consumers read via `CanonicalMapLoader`.
3. Compatibility report consumers above are marked equivalent or explicitly retired.

## Residual Risks

- Frontend design samples still use some `*_layer` naming; runtime contract uses
  MODEL-CONTRACT plane ids.
- Workflow provider is opt-in scan signal only; not yet wired into default
  `ProjectScanService` aggregation (avoid silent behavior change in 00A).
- Profile / readiness sidecars are out of 00A scope.
