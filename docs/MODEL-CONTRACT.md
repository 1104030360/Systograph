# KAI-Mind Phase 2 Model Contract

Status: planned Phase 2 static-readiness contract draft. Runtime/query trace is
deferred; generic `ai-system-map/v2` now follows 00A compatibility migration,
Plan 13 cutover, and Plan 14 final validation.

Audience: frontend / viewer implementers.

Last updated: 2026-07-07.

## 2026-07-06 Superseding Contract

This section supersedes later v1-only, three-state, detected-only projection, and
fixed-row RAG catalog wording.

- Input is an AI system repo or workflow artifact; it is not assumed to be RAG.
- Active target is generic `ai-system-map/v2`; v1 remains legacy-readable through
  the 00A adapter.
- `rag-core-v1` is a legacy v1 compatibility template and migration input only.
  It does not define product readiness, frontend summaries, or a RAG classifier.
- Profiles are registry-driven generic capability overlays, not RAG variants.
- Active assessment status is five-state: `detected / partial / undetermined /
  not_detected / conflicted`.
- Activation is separate from assessment status: `enabled / disabled /
  conditional / unknown / conflicted / not_applicable`.
- Evidence kind is explicit: `direct / indirect / explicit_negative`.
- `detected` requires direct evidence. Indirect-only evidence is always `partial`,
  even when multiple independent indirect signals converge.
- Explicit-negative evidence requires an explicit disabled, bypassed, forbidden,
  deny/skip, or incompatible declaration. Absence or no match is not negative evidence.
- `not_detected` requires a capability-specific coverage gate. Absence of
  sufficient direct/indirect evidence before that gate passes is `undetermined`,
  not `not_detected`.
- Conflicts are field-specific and retain evidence from both sides; a conflict in
  one field must not erase unrelated supported fields.
- Assessment scope is explicit and stable across sibling artifacts:
  `scan_id`, `build_id`, and `environment_id`. `scan_id` identifies the
  immutable read-only scan snapshot; `build_id` identifies one materialization
  from that snapshot. Phase2 does not expose a separate active `snapshot_id`.
- The viewer uses a fixed ten-plane / 52-node reference map plus a repo overlay.
  Reference capability nodes and repo component nodes are distinct semantic kinds.
- Mapping Completeness is a derived coverage metric, not confidence. Its weights
  are detected 1, not_detected 1, partial 0.5, undetermined/conflicted 0. The
  denominator is every fixed reference node; activation/not_applicable never
  removes a node from the denominator.
- Numeric `confidence` is forbidden.
- `primary_map_type` is a derived readiness-report summary, not canonical truth.
- Required static-readiness output set: `ai_system_map.json`,
  `profile_signals.json`, `readiness_report.json`, `ai_system_map.md`,
  `system_map.mmd`.
- Required P0 static execution output set, owned by dynamic `00` but not runtime
  tracing: `call_graph.json`, `dataflow_hints.json`, `execution_paths.json`,
  `evidence_table.json`, `execution_map.mmd`.
- JSON artifacts are separate sibling files with separate schemas. They are not
  nested into one aggregate JSON file. This keeps the Phase2 file contract ready
  for post-Phase2 database tables.
- Profile registry MVP ids are: `rag-grounding`, `agentic-control`, `tool-calling`,
  `memory`, `workflow-orchestration`, `hybrid-retrieval`, `reranking`,
  `corrective-retrieval`, `self-reflection`, `graph-retrieval`,
  `hierarchical-retrieval`, `contextual-retrieval`, `multimodal-grounding`,
  `modular-composition`, `multi-query-retrieval`.
- Frontend must not hard-code profile count/order or infer topology.

DeepResearch artifacts, including its web Validation Simulator, are reference
material only. They do not define product runtime behavior or add a simulator to
the KAI-Mind Phase 2 contract.

## 2026-07-07 Superseding Contract — UA Staged Rollout

This section supersedes wording that treats UA as already active in current
runtime, treats semantic candidates as Phase2 contract data, or implies that
Apply recomputes the scan. The migration is staged:

- **Phase A — TOML primary (current runtime):** existing KAI scan providers
  produce Step 3 facts/evidence. Phase2 deterministic
  `ProfileInferenceService` and Apply must work when the UA sidecar is absent.
- **Phase B — UA primary + TOML parity (target after Gate-1):** UA structural
  extraction becomes the primary Step 3 source; KAI providers run only to
  produce a parity report.
- **Phase C — UA only (target after Plan 14 parity gate):** Plan 18 retires the
  transitional KAI provider path from primary scanning.
- The UA Phase2 active path runs only deterministic import-map, batching, and
  structural extraction. `file-analyzer` bounded LLM, semantic graph merge, and
  `ua-analysis-result.json` are deferred.
- `ua-analysis-result.json` / semantic sidecar is a reserved nullable
  snapshot-internal slot. It is not produced or consumed by the Phase2 active
  path, is not part of the required public output set, must not be listed in API
  artifact paths, and frontend code must not depend on it.
- Phase2 Step 6 does not introduce `AssessmentOrchestrator` or AI assessment
  candidates. Plan 17 is deferred and is not a prerequisite for Plan 14, Plan
  18, or Plan 15.
- Phase2 Step 6 is pure Python deterministic assessment.
  `ProfileInferenceService` directly consumes the validated system map,
  confirmed manual-mapping capability candidates, and metadata catalogs.
- The UA semantic result is stored only as a snapshot-internal sidecar in
  Phase2. It has no Phase2 consumer, does not enter canonical facts or public
  artifacts, and does not add frontend fields.
- `ProfileInferenceService` remains the sole owner of final `detected / partial /
  undetermined / not_detected / conflicted` decisions; `detected` still requires
  direct evidence.
- Apply does not rerun UA. It replays `ScanSnapshot.scan_result` from the same
  `scan_id` and produces a new `build_id`; any stored UA semantic sidecar remains
  unchanged and is not consumed. Rescan creates a new `scan_id` and reruns UA.
- UA failure is fail-closed. If the sidecar cannot produce a valid result, the
  build must not proceed into Step 4 or present the scan as complete.
- KAI-Mind does not adopt Understand-Anything Phase 3-7,
  `knowledge-graph.json`, or its dashboard. Canonical output remains
  `ai_system_map.json` plus validated sidecars such as `profile_signals.json`
  and the backend-owned `GraphViewModel`.
- Source of truth: `ref-opensource/kai-mind-understand-anything-integration-boundary.md`
  and
  `docs/work/Timmy/schedule/plan/unfinish/phase4-scanner-expansion/00-phase2-pipeline-ascii-map.md`.

