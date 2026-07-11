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
    status: assessmentStatusSchema,
    activation: activationStateSchema,
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
    evidence_ids: z.array(z.string()),
  })
  .passthrough();

const profileInferenceResultSchema = z
  .object({
    schema_version: z.literal("profile-signals/v1"),
    source_schema_version: z.literal("ai-system-map/v2"),
    project_id: z.string(),
    scan_id: z.string(),
    build_id: z.string(),
    environment_id: z.string(),
    generated_from_build_id: z.string(),
    reference_map_version: z.string(),
    reference_capability_assessments: z.array(referenceAssessmentSchema).length(52),
    mapping_completeness: mappingCompletenessSchema,
    profiles: z.array(profileFindingSchema).length(15),
    capability_candidate_components: z.array(z.record(z.unknown())).default([]),
  })
  .passthrough();

const readinessReportSchema = z
  .object({
    schema_version: z.literal("readiness-report/v1"),
    source_schema_version: z.literal("ai-system-map/v2"),
    project_id: z.string(),
    scan_id: z.string(),
    build_id: z.string(),
    environment_id: z.string(),
    generated_from_build_id: z.string(),
    finding_registry_version: z.string(),
    release_verdict: z.enum(["ready", "needs_review", "blocked"]),
    summary: z
      .object({
        status: assessmentStatusSchema,
        runtime_verified: z.literal(false),
      })
      .passthrough(),
    findings: z.array(
      z
        .object({
          finding_id: z.string(),
          category: z.string(),
          severity: z.string(),
          status: assessmentStatusSchema,
          evidence_ids: z.array(z.string()),
          limitations: z.array(z.string()).default([]),
        })
        .passthrough(),
    ),
  })
  .passthrough();

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

export class ViewerContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ViewerContractError";
  }
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
    return viewerPayloadSchema.parse({
      ...legacy.data,
      contract_source: "legacy-v1",
      viewer_load_result: {
        ...loadResult,
        warnings: [],
        project_id: legacyProjectId(loadResult.ai_system_map),
        scan_id: null,
        build_id: null,
        environment_id: null,
        generated_from_build_id: null,
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
