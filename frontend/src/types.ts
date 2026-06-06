import { z } from "zod";

const stringArray = z.array(z.string()).default([]);

export const graphNodeSchema = z.object({
  id: z.string(),
  source_id: z.string().optional(),
  type: z.string().optional(),
  slot: z.string().nullable().optional(),
  status: z.string().optional(),
  label: z.string(),
  subtitle: z.string().nullable().optional(),
  badges: stringArray,
  evidence_ids: stringArray,
  risk_hint_ids: stringArray,
});

export const graphEdgeSchema = z.object({
  id: z.string(),
  source_id: z.string().optional(),
  flow_id: z.string().optional(),
  from: z.string(),
  to: z.string(),
  relationship: z.string().optional(),
  label: z.string().nullable().optional(),
  status: z.string().nullable().optional(),
  evidence_ids: stringArray,
  risk_hint_ids: stringArray,
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
  matches_node_ids: stringArray,
  matches_edge_ids: stringArray,
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
  schema_version: z.string().optional(),
  source_schema_version: z.string().optional(),
  map_json: z.string().optional(),
  summary: z.record(z.unknown()).optional(),
  nodes: z.array(graphNodeSchema),
  edges: z.array(graphEdgeSchema),
  details: z.object({
    evidence_by_id: z.record(evidenceDetailSchema).default({}),
    risk_hints_by_id: z.record(riskHintDetailSchema).default({}),
  }),
  filters: z.object({
    available: z.array(graphFilterSchema).default([]),
    behavior: z.string().nullable().optional(),
  }),
});

export const viewerPayloadSchema = z.object({
  sample_meta: z.record(z.unknown()).optional(),
  viewer_load_result: z.object({
    loaded: z.boolean(),
    error_reason: z.string().nullable().optional(),
    map_json: z.string().optional(),
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
export type GraphFilterModel = z.infer<typeof graphFilterSchema>;
export type GraphViewModel = z.infer<typeof graphViewModelSchema>;
export type ViewerPayload = z.infer<typeof viewerPayloadSchema>;
export type ScanProgressEvent = z.infer<typeof scanProgressEventSchema>;

export type DataSourceMode = "sample" | "api";

export type Selection =
  | { kind: "node"; id: string }
  | { kind: "edge"; id: string }
  | { kind: "trace"; id: string }
  | null;

export const traceEventSchema = z.object({
  id: z.string().optional(),
  trace_id: z.string().optional(),
  sequence_index: z.number().optional(),
  replay_depth: z.string().optional(),
  slot: z.string().nullable().optional(),
  component_id: z.string().nullable().optional(),
  unmapped_component_id: z.string().nullable().optional(),
  edge_id: z.string().nullable().optional(),
  step_type: z.string().optional(),
  latency_ms: z.number().optional(),
  error: z
    .object({ code: z.string().optional(), message: z.string().optional() })
    .nullable()
    .optional(),
  input: z.record(z.unknown()).optional(),
  output: z.record(z.unknown()).optional(),
});

export type TraceEvent = z.infer<typeof traceEventSchema>;

export type ScanTarget = {
  id: string;
  label: string;
  kind: "node" | "edge";
};