## Related Docs

- JSON payload samples: `docs/work/Timmy/design/EPIC1/frontend-json-handoff/` (organized by Phase2 pipeline step; see root `README.md`)
- Local API endpoints: `docs/API-GUIDE.md`, `frontend/API_CONTRACT.md`

This document describes the expected backend contract after the current Phase 2
plans are implemented. It is not saying every field already exists in current
code. Current source of truth is still:

- `src/kai_mind/core/models/system_map.py`
- `src/kai_mind/core/models/viewer.py`
- `src/kai_mind/core/models/mapping.py`
- `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/00A-introduce-ai-system-map-v2-compatibility-migration.md`
- `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/01-rework-manual-mapping-capability-candidates.md`
- `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/01A-define-ai-system-capability-map-reference-catalog.md`
- `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/02-implement-stackable-profile-inference.md`
- `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/03-consolidate-profile-sidecar-lifecycle.md`
- `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/06-deepen-graph-projection-module.md`
- `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/10-define-profile-rule-catalog-boundary.md`
- `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/11-migrate-profile-rule-metadata-to-toml-catalog.md`
- `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/13-retire-legacy-extension-contract.md`
- `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/15-complete-legacy-v1-retirement-after-compatibility.md`
- `docs/work/Timmy/schedule/plan/unfinish/phase2/dynamic-trace-plan/00-implement-static-call-graph-and-execution-path-mvp.md`

Deferred boundary:

- `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/12-add-runtime-component-trace-contract.md`

Dynamic trace implementation (after static path):

- `docs/work/Timmy/schedule/plan/unfinish/phase2/dynamic-trace-plan/01-implement-runtime-component-trace-mvp.md`

## Contract Layers

```text
source scan / manual decisions
        |
        v
ai-system-map/v2                 generic canonical AI system map
        |
        +--> profile-signals/v1   read-only capability sidecar
        +--> readiness-report/v1  evidence-backed findings
        |
        +--> GraphViewModel       frontend projection, render only
        +--> static execution     call graph / dataflow / execution paths
        +--> Markdown / Mermaid   artifact renderers
```

| Layer | Artifact / model | Canonical? | Frontend should use it for |
|---|---|---:|---|
| Canonical map | `ai_system_map.json`, `AiSystemMapV2` | Yes | Generic components, edges, evidence, risks, endpoints |
| Profile sidecar | `profile_signals.json`, `ProfileInferenceResult` | No | Capability findings, confirmed candidate refs, detail content |
| Readiness report | `readiness_report.json` | No | Findings, next checks, limitations, derived summary |
| Evidence table | `evidence_table.json` | No | Flattened evidence rows for debugging, report joins, and future database table ingestion |
| Static execution artifacts | `call_graph.json`, `dataflow_hints.json`, `execution_paths.json`, `execution_map.mmd` | No | Inferred query path and supporting evidence, not runtime proof |
| Viewer projection | `GraphViewModel` | No | Canvas nodes, edges, filters, details |
| Mapping lifecycle | mapping proposal / manual mapping API | Durable user decision | Mapping generic components/grounding or confirming non-baseline candidates |
| Runtime trace | future contract only | No | Deferred; not a Phase2 acceptance dependency |
| Lookup index | `SystemMapIndex` | Internal only | Backend implementation detail; frontend must not depend on it |

`non-canonical` does not mean "unimportant". It means the data is validated and
useful, but it is not the authoritative `ai-system-map/v2` schema and must not
be written back into `ai_system_map.json`.

## Legacy RAG Compatibility Boundary

`rag-core-v1` may remain readable during the Phase 2 migration so legacy
artifacts, fixtures, and old manual decisions can be interpreted safely. It is
not an active product surface and must not emit a public compatibility-derived
readiness layer or frontend summary.

Grounding, retrieval, citation/source traceability, and delivery-readiness gaps
are represented through the generic Capability Map, `profile_signals.json`, and
`readiness_report.json.findings[]`. If the backend needs legacy slot facts during
adapter migration, those facts stay internal to the adapter and are normalized
into generic v2 components, edges, evidence, profiles, or findings before
reaching public artifacts.

## Fixed Reference Map and Repo Overlay

The first production reference map is catalog version `1` with exactly these ten planes:

| `plane_id` | Display name |
|---|---|
| `input_intent` | Input & Intent Plane |
| `control` | Control Plane |
| `ingestion_indexing` | Ingestion & Indexing Plane |
| `retrieval` | Retrieval Plane |
| `extension_subsystems` | Extension Subsystems Plane |
| `evidence` | Evidence Plane |
| `generation` | Generation Plane |
| `memory_state` | Memory & State Plane |
| `governance_observability` | Governance & Observability Plane |
| `deployment_topology` | Deployment Topology Plane |

The fixed catalog contains exactly these 52 reference nodes:

| `plane_id` | Reference node ids | Count |
|---|---|---:|
| `input_intent` | `user_input`, `session_context`, `query_classifier` | 3 |
| `control` | `planner`, `router`, `agent_loop`, `orchestrator`, `stop_policy`, `human_approval_gate` | 6 |
| `ingestion_indexing` | `document_loader`, `parser`, `chunker`, `metadata_extractor`, `embedder`, `index_builder` | 6 |
| `retrieval` | `dense_retriever`, `sparse_retriever`, `hybrid_retriever`, `graph_retriever`, `memory_retriever`, `web_retriever` | 6 |
| `extension_subsystems` | `graph_rag_system`, `rag_anything_system`, `infini_memory_system`, `corag_federated_system` | 4 |
| `evidence` | `reranker`, `conflict_checker`, `citation_mapper`, `evidence_pack` | 4 |
| `generation` | `context_composer`, `prompt_builder`, `llm_answerer`, `tool_using_generator`, `output_guardrail` | 5 |
| `memory_state` | `session_state`, `working_memory`, `long_term_memory`, `memory_reader`, `memory_writer` | 5 |
| `governance_observability` | `input_guardrail`, `permission_policy`, `human_approval`, `trace_store`, `eval_harness`, `cost_monitor`, `latency_monitor` | 7 |
| `deployment_topology` | `client_app`, `api_server`, `agent_runtime`, `worker_queue`, `tool_network`, `federated_clients` | 6 |

Canonical display labels and ordering are defined in Plan `01A`'s
`Canonical display labels` tree. Serialized contracts and migrations use ids,
never labels, as identity.

