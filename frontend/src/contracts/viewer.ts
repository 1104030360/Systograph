import { z } from "zod";
import {
  activationStateSchema,
  assessmentStatusSchema,
  frontendViewerLoadResultSchema,
  graphNodeSchema,
  graphViewModelSchema,
  legacyViewerPayloadSchema,
  mappingCompletenessSchema,
  viewerPayloadSchema,
  type ViewerPayload,
} from "../types";

const workflowStatusSchema = z.enum(["needs_review", "confirmed_non_baseline"]);

const phase2GraphNodeSchema = graphNodeSchema.extend({
  status: z.union([assessmentStatusSchema, workflowStatusSchema]),
  activation: activationStateSchema,
  semantic_kind: z.string(),
});

const phase2GraphViewModelSchema = graphViewModelSchema.extend({
  schema_version: z.literal("graph-view-model/v1"),
  source_schema_version: z.literal("ai-system-map/v2"),
  project_id: z.string(),
  scan_id: z.string(),
  build_id: z.string(),
  environment_id: z.string(),
  generated_from_build_id: z.string(),
  reference_map_version: z.string(),
  mapping_completeness: mappingCompletenessSchema,
  nodes: z.array(phase2GraphNodeSchema),
});

const phase2BuildGraphViewModelSchema = graphViewModelSchema.extend({
  schema_version: z.literal("graph-view-model/v1"),
  source_schema_version: z.literal("ai-system-map/v2"),
  project_id: z.string(),
  scan_id: z.string(),
  build_id: z.string(),
  environment_id: z.string(),
  generated_from_build_id: z.string(),
  reference_map_version: z.string(),
});

const phase2AiSystemMapSchema = z
  .object({
    schema_version: z.literal("ai-system-map/v2"),
    system_type: z.string(),
    scan_id: z.string(),
    build_id: z.string(),
    environment_id: z.string(),
    generated_from_build_id: z.string(),
    project: z
      .object({
        project_id: z.string(),
        name: z.string(),
        root_path: z.string().nullable(),
        root_path_redacted: z.string().nullable().optional(),
        path_mode: z.string(),
      })
      .passthrough(),
    components: z.array(z.record(z.unknown())),
    edges: z.array(z.record(z.unknown())),
    evidence: z.array(z.record(z.unknown())),
    endpoints: z.array(z.record(z.unknown())),
    risk_hints: z.array(z.record(z.unknown())),
    unmapped_components: z.array(z.record(z.unknown())),
  })
  .passthrough();

const referenceAssessmentSchema = z
  .object({
    reference_node_id: z.string(),
    plane_id: z.string(),
    status: assessmentStatusSchema,
    activation: activationStateSchema,
    scan_id: z.string(),
    build_id: z.string(),
    environment_id: z.string(),
    direct_evidence_ids: z.array(z.string()),
    indirect_evidence_ids: z.array(z.string()),
    explicit_negative_evidence_ids: z.array(z.string()),
  })
  .passthrough();

const profileFindingSchema = z
  .object({
    profile_id: z.string(),
    label: z.string(),
    status: assessmentStatusSchema,
    activation: activationStateSchema,
    scan_id: z.string(),
    build_id: z.string(),
    environment_id: z.string(),
    description: z.string().nullable().default(null),
    primary_axis: z.string(),
    secondary_axes: z.array(z.string()).default([]),
    coverage_detected: z.number().int().nonnegative(),
    coverage_total: z.number().int().nonnegative(),
    detected_signals: z.array(z.string()).default([]),
    missing_signals: z.array(z.string()).default([]),
    evidence_ids: z.array(z.string()),
    direct_evidence_ids: z.array(z.string()).default([]),
    indirect_evidence_ids: z.array(z.string()).default([]),
    explicit_negative_evidence_ids: z.array(z.string()).default([]),
    implementation_depth_level: z.number().int().nonnegative(),
    implementation_depth_reason: z.string().nullable().default(null),
    recommended_next_checks: z.array(z.string()).default([]),
    related_component_ids: z.array(z.string()).default([]),
    related_unmapped_component_ids: z.array(z.string()).default([]),
    related_capability_candidate_component_ids: z.array(z.string()).default([]),
    related_risk_hint_ids: z.array(z.string()).default([]),
    evidence_strength: z.string(),
    uncertainty: z.string().nullable(),
    source: z.string(),
    conflict_fields: z.array(z.record(z.unknown())).default([]),
    not_detected_coverage_gate_passed: z.boolean(),
  })
  .passthrough();

