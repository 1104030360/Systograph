import { z } from "zod";

const stringArray = z.array(z.string()).default([]);
const nullableString = z.string().nullable().optional();

export const assessmentStatusSchema = z.enum([
  "detected",
  "partial",
  "undetermined",
  "not_detected",
  "conflicted",
]);

export const activationStateSchema = z.enum([
  "enabled",
  "disabled",
  "conditional",
  "unknown",
  "conflicted",
  "not_applicable",
]);

export const graphAssessmentScopeSchema = z.object({
  build_id: z.string(),
  scan_id: z.string(),
  environment_id: z.string(),
});

export const graphNodeSchema = z.object({
  id: z.string(),
  source_id: nullableString,
  reference_node_id: nullableString,
  component_id: nullableString,
  profile_id: nullableString,
  plane_id: nullableString,
  type: nullableString,
  semantic_kind: nullableString,
  slot: nullableString,
  status: nullableString,
  activation: activationStateSchema.nullable().optional(),
  label: z.string(),
  subtitle: nullableString,
  badges: stringArray,
  evidence_ids: stringArray,
  direct_evidence_ids: stringArray,
  indirect_evidence_ids: stringArray,
  explicit_negative_evidence_ids: stringArray,
  conflict_fields: z.array(z.record(z.unknown())).default([]),
  not_detected_coverage_gate_passed: z.boolean().nullable().optional(),
  assessment_scope: graphAssessmentScopeSchema.nullable().optional(),
  primary_anchor_node_id: nullableString,
  anchor_node_ids: stringArray,
  related_component_ids: stringArray,
  related_unmapped_component_ids: stringArray,
  related_capability_candidate_component_ids: stringArray,
  related_risk_hint_ids: stringArray,
  description: nullableString,
  implementation_depth_level: z.number().int().nullable().optional(),
  implementation_depth_reason: nullableString,
  evidence_strength: nullableString,
  uncertainty: nullableString,
  recommended_next_checks: stringArray,
  risk_hint_ids: stringArray,
});

export const graphEdgeSchema = z.object({
  id: z.string(),
  source_id: nullableString,
  flow_id: nullableString,
  from: z.string(),
  to: z.string(),
  relationship: nullableString,
  label: nullableString,
  // Compatibility field used by legacy projections only.
  status: nullableString,
  evidence_ids: stringArray,
  risk_hint_ids: stringArray,
});

export const graphRelationshipSchema = z.object({
  id: z.string(),
  kind: z.enum([
    "reference_component_mapping",
    "reference_unmapped_mapping",
    "reference_candidate_mapping",
    "profile_anchor",
    "candidate_source",
  ]),
  source_node_id: z.string(),
  target_node_id: z.string(),
  evidence_ids: stringArray,
});

export const graphEndpointSchema = z.object({
  endpoint_id: z.string(),
  value: z.string(),
  endpoint_type: z.enum(["local", "external"]),
  method: nullableString,
  component_id: nullableString,
  slot: nullableString,
});

export const graphRecommendedNextCheckSchema = z.object({
  id: z.string(),
  target_type: z.string(),
  target: z.string(),
  reason: z.string(),
  action: z.string(),
});

export const evidenceDetailSchema = z
  .object({
    title: z.string().optional(),
    file: z.string().optional(),
    path: z.string().optional(),
    value: z.string().optional(),
  })
  .passthrough();

export const riskHintDetailSchema = z
  .object({
    title: z.string().optional(),
    // Backend uses `severity_hint`; keep `severity` too for forward/back compatibility.
    severity_hint: z.string().optional(),
    severity: z.string().optional(),
    rationale: z.string().optional(),
    uncertainty: z.string().optional(),
  })
  .passthrough();

export const graphFilterSchema = z.object({
  id: z.string(),
  label: z.string(),
  kind: z.string(),
  active: z.boolean().default(false),
  matches_node_ids: stringArray,
  matches_edge_ids: stringArray,
});