Governance and observability are now a canonical plane. A cross-plane governance
lens may still highlight policy, approval, risk, and audit relationships outside
that plane, but it is a derived backend projection and must not duplicate
canonical facts. Each reference node has
catalog metadata including id, plane, label, description, display order, and
activation applicability. Activation applicability is data-only; Python derives
the actual `activation` from evidence. `not_applicable` is used only when
catalog metadata says that a node inherently has no enable/disable semantics; it
is not a backend judgment that a capability does not apply to the current system.

This is a breaking taxonomy revision from the superseded 8-plane / 35-node draft,
but no production reference catalog exists yet. Therefore it does not add a
runtime dual-read requirement: the first shipped catalog is the 10-plane / 52-node
version `1`. Any retained prototype fixture must be converted with explicit
plane/node id mappings; display labels and aliases are not valid migration keys.

```ts
type AssessmentStatus =
  | "detected"
  | "partial"
  | "undetermined"
  | "not_detected"
  | "conflicted";

type ActivationState =
  | "enabled"
  | "disabled"
  | "conditional"
  | "unknown"
  | "conflicted"
  | "not_applicable";

type AssessmentEvidenceKind = "direct" | "indirect" | "explicit_negative";

type AssessmentScope = {
  scan_id: string;
  build_id: string;
  environment_id: string;
};

type ReferenceCapabilityAssessment = {
  reference_node_id: string;
  status: AssessmentStatus;
  activation: ActivationState;
  direct_evidence_ids: string[];
  indirect_evidence_ids: string[];
  explicit_negative_evidence_ids: string[];
  conflict_fields: string[];
  conflict_evidence_ids: string[];
  not_detected_coverage_gate_passed: boolean;
};

type MappingCompleteness = {
  numerator: number;
  denominator: number; // every fixed reference node
  value: number;
  weights: {
    detected: 1;
    partial: 0.5;
    undetermined: 0;
    not_detected: 1;
    conflicted: 0;
  };
};
```

The repo overlay contains only evidence-backed repo components and their
relationships to reference nodes. A reference node describes what can exist; a
repo component describes what this scanned repo contains. The frontend must not
turn a reference node into a detected repo component.

## `ai-system-map/v2`

`ai-system-map/v2` is the active target after Plan 13 cutover. During Plan 00A
compatibility work, the same model is available as an opt-in normalized view while
v1 remains the default output.

```ts
type CanonicalComponent = {
  component_id: string;
  display_name: string;
  canonical_type: string;
  layer: string;
  status: AssessmentStatus;
  activation: ActivationState;
  framework?: string | null;
  evidence_ids: string[];
  metadata: Record<string, unknown>;
};

type CanonicalEdge = {
  edge_id: string;
  source: string;
  target: string;
  relationship: string;
  status: AssessmentStatus;
  evidence_ids: string[];
};

type AiSystemMapV2 = {
  schema_version: "ai-system-map/v2";
  system_type: "ai_system";
  scan_id: string;
  build_id: string;
  environment_id: string;
  project: Project;
  components: CanonicalComponent[];
  edges: CanonicalEdge[];
  evidence: Evidence[];
  endpoints: Endpoint[];
  risk_hints: RiskHint[];
  unmapped_components: UnmappedComponent[];
};
```

The canonical map contains evidence-backed facts. Grounding readiness, capability
profiles, `primary_map_type`, viewer ids, and runtime trace are derived layers and
must not be written back as canonical truth.

## Active Capability Profile Registry

The active registry is generic and capability-based. It is not a fixed RAG
variant taxonomy.

Frontend rule: do not hard-code labels or counts. Render backend-provided
`profile_id`, `label`, `status`, and details.

Profile shape rule: profiles are one-level only. Frontend should render one
profile row / profile attachment per backend-emitted profile. Do not expect or
render nested signal arrays, nested profile nodes, or a second profile
classification layer. Lower-level details such as reranker or query rewrite
should appear only as evidence wording, uncertainty, recommendations, or detail
panel text.

Profile taxonomy rule: the catalog is multi-label and feature-axis based, not a
single inheritance taxonomy. `primary_axis` and optional `secondary_axes` are
metadata on each one-level `ProfileFinding`; they must not introduce nested
profile objects or a second UI classification layer.

| Order | `profile_id` | Display label | Primary axis | What it means |
|---:|---|---|---|---|
| 1 | `rag-grounding` | RAG Grounding | `grounding` | Model output is grounded through retrieved or assembled external context |
| 2 | `agentic-control` | Agentic Control | `agent_control` | Planner, router, state graph, retry/evaluator, or agent loop controls AI system behavior |
| 3 | `tool-calling` | Tool Calling | `tool_use` | LLM or agent can invoke tools or external functions |
| 4 | `memory` | Memory | `memory` | Conversation, entity, vector, or state memory participates in context |
| 5 | `workflow-orchestration` | Workflow Orchestration | `workflow_orchestration` | Workflow graph, DAG, or node/edge artifact orchestrates the AI system |
| 6 | `hybrid-retrieval` | Hybrid Retrieval | `retrieval_strategy` | Dense retrieval plus sparse/keyword retrieval or fused ranking |
| 7 | `reranking` | Reranking | `retrieval_strategy` | Retrieved candidates are reranked before context assembly |
| 8 | `corrective-retrieval` | Corrective Retrieval | `retrieval_strategy` | Retrieval quality is evaluated, corrected, retried, or augmented |
| 9 | `self-reflection` | Self Reflection | `agent_control` | Self-critique/reflection signals affect retrieval or answer generation |
| 10 | `graph-retrieval` | Graph Retrieval | `knowledge_structure` | Graph store, entity graph, or graph retriever supports grounding |
| 11 | `hierarchical-retrieval` | Hierarchical Retrieval | `knowledge_structure` | Tree, recursive summary, parent/child, or hierarchy index is used |
| 12 | `contextual-retrieval` | Contextual Retrieval | `context_enrichment` | Chunks or retrieval units are contextualized before indexing or retrieval |
| 13 | `multimodal-grounding` | Multimodal Grounding | `data_modality` | Images, tables, PDFs, layout, audio, or another non-text modality contributes to grounding |
| 14 | `modular-composition` | Modular Composition | `design_paradigm` | Replaceable providers, registries, plugins, or config-driven modules compose the AI system |
| 15 | `multi-query-retrieval` | Multi-query Retrieval | `retrieval_strategy` | Multiple generated queries, heads, or perspectives feed retrieval |

Notes:

- `rag-grounding` is a capability overlay. Grounding readiness still belongs to
  the readiness report / grounding baseline policy.
- `reranking` is a standalone capability overlay because Phase2 P0 needs to
  explain retrieval strategy and execution path evidence.
- A profile may be `undetermined` when relevant static evidence exists but the
  call/dataflow path is not strong enough.
- Do not create roll-up rows such as `advanced-rag`.

## Legacy RAG Profile Alias Reference

Legacy names such as `advanced-rag`, `agentic-rag`, `graph-knowledge-rag`,
`self-rag`, and `multi-head-rag` may appear in old
fixtures or discussion notes. They are aliases only and must be mapped to the
active capability registry before becoming frontend-facing active output.

## Legacy `ai-system-map/v1` Compatibility Contract

`ai-system-map/v1` is the pre-cutover canonical readiness map. It remains readable
through the 00A loader/adapter and is retained for migration fixtures; after Plan 13
it is not the active output contract.

Top-level shape:

```ts
type RagSystemMap = {
  schema_version: "ai-system-map/v1";
  system_type: "rag";
  classification: Classification;
  project: Project;
  reference_architecture: ReferenceArchitecture;
  scan_depth: "system" | "component" | "code_path";
  scan_summary?: ScanSummary | null;
  components_by_slot: Record<string, ComponentSlot>;
  evidence: Evidence[];
  endpoints: Endpoint[];
  flows: Flow[];
  extensions: ExtensionComponent[];
  unmapped_components: UnmappedComponent[];
  detail_scans: DetailScanResult[];
  risk_hints: RiskHint[];
  recommended_next_checks: RecommendedNextCheck[];
  query_trace_events: QueryTraceEvent[];
};
```

Legacy v1 grounding compatibility slot target:

```text
Indexing
data_sources
  -> document_loader
  -> chunking
  -> embedding_model
  -> vector_store

Query answer
app_api_or_orchestrator
  -> retriever
  -> vector_store
  -> prompt_builder
  -> llm
  -> citation_or_response_composer
```

Expected `ReferenceArchitecture`:

```ts
type ReferenceArchitecture = {
  id: "rag-core-v1";
  version?: "1.1.0" | string | null;
  slots: string[];
  flows: string[];
};
```

Slot status values stay:

```ts
type SlotStatus =
  | "detected"
  | "missing"
  | "not_configured"
  | "not_applicable";
```

Frontend meaning:

- `detected`: backend found evidence for a component in that slot.
- `missing`: required legacy v1 grounding slot has no evidence.
- `not_configured`: the slot applies, but the app appears not to configure it.
- `not_applicable`: the slot does not apply to this validated map shape or
  project context.

### `extensions` and `unmapped_components`

Legacy v1 keeps these fields for backward compatibility, but the new main flow is:

```text
ambiguous component
  -> ask user: is this a grounding baseline component?
      -> yes: manual mapping to an applicable grounding slot/dimension
      -> no: non-baseline capability candidate
  -> assessment emits detected / partial / undetermined / not_detected / conflicted
```

So:

- new Phase 2 UI should not require users to create `extensions`;
- `extensions` may still appear in legacy artifacts and should remain readable;
- `unmapped_components` still exist for ambiguous grounding/component confirmation and
  source evidence navigation;
- confirmed non-baseline decisions are materialized into
  `capability_candidate_components`, not into canonical `ai_system_map.json`.

Plan 00A defines compatibility and Plan 13 removes `extensions` from active output
by switching to `ai-system-map/v2`. The Phase 2 static-readiness path treats
`extensions` as legacy-readable migration data, not as the new product flow.

## Manual Mapping Contract

Existing values remain for compatibility:

```ts
type ManualMappingType =
  | "existing_slot_mapping"
  | "non_baseline_capability_candidate"
  | "new_extension_component";          // legacy compatibility only

type MappingCandidateType =
  | "existing_slot_mapping"
  | "non_baseline_capability_candidate"
  | "needs_more_information"
  | "skip_for_now"
  | "new_extension_component";          // legacy compatibility only
```

Planned `ManualMappingCreate` additions:

```ts
type ManualMappingCreate = {
  project_id: string;
  mapping_type: ManualMappingType;
  decision: "confirmed" | "rejected" | "skip_for_now" | "not_applicable";
  source_unmapped_id?: string | null;
  source_file?: string | null;
  observed_kind?: string | null;
  evidence_ids: string[];
  reason?: string | null;

  // existing-slot path
  target_slot?: string | null;
  component_name?: string | null;
  component_kind?: string | null;
  provider?: string | null;

  // generic non-baseline capability path
  capability_candidate_id?: string | null;
  capability_candidate_name?: string | null;
  capability_candidate_kind?: string | null;

  // legacy extension path; not allowed in active v2 happy path
  extension_id?: string | null;
  extension_name?: string | null;
  extension_kind?: string | null;
  extension_edges?: Array<Record<string, string>>;

  proposal_id?: string | null;
  decision_source: string;
  audit_metadata: Record<string, string>;
};
```

Frontend rule:

- `existing_slot_mapping` answers: "this ambiguous component belongs to a
  grounding slot".
- `non_baseline_capability_candidate` answers: "this is not a grounding
  baseline slot; pass it to capability inference".
- Do not add a profile-level confirm/edit/reject lifecycle in Phase 2.
- Do not auto-create `extension` records for profile misses.

## `capability_candidate_components`

Capability candidates are non-canonical materialized outputs. They should appear in
`profile_signals.json`, not in `ai_system_map.json`. In Phase2 this section refers
only to confirmed non-baseline candidates produced by the manual-mapping lifecycle.
Phase2 does not produce or consume AI assessment candidates.

```ts
type CapabilityCandidateComponent = {
  id: string;
  name: string;
  observed_kind: string;
  status: "confirmed_non_baseline";
  evidence_ids: string[];
  source_unmapped_component_id?: string | null;
  source_file?: string | null;
  proposal_id?: string | null;
  decision_source?: string | null;
};
```

They are evidence-backed refs used by profile inference. They are not graph
topology by themselves unless backend projection emits a related viewer node.

## `profile-signals/v1`

`profile-signals/v1` is a read-only sidecar. During 00A it can be generated from a
validated v1 or v2 normalized map; after Plan 13 its active source is v2. It should
fail closed during map build validation, CI
contract validation, or explicit strict mode if invalid. Normal viewer/API load
must still load the canonical base graph when the sidecar is missing or invalid,
and should mark profile enrichment as unavailable instead of blocking the map.