export const profileInferenceResultSchema = z
  .object({
    schema_version: z.literal("profile-signals/v1"),
    source_schema_version: z.literal("ai-system-map/v2"),
    scan_id: z.string(),
    build_id: z.string(),
    environment_id: z.string(),
    generated_from_build_id: z.string(),
    reference_catalog_version: z.string(),
    reference_capability_assessments: z.array(referenceAssessmentSchema).length(52),
    mapping_completeness: mappingCompletenessSchema,
    profiles: z.array(profileFindingSchema).length(15),
    capability_candidate_components: z.array(z.record(z.unknown())).default([]),
  })
  .passthrough()
  .superRefine((value, context) => {
    const scopedRows = [
      ...value.reference_capability_assessments.map((row, index) => ({
        label: "reference_capability_assessments",
        index,
        row,
      })),
      ...value.profiles.map((row, index) => ({ label: "profiles", index, row })),
    ];
    for (const { label, index, row } of scopedRows) {
      for (const identity of ["scan_id", "build_id", "environment_id"] as const) {
        if (row[identity] !== value[identity]) {
          context.addIssue({
            code: z.ZodIssueCode.custom,
            path: [label, index, identity],
            message: `${label}[${index}].${identity} must match profile sidecar ${identity}`,
          });
        }
      }
    }
  });

export type ProfileInferenceResult = z.infer<typeof profileInferenceResultSchema>;
export type ProfileFinding = z.infer<typeof profileFindingSchema>;

/* Mirrors kai_mind.core.models.readiness_report — the backend owns this shape;
   the frontend renders it and degrades when parsing fails. */
const readinessFindingSchema = z
  .object({
    finding_id: z.string(),
    category: z.string(),
    status: assessmentStatusSchema,
    title: z.string(),
    reason: z.string(),
    evidence_ids: z.array(z.string()).default([]),
    recommended_next_checks: z.array(z.string()).default([]),
  })
  .passthrough();

const readinessDimensionSchema = z
  .object({
    dimension_id: z.string(),
    status: assessmentStatusSchema,
    evidence_ids: z.array(z.string()).default([]),
    reason: z.string().nullable().optional(),
  })
  .passthrough();

const groundingReadinessSummarySchema = z
  .object({
    applicability: z.enum(["applicable", "undetermined", "not_applicable"]),
    status: assessmentStatusSchema,
    dimensions: z.array(readinessDimensionSchema).default([]),
    evidence_ids: z.array(z.string()).default([]),
    reason: z.string().nullable().optional(),
  })
  .passthrough();

const capabilityReadinessSummarySchema = z
  .object({
    profile_id: z.string(),
    status: assessmentStatusSchema,
    activation: activationStateSchema,
    evidence_ids: z.array(z.string()).default([]),
  })
  .passthrough();

export const readinessReportSchema = z
  .object({
    schema_version: z.literal("readiness-report/v1"),
    source_schema_version: z.literal("ai-system-map/v2"),
    scan_id: z.string(),
    build_id: z.string(),
    environment_id: z.string(),
    generated_from_build_id: z.string(),
    mapping_completeness: mappingCompletenessSchema,
    grounding: groundingReadinessSummarySchema,
    capability_summaries: z.array(capabilityReadinessSummarySchema).default([]),
    findings: z.array(readinessFindingSchema),
    recommended_next_checks: z.array(z.string()).default([]),
    limitations: z.array(z.string()).default([]),
    primary_map_type: z.string().nullable().optional(),
  })
  .passthrough();

export type ReadinessReport = z.infer<typeof readinessReportSchema>;
export type ReadinessFinding = z.infer<typeof readinessFindingSchema>;

export const phase2ViewerLoadResultSchema = frontendViewerLoadResultSchema
  .extend({
    project_id: z.string(),
    scan_id: z.string(),
    build_id: z.string(),
    environment_id: z.string(),
    generated_from_build_id: z.string(),
    ai_system_map: phase2AiSystemMapSchema,
    profile_inference_result: profileInferenceResultSchema.nullable(),
    readiness_report: readinessReportSchema.nullable(),
    graph_view_model: phase2GraphViewModelSchema,
  })
  .superRefine((value, context) => {
    if (value.generated_from_build_id !== value.build_id) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["generated_from_build_id"],
        message: "generated_from_build_id must equal build_id",
      });
    }

    const scopedArtifacts = [
      ["ai_system_map", value.ai_system_map],
      ["profile_inference_result", value.profile_inference_result],
      ["readiness_report", value.readiness_report],
      ["graph_view_model", value.graph_view_model],
    ] as const;

    for (const [label, artifact] of scopedArtifacts) {
      if (!artifact) continue;
      for (const identity of ["project_id", "scan_id", "build_id", "environment_id"] as const) {
        // The profile/readiness sidecars are build-scoped only; they carry no
        // project_id (kai_mind.core.models.profile_signal / readiness_report).
        if (
          identity === "project_id" &&
          (label === "profile_inference_result" || label === "readiness_report")
        ) {
          continue;
        }
        const artifactIdentity =
          label === "ai_system_map" && identity === "project_id"
            ? value.ai_system_map.project.project_id
            : artifact[identity];
        if (artifactIdentity !== value[identity]) {
          context.addIssue({
            code: z.ZodIssueCode.custom,
            path: [label, identity],
            message: `${label}.${identity} must match ViewerLoadResult.${identity}`,
          });
        }
      }
      if (artifact.generated_from_build_id !== value.build_id) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          path: [label, "generated_from_build_id"],
          message: `${label}.generated_from_build_id must equal build_id`,
        });
      }
    }
  });