export const graphLensSchema = z.object({
  id: z.string(),
  label: z.string(),
  supported: z.boolean().default(true),
  unavailable_reason: z.string().nullable().optional(),
  matches_node_ids: stringArray,
  matches_edge_ids: stringArray,
});

export const mappingCompletenessSchema = z.object({
  numerator: z.number().nonnegative(),
  denominator: z.number().positive(),
  value: z.number().min(0).max(1),
  weights: z.object({
    detected: z.number(),
    partial: z.number(),
    undetermined: z.number(),
    not_detected: z.number(),
    conflicted: z.number(),
  }),
});

export const scanSummarySchema = z
  .object({
    status: z.string().optional(),
    files_scanned: z.number().optional(),
    files_skipped: z.number().optional(),
    detected_slots: z.number().optional(),
    missing_slots: z.number().optional(),
    not_configured_slots: z.number().optional(),
    unmapped_components: z.number().optional(),
    risk_hints: z.number().optional(),
    secret_masking_applied: z.boolean().optional(),
  })
  .passthrough();

export type ScanSummary = z.infer<typeof scanSummarySchema>;

export const graphViewModelSchema = z.object({
  schema_version: nullableString,
  source_schema_version: nullableString,
  project_id: nullableString,
  scan_id: nullableString,
  build_id: nullableString,
  environment_id: nullableString,
  generated_from_build_id: nullableString,
  reference_map_version: nullableString,
  mapping_completeness: mappingCompletenessSchema.nullable().optional(),
  map_json: nullableString,
  summary: z.record(z.unknown()).nullable().optional(),
  nodes: z.array(graphNodeSchema),
  edges: z.array(graphEdgeSchema),
  relationships: z.array(graphRelationshipSchema).default([]),
  endpoints: z.array(graphEndpointSchema).default([]),
  recommended_next_checks: z.array(graphRecommendedNextCheckSchema).default([]),
  details: z.object({
    evidence_by_id: z.record(evidenceDetailSchema).default({}),
    risk_hints_by_id: z.record(riskHintDetailSchema).default({}),
    reference_assessments_by_id: z.record(z.record(z.unknown())).default({}),
    profile_findings_by_id: z.record(z.record(z.unknown())).default({}),
    capability_candidates_by_id: z.record(z.record(z.unknown())).default({}),
  }),
  filters: z.object({
    available: z.array(graphFilterSchema).default([]),
    lenses: z.array(graphLensSchema).default([]),
    behavior: z.string().nullable().optional(),
  }),
});

export const legacyViewerPayloadSchema = z.object({
  sample_meta: z.record(z.unknown()).optional(),
  viewer_load_result: z.object({
    loaded: z.boolean(),
    error_reason: z.string().nullable().optional(),
    map_json: z.string().nullable().optional(),
    ai_system_map: z.record(z.unknown()).and(
      z.object({
        schema_version: z.string().optional(),
        system_type: z.string().optional(),
        scan_depth: z.string().optional(),
        scan_summary: scanSummarySchema.optional(),
        query_trace_events: z.array(z.record(z.unknown())).optional(),
        unmapped_components: z.array(z.record(z.unknown())).optional(),
      }),
    ),
    graph_view_model: graphViewModelSchema,
  }),
  trace_result_samples: z.record(z.record(z.unknown())).optional(),
  detail_scan_result_sample: z.record(z.unknown()).optional(),
  mapping_proposal_result_sample: z.record(z.unknown()).optional(),
  invalid_map_error_sample: z.record(z.unknown()).optional(),
});

export const artifactRefSchema = z.object({
  artifact_id: z.string(),
  artifact_type: z.string(),
  file_name: z
    .string()
    .min(1)
    .refine((value) => !value.includes("/") && !value.includes("\\"), "file_name must be a basename"),
  media_type: z.string(),
  sha256: z.string().regex(/^[a-f0-9]{64}$/i),
  size_bytes: z.number().int().nonnegative(),
});

