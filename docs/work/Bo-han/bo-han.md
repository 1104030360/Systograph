# Bo-Han Work Scope - Epic 1 Viewer Layer

> Owner: Viewer, graph UX, detail panel, filters

## Goal

Bo-Han owns the presentation layer after `ai-system-map/v1` is stable. The viewer should help users inspect the map, but it must not become a second scanner.

## Responsibilities

- Implement `kai-mind viewer <map_json>` when the schema is stable.
- Load and validate `ai_system_map.json`.
- Build graph view model from map data.
- Render nodes, edges, endpoints, risk hints, and missing slots.
- Show node and edge detail panels.
- Show evidence and related risk hints.
- Implement highlight-only filters.
- Handle invalid map input with an error state.
- Add viewer and view-model tests.

## Non-Responsibilities

- Filesystem scanning.
- Config, Docker Compose, dependency, or code parsing.
- Deciding whether a component exists.
- Inventing components missing from the JSON.
- Runtime health checks.
- Query trace replay in Epic 1 MVP.

## Must Deliver

| Deliverable | Notes |
|---|---|
| Viewer load flow | Valid map shows graph; invalid map shows error |
| Graph view model | Built only from `ai_system_map.json` |
| Detail panel | Shows slot, status, evidence, risk hints |
| Filters | Keep full graph visible; highlight matches |
| Tests | Valid map, invalid map, detail panel, filters, no full secret |

## Contract With Timmy

Bo-Han depends on:

- stable `ai-system-map/v1`
- sample maps
- evidence refs
- risk hint refs
- flow and edge fields
- human-readable labels

If a field is missing, ask Timmy to add it to the schema. Do not patch missing schema fields in the viewer.

## Review Checklist

- Viewer does not read project files.
- Viewer does not infer components absent from JSON.
- Viewer does not show unmasked secrets.
- Filters do not hide unmatched graph items by default.
- Invalid maps do not render partial graphs.