/* Mirrors kai_mind.web.schemas.MapBuildScopedResponse: phase2 lineage and
   validated sidecars around the current v1 base graph projection. */
const phase2MapBuildResultSchema = z
  .object({
    status: z.enum(["ok", "error"]),
    project_name: z.string(),
    active_schema_version: z.literal("ai-system-map/v2"),
    requested_schema_version: z.literal("ai-system-map/v2"),
    source_schema_version: z.literal("ai-system-map/v2"),
    operator_rollback_active: z.boolean(),
    migration_warnings: z.array(z.string()).default([]),
    warnings: z.array(z.string()).default([]),
    profile_signals_available: z.boolean(),
    readiness_report_available: z.boolean(),
    profile_inference_result: profileInferenceResultSchema.nullable(),
    readiness_report: readinessReportSchema.nullable(),
  })
  .passthrough();

export const mapBuildScopedResponseSchema = z
  .object({
    project_id: z.string(),
    scan_id: z.string(),
    build_id: z.string(),
    based_on_build_id: z.string().nullable(),
    build_reason: z.enum(["initial_scan", "apply_confirmations", "detail_scan"]),
    applied_mapping_ids: z.array(z.string()).default([]),
    build_result: phase2MapBuildResultSchema,
    viewer_load_result: z
      .object({
        loaded: z.boolean(),
        error_reason: z.string().nullable().optional(),
        map_json: z.string().nullable().optional(),
        ai_system_map: phase2AiSystemMapSchema,
        graph_view_model: phase2BuildGraphViewModelSchema,
      })
      .passthrough(),
  })
  .superRefine((value, context) => {
    const sidecars = [
      ["profile_inference_result", value.build_result.profile_inference_result],
      ["readiness_report", value.build_result.readiness_report],
    ] as const;
    for (const [label, sidecar] of sidecars) {
      if (!sidecar) continue;
      for (const identity of ["scan_id", "build_id"] as const) {
        if (sidecar[identity] !== value[identity]) {
          context.addIssue({
            code: z.ZodIssueCode.custom,
            path: ["build_result", label, identity],
            message: `${label}.${identity} must match build ${identity}`,
          });
        }
      }
      if (sidecar.generated_from_build_id !== value.build_id) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["build_result", label, "generated_from_build_id"],
          message: `${label}.generated_from_build_id must equal build_id`,
        });
      }
    }

    const graph = value.viewer_load_result.graph_view_model;
    for (const identity of ["project_id", "scan_id", "build_id"] as const) {
      const graphIdentity = graph[identity];
      if (graphIdentity != null && graphIdentity !== value[identity]) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["viewer_load_result", "graph_view_model", identity],
          message: `graph_view_model.${identity} must match build ${identity}`,
        });
      }
    }
    if (graph.generated_from_build_id != null && graph.generated_from_build_id !== value.build_id) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["viewer_load_result", "graph_view_model", "generated_from_build_id"],
        message: "graph_view_model.generated_from_build_id must equal build_id",
      });
    }

    const map = value.viewer_load_result.ai_system_map;
    const mapIdentity = {
      project_id: map.project.project_id,
      scan_id: map.scan_id,
      build_id: map.build_id,
    };
    for (const identity of ["project_id", "scan_id", "build_id"] as const) {
      if (mapIdentity[identity] !== value[identity]) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["viewer_load_result", "ai_system_map", identity],
          message: `ai_system_map.${identity} must match build ${identity}`,
        });
      }
    }
    if (map.generated_from_build_id !== value.build_id) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["viewer_load_result", "ai_system_map", "generated_from_build_id"],
        message: "ai_system_map.generated_from_build_id must equal build_id",
      });
    }
  });

/* Mirrors kai_mind.web.schemas.MapBuildHistorySummary / MapBuildHistoryResponse.
   The API returns builds sorted generated_at ASC (lineage order). */
export const mapBuildHistorySummarySchema = z
  .object({
    project_id: z.string(),
    scan_id: z.string(),
    build_id: z.string(),
    based_on_build_id: z.string().nullable(),
    build_reason: z.enum(["initial_scan", "apply_confirmations", "detail_scan"]),
    applied_mapping_ids: z.array(z.string()).default([]),
    generated_at: z.string(),
  })
  .passthrough();