export const frontendAiSystemMapSchema = z.record(z.unknown()).and(
  z.object({
    schema_version: z.string().optional(),
    system_type: z.string().optional(),
    scan_id: z.string().optional(),
    build_id: z.string().optional(),
    environment_id: z.string().optional(),
    generated_from_build_id: z.string().optional(),
    scan_depth: z.string().optional(),
    scan_summary: scanSummarySchema.optional(),
    query_trace_events: z.array(z.record(z.unknown())).optional(),
    unmapped_components: z.array(z.record(z.unknown())).optional(),
  }),
);

export const frontendViewerLoadResultSchema = z.object({
  loaded: z.boolean(),
  error_reason: z.string().nullable().optional(),
  warnings: stringArray,
  project_id: z.string().nullable(),
  scan_id: z.string().nullable(),
  build_id: z.string().nullable(),
  environment_id: z.string().nullable(),
  generated_from_build_id: z.string().nullable(),
  based_on_build_id: z.string().nullable().optional(),
  applied_mapping_ids: stringArray,
  artifact_refs: z.array(artifactRefSchema).default([]),
  map_json: z.string().nullable().optional(),
  ai_system_map: frontendAiSystemMapSchema,
  profile_inference_result: z.record(z.unknown()).nullable(),
  readiness_report: z.record(z.unknown()).nullable(),
  graph_view_model: graphViewModelSchema,
});

export const viewerPayloadSchema = z.object({
  // "phase2-build": current MapBuildScopedResponse — phase2 lineage/sidecars
  // wrapped around the v1 base graph projection (API-GUIDE §map-builds).
  contract_source: z.enum(["legacy-v1", "phase2", "phase2-build"]),
  viewer_load_result: frontendViewerLoadResultSchema,
  sample_meta: z.record(z.unknown()).optional(),
  trace_result_samples: z.record(z.record(z.unknown())).optional(),
  detail_scan_result_sample: z.record(z.unknown()).optional(),
  mapping_proposal_result_sample: z.record(z.unknown()).optional(),
  invalid_map_error_sample: z.record(z.unknown()).optional(),
});

export const detailScanDepthSchema = z.enum(["component", "code_path"]);
export const detailScanTargetTypeSchema = z.enum([
  "component_slot",
  "component_instance",
  "unmapped_component",
  "edge",
  "evidence",
]);

export const detailScanFindingSchema = z.object({
  kind: z.string(),
  summary: z.string(),
  evidence_ids: stringArray,
  best_effort: z.boolean().nullable().optional(),
});

function isProjectRelativePosixPath(value: string): boolean {
  if (!value || value.startsWith("/") || value.startsWith("\\\\") || /^[A-Za-z]:/.test(value)) return false;
  if (value.includes("\\")) return false;
  return value.split("/").every((segment) => segment !== "" && segment !== "..");
}

export const detailScanCodePathStepSchema = z.object({
  file: z.string().refine(isProjectRelativePosixPath, "file must be a project-relative POSIX path"),
  symbol: z.string().nullable().optional(),
  line_start: z.number().int().positive().nullable().optional(),
  line_end: z.number().int().positive().nullable().optional(),
  evidence_id: z.string().nullable().optional(),
  best_effort: z.boolean().nullable().optional(),
});

export const detailScanResultSchema = z.object({
  id: z.string(),
  target_type: detailScanTargetTypeSchema,
  target: z.string(),
  scan_depth: detailScanDepthSchema,
  status: z.string(),
  replay_depth: z.string().nullable().optional(),
  findings: z.array(detailScanFindingSchema).default([]),
  code_path: z.array(detailScanCodePathStepSchema).default([]),
  warnings: stringArray,
  best_effort: z.boolean().nullable().optional(),
  context_limits: z.record(z.unknown()).default({}),
});