Top-level shape:

```ts
type ProfileInferenceResult = {
  schema_version: "profile-signals/v1";
  source_schema_version: "ai-system-map/v2";
  scan_id: string;
  build_id: string;
  environment_id: string;
  generated_from_build_id?: string | null;
  profile_catalog_version?: string | null;
  capability_candidate_components: CapabilityCandidateComponent[];
  profiles: ProfileFinding[];
  mapping_completeness: MappingCompleteness;
  summary?: Record<string, number>;
};
```

No nested profile layer:

```ts
// Not part of Phase 2 contract.
type UnsupportedProfileShape = {
  profile_id: string;
  nested_signals: unknown[];
};
```

Profile finding:

```ts
type ProfileStatus = AssessmentStatus;

type ProfileAxis =
  | "grounding"
  | "agent_control"
  | "tool_use"
  | "memory"
  | "workflow_orchestration"
  | "retrieval_strategy"
  | "knowledge_structure"
  | "context_enrichment"
  | "data_modality"
  | "design_paradigm";

type EvidenceStrength =
  | "static_multiple_signals"
  | "static_single_signal"
  | "weak_or_ambiguous_signal"
  | "not_detected";

type ImplementationDepthLevel = 0 | 1 | 2 | 3 | 4;

type ProfileFinding = {
  profile_id: string;
  label: string;
  description?: string | null;
  status: ProfileStatus;
  activation: ActivationState;
  primary_axis: ProfileAxis;
  secondary_axes: ProfileAxis[];
  implementation_depth_level: ImplementationDepthLevel;
  implementation_depth_reason?: string | null;
  coverage_detected: number;
  coverage_total: number;
  detected_signals: string[];
  missing_signals: string[];
  direct_evidence_ids: string[];
  indirect_evidence_ids: string[];
  explicit_negative_evidence_ids: string[];
  evidence_ids: string[];
  evidence_strength: EvidenceStrength;
  uncertainty?: string | null;
  related_unmapped_component_ids: string[];
  related_capability_candidate_component_ids: string[];
  related_risk_hint_ids: string[];
  recommended_next_checks: string[];
  conflict_fields: string[];
  conflict_evidence_ids: string[];
  not_detected_coverage_gate_passed: boolean;
  source: "deterministic_static";
};
```

Status semantics:

- `detected`: at least one direct deterministic evidence item proves the capability.
- `partial`: some required parts have direct support, but the capability is not
  complete enough for `detected`, or all available positive evidence is indirect.
- `undetermined`: profile-relevant signal exists, but static evidence is not
  enough to classify it, or coverage is incomplete.
- `not_detected`: the capability-specific coverage gate passed and no required
  evidence surface supports the assessed capability; explicit negative evidence
  may support this result but absence alone is not explicit negative evidence.
- `conflicted`: one or more named fields have incompatible evidence. Both sides
  remain linked through `conflict_evidence_ids`.

Activation semantics are independent of the five-state assessment. For example,
a capability can be `detected` but `disabled`, or `partial` and `conditional`.

Implementation depth semantics:

- `0`: no observed implementation for this profile.
- `1`: concept, dependency, README claim, naming, prompt, or config-only signal.
- `2`: module or artifact exists, but the query / answer path is not proven
  end-to-end.
- `3`: complete profile-specific pipeline is observed in the query / answer
  path.
- `4`: complete pipeline plus evaluation, benchmark, tests, fallback,
  observability, or comparable production hardening.

`implementation_depth_level` is observed implementation scope, not confidence.
The project intentionally has no `confidence` field. Classification status and
evidence strength decide whether the profile is `detected`; depth only explains
how much of the profile-specific implementation was observed.

Important constraints:

- `detected` must have `evidence_ids`.
- `detected` must have non-empty `direct_evidence_ids`; multiple convergent
  indirect signals cannot substitute for direct evidence.
- indirect-only positive evidence must be `partial`, not `detected`.
- `detected` should normally have `implementation_depth_level >= 3`.
- `partial` must identify supported and missing signals and retain its evidence.
- `undetermined` may have `implementation_depth_level` 1 or 2 when weak but
  relevant implementation evidence exists.
- `not_detected` must have `implementation_depth_level=0`.
- `not_detected` requires `not_detected_coverage_gate_passed=true`; otherwise the
  status is `undetermined`.
- `not_detected` may retain explicit-negative evidence; indirect positive evidence
  belongs on `undetermined`, `partial`, or `conflicted` instead.
- explicit-negative evidence must identify an explicit disabled, bypassed,
  forbidden, deny/skip, or incompatible declaration; absence is not explicit negative.
- `conflicted` requires non-empty `conflict_fields` and evidence for both sides.
- weak / ambiguous evidence belongs in `undetermined`, not `not_detected`.
- no `confidence` field in MVP.
- every profile finding belongs to the result's build/snapshot/environment scope.
- no raw source snippets, raw prompts, full secrets, or absolute paths.
- profile inference is deterministic and local-only for Phase 2 MVP.
- profile inference does not call mapping proposal, manual mapping, or LLM
  proposal providers.

## Artifact Lifecycle

### JSON Artifact Boundary

Phase2 P0 emits multiple sibling JSON artifacts. Each JSON artifact has its own
schema, writer, validation gate, and future table candidate.

| JSON artifact | Future table candidate | Notes |
|---|---|---|
| `ai_system_map.json` | `ai_system_maps`, `components`, `edges` | Canonical AI system facts and canonical evidence refs |
| `evidence_table.json` | `evidence` | Flattened evidence rows keyed by `evidence_id` |
| `call_graph.json` | `call_graphs`, `call_edges`, `entrypoints` | Static inferred call graph |
| `dataflow_hints.json` | `dataflow_hints` | Static shallow dataflow hints |
| `execution_paths.json` | `execution_paths`, `execution_steps` | Static inferred ordered execution paths |
| `profile_signals.json` | `profile_signals`, `profile_findings` | Non-canonical capability overlay |
| `readiness_report.json` | `readiness_reports`, `readiness_findings` | Delivery/readiness findings derived from Capability Map / profiles / evidence gaps |

The Mermaid artifacts, `system_map.mmd` and `execution_map.mmd`, remain render
outputs. They are not JSON table sources.

Successful profile-enabled map build should emit:

```text
<run-dir>/
  ai_system_map.json
  ai_system_map.md
  system_map.mmd
  profile_signals.json
  readiness_report.json
  call_graph.json
  dataflow_hints.json
  execution_paths.json
  evidence_table.json
  execution_map.mmd
```