export const mapBuildHistoryResponseSchema = z
  .object({
    project_id: z.string(),
    builds: z.array(mapBuildHistorySummarySchema).default([]),
  })
  .passthrough();

export type MapBuildHistorySummary = z.infer<typeof mapBuildHistorySummarySchema>;

export class ViewerContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ViewerContractError";
  }
}

/* Backend-computed completeness only: the target projection carries it on the
   graph view model; the current build-scoped response carries it inside the
   profile sidecar. Absent in both → undefined, and the UI shows "unavailable"
   rather than a fabricated percentage. */
export function extractMappingCompleteness(payload: ViewerPayload) {
  const graphCompleteness = payload.viewer_load_result.graph_view_model.mapping_completeness;
  if (graphCompleteness) return graphCompleteness;

  const sidecar = payload.viewer_load_result.profile_inference_result;
  if (!sidecar) return undefined;
  const parsed = mappingCompletenessSchema.safeParse(
    (sidecar as Record<string, unknown>).mapping_completeness,
  );
  return parsed.success ? parsed.data : undefined;
}

export function parseMapBuildPayload(raw: unknown): ViewerPayload {
  const parsed = mapBuildScopedResponseSchema.safeParse(raw);
  if (!parsed.success) {
    const issue = parsed.error.issues[0];
    throw new ViewerContractError(
      `Unsupported map build payload. ${issue?.path.join(".") ?? ""}: ${issue?.message ?? "invalid"}`,
    );
  }

  const build = parsed.data;
  const buildResult = build.build_result;
  const environmentId =
    build.viewer_load_result.graph_view_model.environment_id ??
    buildResult.profile_inference_result?.environment_id ??
    buildResult.readiness_report?.environment_id ??
    null;

  return viewerPayloadSchema.parse({
    contract_source: "phase2-build",
    viewer_load_result: {
      loaded: build.viewer_load_result.loaded && buildResult.status === "ok",
      error_reason: build.viewer_load_result.error_reason ?? null,
      warnings: [...buildResult.warnings, ...buildResult.migration_warnings],
      project_id: build.project_id,
      scan_id: build.scan_id,
      build_id: build.build_id,
      environment_id: environmentId,
      generated_from_build_id: build.build_id,
      based_on_build_id: build.based_on_build_id,
      applied_mapping_ids: build.applied_mapping_ids,
      // Current build-scoped responses publish no artifact refs (Plan 06).
      artifact_refs: [],
      map_json: build.viewer_load_result.map_json ?? null,
      ai_system_map: build.viewer_load_result.ai_system_map,
      profile_inference_result: buildResult.profile_inference_result,
      readiness_report: buildResult.readiness_report,
      graph_view_model: build.viewer_load_result.graph_view_model,
    },
  });
}

function legacyProjectId(aiSystemMap: Record<string, unknown>): string | null {
  if (typeof aiSystemMap.project_id === "string") return aiSystemMap.project_id;
  if (!aiSystemMap.project || typeof aiSystemMap.project !== "object") return null;

  const project = aiSystemMap.project as Record<string, unknown>;
  const projectId = project.project_id ?? project.id;
  return typeof projectId === "string" ? projectId : null;
}

export function parseViewerPayload(raw: unknown): ViewerPayload {
  const phase2 = phase2ViewerLoadResultSchema.safeParse(raw);
  if (phase2.success) {
    return viewerPayloadSchema.parse({
      contract_source: "phase2",
      viewer_load_result: phase2.data,
    });
  }

  const legacy = legacyViewerPayloadSchema.safeParse(raw);
  if (legacy.success) {
    const loadResult = legacy.data.viewer_load_result;
    const graph = loadResult.graph_view_model;
    const hasReferenceProjection = graph.reference_map_version != null;
    return viewerPayloadSchema.parse({
      ...legacy.data,
      contract_source: hasReferenceProjection ? "phase2" : "legacy-v1",
      viewer_load_result: {
        ...loadResult,
        warnings: [],
        project_id: graph.project_id ?? legacyProjectId(loadResult.ai_system_map),
        scan_id: graph.scan_id ?? null,
        build_id: graph.build_id ?? null,
        environment_id: graph.environment_id ?? null,
        generated_from_build_id: graph.generated_from_build_id ?? null,
        based_on_build_id: null,
        applied_mapping_ids: [],
        artifact_refs: [],
        profile_inference_result: null,
        readiness_report: null,
      },
    });
  }

  const phase2Issue = phase2.error.issues[0];
  const legacyIssue = legacy.error.issues[0];
  throw new ViewerContractError(
    `Unsupported viewer payload. Phase2: ${phase2Issue?.message ?? "invalid"}; legacy: ${legacyIssue?.message ?? "invalid"}`,
  );
}