export const detailScanCreateRequestSchema = z.object({
  project_id: z.string().min(1),
  // Frontend v2 deliberately requires a base build even though the backend
  // retains a legacy latest-build fallback for older clients.
  build_id: z.string().min(1),
  target_type: detailScanTargetTypeSchema,
  target: z.string().min(1),
  scan_depth: detailScanDepthSchema,
});

export const detailScanResponseSchema = z.object({
  project_id: z.string(),
  detail_scan: detailScanResultSchema,
  ai_system_map: frontendAiSystemMapSchema,
  source_build_id: z.string().nullable().optional(),
  build_id: z.string().nullable().optional(),
  scan_id: z.string().nullable().optional(),
  viewer_load_result: z
    .object({
      loaded: z.boolean(),
      error_reason: z.string().nullable().optional(),
      map_json: z.string().nullable().optional(),
      ai_system_map: frontendAiSystemMapSchema,
      graph_view_model: graphViewModelSchema,
    })
    .nullable()
    .optional(),
  warnings: stringArray,
});

export const scanProgressEventSchema = z.object({
  event: z.string().optional(),
  type: z.string().optional(),
  status: z.string().optional(),
  stage: z.string().optional(),
  message: z.string().optional(),
  percent: z.number().min(0).max(100).optional(),
  node_id: z.string().optional(),
  edge_id: z.string().optional(),
  component_id: z.string().optional(),
  source_id: z.string().optional(),
  slot: z.string().optional(),
  evidence_id: z.string().optional(),
  scan_depth: z.string().optional(),
  timestamp: z.string().optional(),
});

export type GraphNodeModel = z.infer<typeof graphNodeSchema>;
export type GraphEdgeModel = z.infer<typeof graphEdgeSchema>;
export type GraphRelationshipModel = z.infer<typeof graphRelationshipSchema>;
export type GraphFilterModel = z.infer<typeof graphFilterSchema>;
export type GraphLensModel = z.infer<typeof graphLensSchema>;
export type GraphViewModel = z.infer<typeof graphViewModelSchema>;
export type ViewerPayload = z.infer<typeof viewerPayloadSchema>;
export type ArtifactRef = z.infer<typeof artifactRefSchema>;
export type AssessmentStatus = z.infer<typeof assessmentStatusSchema>;
export type ActivationState = z.infer<typeof activationStateSchema>;
export type MappingCompleteness = z.infer<typeof mappingCompletenessSchema>;
export type ScanProgressEvent = z.infer<typeof scanProgressEventSchema>;
export type DetailScanDepth = z.infer<typeof detailScanDepthSchema>;
export type DetailScanTargetType = z.infer<typeof detailScanTargetTypeSchema>;
export type DetailScanFinding = z.infer<typeof detailScanFindingSchema>;
export type DetailScanCodePathStep = z.infer<typeof detailScanCodePathStepSchema>;
export type DetailScanResult = z.infer<typeof detailScanResultSchema>;
export type DetailScanCreateRequest = z.infer<typeof detailScanCreateRequestSchema>;
export type DetailScanResponse = z.infer<typeof detailScanResponseSchema>;

export type DataSourceMode = "sample" | "api";

export const apiErrorSchema = z
  .object({
    detail: z.union([z.string(), z.record(z.unknown()), z.array(z.unknown())]).optional(),
  })
  .passthrough();

export const projectImportRequestSchema = z.object({
  source_type: z.literal("local_path"),
  project_path: z.string().min(1),
});

export const projectImportResponseSchema = z.object({
  project_id: z.string(),
  source_type: z.literal("local_path"),
  project_name: z.string(),
  project_path: z.string(),
});

export const scanBoundaryTargetSchema = z.object({
  path: z.string(),
  target_type: z.string(),
  risk_type: z.string(),
  reason: z.string(),
  size_bytes: z.number().nullable().optional(),
  fingerprint: z.string(),
});