Planned API / model additions use safe artifact references. Target responses do
not expose server-local absolute paths. Current v1 `*_path` fields remain
compatibility-only until callers migrate.

```ts
type ArtifactRef = {
  artifact_id: string;
  artifact_type:
    | "ai_system_map"
    | "ai_system_map_markdown"
    | "system_map_mermaid"
    | "profile_signals"
    | "readiness_report"
    | "call_graph"
    | "dataflow_hints"
    | "execution_paths"
    | "evidence_table"
    | "execution_map_mermaid"
    | "map_error";
  file_name: string; // basename only; never an absolute or traversal path
  media_type: string;
  sha256: string;
  size_bytes: number;
};

type OutputRun = {
  scan_id: string;
  build_id: string;
  environment_id: string;
  artifacts: ArtifactRef[];
};

type MapBuildResult = {
  status: string;
  scan_id: string;
  build_id: string;
  environment_id: string;
  project_name?: string | null;
  artifacts: ArtifactRef[];
  ai_system_map?: unknown | null;
  viewer_load_result?: unknown | null;
  warnings: string[];
  error?: string | null;
};
```

All sibling artifacts carry the same `scan_id`, `build_id`, and
`environment_id`. `profile_signals.json` is written once from the same validated
build result.
Viewer routes should not recompute profile inference at load time. If the
sidecar is absent or invalid in normal viewer mode, the viewer should return the
base `ai_system_map` / `GraphViewModel` and expose a stable warning such as
`profile_signals_missing` or `profile_signals_invalid`.

Static execution artifacts are also written from the same validated build result.
They are derived, non-canonical artifacts. They may say that static evidence
suggests a path, but must not claim that a runtime query executed that path.

`evidence_table.json` must be emitted as its own file. It may duplicate selected
fields from `ai_system_map.json.evidence[]`, but the purpose is different:
`ai_system_map.json.evidence[]` preserves canonical references inside the map;
`evidence_table.json` provides a flattened, query-friendly evidence table for
debugging, reports, joins, and later database ingestion.

## Static Execution Artifacts

Static execution artifacts are owned by dynamic `00`, but they are part of the
Phase2 P0 static-readiness output. They must never claim runtime execution.

```ts
type StaticExecutionStatus = AssessmentStatus;
type StaticInferenceKind = "static_inferred" | "not_detected";

type StaticArtifactHeader = {
  schema_version: string;
  source_schema_version: "ai-system-map/v2" | string;
  project: Project;
  generated_from_build_id: string;
  runtime_verified: false;
  limitations: string[];
};

type StaticCallEdge = {
  edge_id: string;
  source_ref: string;
  target_ref: string;
  call_kind: "route_to_handler" | "function_call" | "workflow_edge" | "import_call";
  status: StaticExecutionStatus;
  inference_kind: StaticInferenceKind;
  evidence_ids: string[];
  analysis_depth: string;
  evidence_strength?: EvidenceStrength | null;
  limitations: string[];
};

type DataflowHint = {
  hint_id: string;
  source_ref: string;
  target_ref: string;
  flow_kind: "query_to_retriever" | "docs_to_context" | "prompt_to_llm" | string;
  status: StaticExecutionStatus;
  evidence_ids: string[];
  evidence_strength?: EvidenceStrength | null;
  limitations: string[];
};

type ExecutionPath = {
  path_id: string;
  status: StaticExecutionStatus;
  inference_kind: "static_inferred";
  runtime_verified: false;
  evidence_strength?: EvidenceStrength | null;
  steps: Array<{
    step_id: string;
    role:
      | "entrypoint"
      | "handler"
      | "pipeline"
      | "retrieval"
      | "reranking"
      | "context_construction"
      | "generation"
      | "output"
      | "agent_control"
      | "query_rewrite"
      | "evaluation";
    component_ref?: string | null;
    evidence_ids: string[];
  }>;
  limitations: string[];
};

type EvidenceTableRow = {
  evidence_id: string;
  artifact_type: string;
  path: string;
  line_start?: number | null;
  line_end?: number | null;
  json_pointer?: string | null;
  rule_id?: string | null;
  extract_summary?: string | null;
  evidence_strength?: EvidenceStrength | null;
  emits_component_ids: string[];
  emits_edge_ids: string[];
  emits_profile_ids: string[];
  review_state: "not_required" | "needs_confirmation" | "confirmed" | "rejected";
  source_artifact_refs: string[];
};
```

Frontend wording must use "static evidence suggests" or "appears to flow". It
must not use "executed" or "traversed" for static artifacts.

## `GraphViewModel`

`GraphViewModel` is a render-only backend projection of the fixed reference map
plus the evidence-backed repo overlay. Projection nodes must not be written back
into `ai_system_map.json`.

Current shape plus planned extensions:

```ts
type GraphNodeModel = {
  id: string;
  source_id?: string | null;
  type?: string | null;
  slot?: string | null;
  status?: string | null;
  label: string;
  subtitle?: string | null;
  badges: string[];
  evidence_ids: string[];
  risk_hint_ids: string[];

  // planned Phase 2 projection metadata
  semantic_kind?:
    | "reference_capability"
    | "repo_component"
    | "canonical_component"
    | "grounding_component"
    | "slot_placeholder"
    | "unmapped_component"
    | "capability_candidate"
    | "legacy_extension" // legacy-readable only, not active v2 output
    | "profile_attachment"; // migration-only viewer compatibility
  plane_id?:
    | "input_intent"
    | "control"
    | "ingestion_indexing"
    | "retrieval"
    | "extension_subsystems"
    | "evidence"
    | "generation"
    | "memory_state"
    | "governance_observability"
    | "deployment_topology"
    | null;
  reference_node_id?: string | null;
  assessment_status?: AssessmentStatus | null;
  activation?: ActivationState | null;
  direct_evidence_ids?: string[];
  indirect_evidence_ids?: string[];
  explicit_negative_evidence_ids?: string[];
  conflict_fields?: string[];
  profile_id?: string | null;
  primary_anchor_node_id?: string | null;
  anchor_node_ids?: string[];
  related_unmapped_component_ids?: string[];
  related_capability_candidate_component_ids?: string[];
  related_risk_hint_ids?: string[];
};

type GraphEdgeModel = {
  id: string;
  source_id?: string | null;
  flow_id?: string | null;
  from: string;
  to: string;
  relationship?: string | null;
  label?: string | null;
  evidence_ids: string[];
  risk_hint_ids: string[];
};

type GraphDetailsModel = {
  evidence_by_id: Record<string, unknown>;
  risk_hints_by_id: Record<string, unknown>;

  // planned Phase 2 details buckets
  profile_findings_by_id?: Record<string, ProfileFinding>;
  profile_metadata_by_id?: Record<string, unknown>;
  capability_candidates_by_id?: Record<string, CapabilityCandidateComponent>;
};

type GraphFilterModel = {
  id: string;
  label: string;
  kind: string;
  matches_node_ids: string[];
  matches_edge_ids: string[];
};

type GraphLensId =
  | "lens:data"
  | "lens:control"
  | "lens:evidence"
  | "lens:governance"
  | "lens:source"
  | "lens:risk";

type GraphLensModel = {
  id: GraphLensId;
  label: string; // backend fallback label; frontend presentation may override
  kind: "lens";
  display_order: number; // recommended default only
  supported: boolean;
  unavailable_reason?: string | null;
  matches_node_ids: string[];
  matches_edge_ids: string[];
};

type GraphViewModel = {
  schema_version?: string | null;
  source_schema_version?: "ai-system-map/v1" | "ai-system-map/v2" | string | null;
  map_json?: string | null; // current compatibility only; may expose a local path
  scan_id: string;
  build_id: string;
  environment_id: string;
  reference_map_version: string; // first production catalog: "1" (10 planes / 52 nodes)
  mapping_completeness: MappingCompleteness;
  summary?: Record<string, unknown> | null;
  nodes: GraphNodeModel[];
  edges: GraphEdgeModel[];
  details: GraphDetailsModel;
  filters: {
    lenses?: GraphLensModel[]; // Phase 2 target; optional during compatibility migration
    available: GraphFilterModel[];
    behavior?: "highlight_and_dim" | string | null;
  };
};

type ViewerLoadResult = {
  loaded: boolean;
  error_reason?: string | null;
  warnings: string[];
  project_id: string;
  scan_id: string;
  build_id: string;
  environment_id: string;
  based_on_build_id?: string | null;
  applied_mapping_ids: string[];
  map_json?: string | null; // current compatibility only
  artifact_refs: ArtifactRef[];
  ai_system_map: Record<string, unknown>;
  graph_view_model: GraphViewModel;
  profile_inference_result?: ProfileInferenceResult | null;
  readiness_report?: Record<string, unknown> | null;
};
```

Reference-map and overlay rules:

- backend emits every fixed reference node, including `partial`, `undetermined`,
  `not_detected`, and `conflicted`; projection is not detected-only;
- backend emits repo overlay nodes only when repo evidence supports them;
- `reference_capability` and `repo_component` remain different semantic kinds;
- backend chooses all anchor/reference relationships; frontend does not infer
  topology or calculate assessment state from `profile_signals.json`;
- frontend uses backend semantic ids and membership; backend labels are safe
  defaults, while frontend may adjust presentation copy, icons, control layout,
  responsive ordering, and visual treatment without changing semantics;
- frontend displays a legend for five statuses, six activation states, and
  direct / indirect / explicit-negative evidence;
- frontend displays assessment scope and Mapping Completeness with its fixed
  formula and must not relabel it as confidence;
- evidence ids and field-specific conflicts remain available in details.

Filter contract:

```ts
type ProfileAttachmentFilter = {
  id: "filter:profile_attachments";
  label: string;
  kind: string;
  matches_node_ids: string[];
  matches_edge_ids: [];
};
```

The filter uses existing positive filter semantics: matching nodes stay
emphasized and non-matching graph content may dim. It is not default active.

### Phase 2 Graph Lens target contract

This is an approximate backend implementation target for coordinating API and
frontend development. It is not a pixel-level or final interaction design. The
frontend may change button labels, localized copy, icons, button/tab/dropdown
presentation, display order, responsive layout, selected-state styling, and
highlight/dim styling.

The frontend must not change the six semantic ids, rewrite backend-provided
`matches_node_ids` / `matches_edge_ids`, or infer lens membership from labels,
topology, file names, or profile output. If product semantics need to change,
update this contract and backend projection together instead of creating a
frontend-only meaning.

The Phase 2 target emits exactly one `GraphLensModel` for each fixed lens id.
Unsupported lenses remain present with `supported=false`, empty membership, and
a safe `unavailable_reason`, allowing the frontend to render a disabled control
without guessing why it is unavailable.

| Lens id | Backend semantic intent |
|---|---|
| `lens:data` | Data ingestion, transformation, indexing/storage, retrieval data movement, and related components |
| `lens:control` | Orchestration, routing, planning, agent loops, tool control, approval, and control-flow components |
| `lens:evidence` | Evidence capture, grounding support, citations, provenance, verification, and evidence relations |
| `lens:governance` | Policy, approval, guardrails, privacy/access boundaries, and governance-related controls |
| `lens:source` | Source systems, loaders/connectors, artifact origins, source mapping, and traceability |
| `lens:risk` | Risk hints, secret/network exposure, unsafe boundaries, conflicts, and uncertainty requiring attention |

Lens membership is non-exclusive: one node or edge may appear in multiple lens
membership lists. The backend computes membership and returns the complete
fixed reference graph plus repo overlay in one `GraphViewModel`. Initial frontend
switching is local presentation state and should not require one API request per
button click.

`behavior="highlight_and_dim"` means matching content is emphasized while
non-matching content may be dimmed. Lens switching must keep the same canonical
graph, stable node ids, and stable layout; it must not delete nodes/edges or
construct a second graph truth.

## Runtime Query Trace Contract

Phase: Epic 1 Phase 3 follow-up. User decision on 2026-07-01: runtime /
query trace is not part of the Epic 1 Phase 2 MVP. Phase 2 must remain a
static pre-runtime readiness contract.

Static profile projection answers:

```text
Which components / profiles appear to exist?
```

Runtime query trace answers:

```text
Which components did this specific query actually traverse?
```

Those are separate truths. Static profile inference must not pretend that a
query traversed a component.

Planned trace reference:

```ts
type TraceComponentRef = {
  ref_type:
    | "endpoint"
    | "slot"
    | "component_instance"
    | "unmapped_component"
    | "capability_candidate"
    | "profile"
    | "edge";
  ref_id: string;
};

type RuntimeTraceStep = {
  step_id: string;
  label?: string | null;
  component_ref?: TraceComponentRef | null;
  status?: string | null;
  latency_ms?: number | null;
  warnings: string[];
};
```

Planned `QueryTraceEvent` additions:

```ts
type QueryTraceEvent = {
  id: string;
  trace_id?: string | null;
  sequence_index: number;
  timestamp: string;
  event_type?: string | null;
  step_type?: string | null;
  status?: string | null;
  endpoint_id?: string | null;

  // existing compatibility refs
  slot?: string | null;
  component_id?: string | null;
  unmapped_component_id?: string | null;
  edge_id?: string | null;

  // Phase 2 typed refs
  component_ref?: TraceComponentRef | null;
  trace_steps: RuntimeTraceStep[];

  warnings: string[];
  input?: unknown | null;
  output?: unknown | null;
  latency_ms?: number | null;
  error?: unknown | null;
};
```

Frontend trace rules:

- trace replay is transient UI state only;
- do not persist trace-derived graph nodes, edges, or profile evidence;
- if `component_ref` resolves to an existing graph node / edge, highlight it;
- if a ref is unknown, show a warning or unknown step without creating a new
  graph node;
- `profile` refs may focus existing profile attachment nodes only when backend
  already emitted them.

## Frontend Implementation Checklist

- Treat `ai_system_map.json` as the canonical readiness map.
- Treat `profile_signals.json` as validated read-only enrichment, not as a
  required condition for rendering the base graph.
- Keep the assessment UI one-level: fixed reference rows plus repo overlay
  components, with no nested classification layer.
- Render graph from `GraphViewModel`, not from hand-built frontend inference.
- Do not hard-code profile labels, profile count, or profile ordering.
- Do not create frontend-only reference or repo overlay nodes.
- Do not require `extensions` for new Phase 2 profile flow.
- Do not add profile-level manual mapping UI in Phase 2.
- Render all five backend-provided states and all six activation states; do not
  derive either in the frontend.
- Show a legend for five states, activation, and direct / indirect /
  explicit-negative evidence.
- Show `scan_id`, `build_id`, `environment_id`, and Mapping Completeness;
  the denominator is every fixed reference node even when activation is
  `not_applicable`.
- Use `filter:profile_attachments` as a normal positive filter.
- Keep query trace as transient overlay and never write it back to map/profile
  artifacts.

## Example Payload Fragments

Profile sidecar:

```json
{
  "schema_version": "profile-signals/v1",
  "source_schema_version": "ai-system-map/v2",
  "scan_id": "scan:s1",
  "build_id": "build:b2",
  "environment_id": "environment:default-static",
  "mapping_completeness": {
    "numerator": 1.5,
    "denominator": 15,
    "value": 0.1,
    "weights": {
      "detected": 1,
      "partial": 0.5,
      "undetermined": 0,
      "not_detected": 1,
      "conflicted": 0
    }
  },
  "capability_candidate_components": [
    {
      "id": "capability-candidate:config-yaml:reranker",
      "name": "Reranker",
      "observed_kind": "reranker",
      "status": "confirmed_non_baseline",
      "evidence_ids": ["evidence:code_pattern:reranker"],
      "source_unmapped_component_id": "unmapped:reranker",
      "source_file": "src/retrieval/pipeline.py",
      "proposal_id": "mapping-proposal:reranker",
      "decision_source": "manual"
    }
  ],
  "profiles": [
    {
      "profile_id": "reranking",
      "label": "Reranking",
      "description": "A deterministic reranking stage is connected to the retrieval path.",
      "status": "detected",
      "activation": "enabled",
      "primary_axis": "retrieval_strategy",
      "secondary_axes": [],
      "implementation_depth_level": 3,
      "implementation_depth_reason": "Reranker is wired into the retrieval-to-answer path.",
      "coverage_detected": 2,
      "coverage_total": 2,
      "detected_signals": ["reranker_detected", "reranker_connected_to_retrieval"],
      "missing_signals": [],
      "direct_evidence_ids": ["evidence:code_pattern:reranker"],
      "indirect_evidence_ids": [],
      "explicit_negative_evidence_ids": [],
      "evidence_ids": ["evidence:code_pattern:reranker"],
      "evidence_strength": "static_single_signal",
      "uncertainty": null,
      "related_unmapped_component_ids": [],
      "related_capability_candidate_component_ids": [
        "capability-candidate:config-yaml:reranker"
      ],
      "related_risk_hint_ids": [],
      "recommended_next_checks": ["review reranker code path"],
      "conflict_fields": [],
      "conflict_evidence_ids": [],
      "not_detected_coverage_gate_passed": false,
      "source": "deterministic_static"
    },
    {
      "profile_id": "self-reflection",
      "label": "Self Reflection",
      "description": "Model adaptively retrieves, generates, and critiques through self-reflection-like signals.",
      "status": "not_detected",
      "activation": "unknown",
      "primary_axis": "agent_control",
      "secondary_axes": [],
      "implementation_depth_level": 0,
      "implementation_depth_reason": null,
      "coverage_detected": 0,
      "coverage_total": 2,
      "detected_signals": [],
      "missing_signals": ["reflection_loop_detected", "adaptive_retrieval_detected"],
      "direct_evidence_ids": [],
      "indirect_evidence_ids": [],
      "explicit_negative_evidence_ids": [],
      "evidence_ids": [],
      "evidence_strength": "not_detected",
      "uncertainty": "No deterministic evidence found.",
      "related_unmapped_component_ids": [],
      "related_capability_candidate_component_ids": [],
      "related_risk_hint_ids": [],
      "recommended_next_checks": [],
      "conflict_fields": [],
      "conflict_evidence_ids": [],
      "not_detected_coverage_gate_passed": true,
      "source": "deterministic_static"
    }
  ]
}
```

Profile attachment node:

```json
{
  "id": "profile-attachment:rag-grounding:retriever",
  "source_id": "profile:rag-grounding",
  "type": "profile_attachment",
  "semantic_kind": "profile_attachment",
  "profile_id": "rag-grounding",
  "primary_anchor_node_id": "node:slot:retriever",
  "anchor_node_ids": ["node:slot:retriever"],
  "label": "RAG Grounding",
  "subtitle": null,
  "badges": [],
  "evidence_ids": ["evidence:code_pattern:retriever"],
  "risk_hint_ids": [],
  "related_capability_candidate_component_ids": []
}
```

Runtime trace step:

```json
{
  "step_id": "step:reranker",
  "label": "Reranker",
  "component_ref": {
    "ref_type": "capability_candidate",
    "ref_id": "capability-candidate:config-yaml:reranker"
  },
  "status": "completed",
  "latency_ms": 19,
  "warnings": []
}
```
