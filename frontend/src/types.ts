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
  evidence_ids: stringArray,
  risk_hint_ids: stringArray,
});

export const graphFilterSchema = z.object({
  id: z.string(),
  label: z.string(),
  kind: z.string(),
  matches_node_ids: stringArray,
  matches_edge_ids: stringArray,
});

export const graphViewModelSchema = z.object({
  schema_version: z.string().optional(),
  source_schema_version: z.string().optional(),
  map_json: z.string().optional(),
  summary: z.record(z.unknown()).optional(),
  nodes: z.array(graphNodeSchema),
  edges: z.array(graphEdgeSchema),
  details: z.object({
    evidence_by_id: z.record(z.record(z.unknown())).default({}),
    risk_hints_by_id: z.record(z.record(z.unknown())).default({}),
  }),
  filters: z.object({
    available: z.array(graphFilterSchema).default([]),
    behavior: z.string().optional(),
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

export type GraphNodeModel = z.infer<typeof graphNodeSchema>;
export type GraphEdgeModel = z.infer<typeof graphEdgeSchema>;
export type GraphFilterModel = z.infer<typeof graphFilterSchema>;
export type GraphViewModel = z.infer<typeof graphViewModelSchema>;
export type ViewerPayload = z.infer<typeof viewerPayloadSchema>;

export type Selection =
  | { kind: "node"; id: string }
  | { kind: "edge"; id: string }
  | { kind: "trace"; id: string }
  | null;

export type TraceEvent = {
  id?: string;
  trace_id?: string;
  sequence_index?: number;
  replay_depth?: string;
  slot?: string | null;
  component_id?: string | null;
  unmapped_component_id?: string | null;
  edge_id?: string | null;
  step_type?: string;
  latency_ms?: number;
  error?: { code?: string; message?: string } | null;
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
};

export type ScanTarget = {
  id: string;
  label: string;
  kind: "node" | "edge";
};