export const scanBoundaryEvidencePacketSchema = z.object({
  project_id: z.string(),
  target_path: z.string(),
  risk_type: z.string(),
  reason: z.string(),
  evidence_ids: z.array(z.string()).default([]),
  rule_ids: z.array(z.string()).default([]),
  masked_evidence_values: z.array(z.string()).default([]),
  masked_snippets: z.array(z.string()).default([]),
  context_limits: z.record(z.union([z.string(), z.number(), z.boolean()])).default({}),
});

export const scanBoundaryActionSchema = z.enum(["scan_this_run", "skip_this_run"]);

export const scanBoundaryProposalSchema = z.object({
  proposal_id: z.string(),
  project_id: z.string(),
  status: z.literal("pending_user_confirmation"),
  target: scanBoundaryTargetSchema,
  evidence_packet: scanBoundaryEvidencePacketSchema,
  available_actions: z.array(scanBoundaryActionSchema).default(["scan_this_run", "skip_this_run"]),
  created_at: z.string(),
  updated_at: z.string(),
});

export const scanBoundaryDecisionSchema = z.object({
  target_path: z.string(),
  fingerprint: z.string(),
  decision: scanBoundaryActionSchema,
  reason: z.string().optional(),
});

export const scanCreateRequestSchema = z.object({
  project_id: z.string(),
  scan_depth: z.literal("system").default("system"),
  output: z.string().default("outputs"),
  redact_root_path: z.boolean().default(true),
  no_snippets: z.boolean().default(false),
  boundary_decisions: z.array(scanBoundaryDecisionSchema).default([]),
});

export const scanCreateResponseSchema = z.object({
  scan_id: z.string(),
  project_id: z.string(),
  status: z.enum(["completed", "error", "requires_boundary_decision"]),
  build_result: z.record(z.unknown()).nullable().optional(),
  boundary_proposals: z.array(scanBoundaryProposalSchema).default([]),
  available_boundary_actions: z.array(scanBoundaryActionSchema).default(["scan_this_run", "skip_this_run"]),
});

export type ApiErrorPayload = z.infer<typeof apiErrorSchema>;
export type ProjectImportRequest = z.infer<typeof projectImportRequestSchema>;
export type ProjectImportResponse = z.infer<typeof projectImportResponseSchema>;
export type ScanBoundaryAction = z.infer<typeof scanBoundaryActionSchema>;
export type ScanBoundaryProposal = z.infer<typeof scanBoundaryProposalSchema>;
export type ScanBoundaryDecision = z.infer<typeof scanBoundaryDecisionSchema>;
export type ScanCreateRequest = z.infer<typeof scanCreateRequestSchema>;
export type ScanCreateResponse = z.infer<typeof scanCreateResponseSchema>;

export type Selection =
  | { kind: "node"; id: string }
  | { kind: "edge"; id: string }
  | { kind: "trace"; id: string }
  | null;

export const traceEventSchema = z.object({
  id: z.string(),
  trace_id: z.string().nullable().optional(),
  sequence_index: z.number().int().nonnegative(),
  timestamp: z.string(),
  event_type: z.string().nullable().optional(),
  replay_depth: nullableString,
  status: z.string().nullable().optional(),
  query_sent: z.boolean().nullable().optional(),
  endpoint_id: z.string().nullable().optional(),
  slot: z.string().nullable().optional(),
  component_id: z.string().nullable().optional(),
  unmapped_component_id: z.string().nullable().optional(),
  edge_id: z.string().nullable().optional(),
  evidence_id: z.string().nullable().optional(),
  warnings: stringArray,
  step_type: z.string().nullable().optional(),
  latency_ms: z.number().nullable().optional(),
  latency: z.string().nullable().optional(),
  error: z.unknown().nullable().optional(),
  input: z.unknown().nullable().optional(),
  output: z.unknown().nullable().optional(),
  retrieved_chunks: z.unknown().nullable().optional(),
});

export const traceRunStatusSchema = z.enum(["completed", "partial", "endpoint_not_found", "error"]);

export const traceRunResultSchema = z.object({
  trace_id: z.string(),
  status: traceRunStatusSchema,
  query_sent: z.boolean(),
  endpoint_id: z.string(),
  source_scan_id: z.string().nullable().optional(),
  source_build_id: z.string().nullable().optional(),
  events: z.array(traceEventSchema).default([]),
  warnings: stringArray,
  error_reason: z.string().nullable().optional(),
});

export const traceCreateRequestSchema = z.object({
  project_id: z.string().min(1),
  build_id: z.string().min(1),
  endpoint_id: z.string().min(1),
  query: z.string().min(1),
  timeout_seconds: z.number().positive().max(120),
});

export type TraceEvent = z.infer<typeof traceEventSchema>;
export type TraceRunStatus = z.infer<typeof traceRunStatusSchema>;
export type TraceRunResult = z.infer<typeof traceRunResultSchema>;
export type TraceCreateRequest = z.infer<typeof traceCreateRequestSchema>;

export type ScanTarget = {
  id: string;
  label: string;
  kind: "node" | "edge";
};

/* ============================================================================
   Scan Template / Mapping Profile  (NEW API — not yet implemented)
   The selection API does not exist yet, so these are served from a mock seam
   (services/scanTemplateApi.ts). Shapes are designed to accept real responses
   unchanged once the backend lands.
   ========================================================================== */
export const scanProfileKind = z.enum(["system_default", "project_custom"]);

export const scanProfileSchema = z.object({
  profile_id: z.string(),
  kind: scanProfileKind,
  name: z.string(),
  version_label: z.string(), // "rag-core-v1" | "project-custom-v1"
  read_only: z.boolean().default(false),
  derived_from: z.string().nullable().optional(),
  description: z.string().optional(),
  core_components: z.array(z.object({ slot: z.string(), label: z.string() })).default([]),
  stats: z.object({ confirmed: z.number(), pending: z.number(), skipped: z.number() }).optional(),
});

export const scanTemplateStateSchema = z.object({
  project_id: z.string(),
  project_name: z.string(),
  selected_profile_id: z.string(),
  profiles: z.array(scanProfileSchema),
});

export const mappingSource = z.enum(["ai_suggested", "user_confirmed", "fallback_rule"]);

/* A concrete piece of code evidence a mapping is based on. The backend extracts
   these from function-interaction analysis, so a mapping cites *what it saw*
   rather than a guessed confidence score. */
export const evidenceRefSchema = z.object({
  evidence_id: z.string(),
  file: z.string(),
  symbol: z.string().optional(), // function / class / export the evidence points at
  line: z.number().optional(),
  label: z.string().optional(), // short human-readable summary (AI-rewritten)
});

export const confirmedMappingRowSchema = z.object({
  mapping_id: z.string(),
  node_path: z.string(),
  node_kind: z.string().optional(),
  target_slot: z.string(),
  target_label: z.string(),
  source: mappingSource,
  evidence: z.array(evidenceRefSchema).default([]),
  updated_at: z.string(),
});

export const pendingProposalRowSchema = z.object({
  unmapped_id: z.string(),
  node_path: z.string(),
  node_kind: z.string().optional(),
  candidate_count: z.number(),
  best_candidate: z.string(),
  evidence_count: z.number().optional(),
});

export const skippedDecisionRowSchema = z.object({
  decision_id: z.string(),
  node_path: z.string(),
  node_kind: z.string().optional(),
  reason: z.string(),
  skipped_at: z.string(),
});

/* ============================================================================
   Mapping Proposal  (matches the real /api/mapping-proposals contract)
   ========================================================================== */
export const mappingCandidateSchema = z.object({
  candidate_id: z.string(),
  candidate_type: z.enum([
    "existing_slot_mapping",
    "non_baseline_capability_candidate",
    "needs_more_information",
    "skip_for_now",
  ]),
  recommendation_level: z.string().optional(),
  source: z.enum(["ai_suggested", "fallback_rule", "deterministic"]).optional(),
  target_slot: z.string().nullable().optional(),
  component_name: z.string().nullable().optional(),
  component_kind: z.string().nullable().optional(),
  provider: z.string().nullable().optional(),
  proposed_capability_candidate_id: z.string().nullable().optional(),
  proposed_capability_candidate_name: z.string().nullable().optional(),
  proposed_capability_candidate_kind: z.string().nullable().optional(),
  label: z.string().optional(),
  rank: z.number().int().positive().optional(),
  // The backend may still send a confidence score, but the UI does not surface
  // it for already-detected components — it lists the cited evidence instead.
  confidence: z.number().min(0).max(1).optional(),
  rationale: z.string(),
  evidence_ids: z.array(z.string()).default([]),
  evidence_refs: z.array(evidenceRefSchema).default([]),
  uncertainty_reason: z.string().nullable().optional(),
  suggested_edges: z.array(z.record(z.unknown())).optional(),
  flow_hint: z.string().nullable().optional(),
});

export const mappingProposalSchema = z.object({
  proposal_id: z.string(),
  project_id: z.string(),
  source_unmapped_id: z.string(),
  source_path: z.string().optional(),
  status: z.enum(["pending_user_confirmation", "accepted", "edited", "rejected", "skipped"]),
  candidates: z.array(mappingCandidateSchema).default([]),
  evidence_packet: z.record(z.unknown()).optional(),
  provider_name: z.string(), // "deterministic" | "nvidia-nim"
  provider_error_reason: z.string().nullable().optional(),
  user_description: z.string().nullable().optional(),
  available_actions: z.array(z.string()).default([]),
  created_at: z.string(),
  updated_at: z.string(),
});

// edited_mapping body from API-GUIDE §4/§5 (ManualMappingCreate, confirmed)
export const manualMappingCreateSchema = z.object({
  project_id: z.string(),
  mapping_type: z.enum(["existing_slot_mapping", "non_baseline_capability_candidate"]),
  decision: z.literal("confirmed"),
  source_unmapped_id: z.string(),
  evidence_ids: z.array(z.string()).default([]),
  target_slot: z.string().nullable().optional(),
  component_name: z.string().nullable().optional(),
  component_kind: z.string().nullable().optional(),
  capability_candidate_id: z.string().nullable().optional(),
  capability_candidate_name: z.string().nullable().optional(),
  capability_candidate_kind: z.string().nullable().optional(),
  reason: z.string().optional(),
});

// decision request (POST .../{proposal_id}/decision)
export const proposalDecisionSchema = z.discriminatedUnion("decision", [
  z.object({ decision: z.literal("accept"), candidate_id: z.string() }),
  z.object({ decision: z.literal("edit"), edited_mapping: manualMappingCreateSchema }),
  z.object({ decision: z.literal("reject"), reason: z.string().optional() }),
  z.object({ decision: z.literal("skip_for_now"), reason: z.string().optional() }),
]);

export type EvidenceRef = z.infer<typeof evidenceRefSchema>;
export type ScanProfile = z.infer<typeof scanProfileSchema>;
export type ScanTemplateState = z.infer<typeof scanTemplateStateSchema>;
export type ConfirmedMappingRow = z.infer<typeof confirmedMappingRowSchema>;
export type PendingProposalRow = z.infer<typeof pendingProposalRowSchema>;
export type SkippedDecisionRow = z.infer<typeof skippedDecisionRowSchema>;
export type MappingProposal = z.infer<typeof mappingProposalSchema>;
export type MappingCandidate = z.infer<typeof mappingCandidateSchema>;
export type ManualMappingCreate = z.infer<typeof manualMappingCreateSchema>;
export type ProposalDecision = z.infer<typeof proposalDecisionSchema>;
export type MappingSource = z.infer<typeof mappingSource>;
