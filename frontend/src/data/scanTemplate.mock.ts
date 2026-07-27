/* ============================================================================
   Mock data for the Scan Template page + Mapping Proposal modal.
   Shapes mirror the backend contract in docs/API-GUIDE.md and src/types.ts so
   the same components can later be fed real /api responses unchanged.

   NOTE: the Scan-Template / project-custom-version selection API does NOT exist
   yet. Everything here is served behind the service seam in
   services/scanTemplateApi.ts. The Mapping Proposal shapes DO map to the real
   /api/mapping-proposals contract.
   ========================================================================== */
import type {
  ConfirmedMappingRow,
  MappingProposal,
  PendingProposalRow,
  ScanProfile,
  SkippedDecisionRow,
} from "../types";

export const PROJECT = {
  project_id: "project:sample-health-rag",
  project_name: "sample-health-rag",
};

// -- Scan templates / mapping profiles (MOCK) -----------------------------
export const SYSTEM_DEFAULT: ScanProfile = {
  profile_id: "profile:rag-core-v1",
  kind: "system_default",
  name: "System default",
  version_label: "rag-core-v1",
  read_only: true,
  description: "Built-in RAG mapping template used as the baseline.",
  core_components: [
    { slot: "api_or_orchestrator", label: "API / Orchestrator" },
    { slot: "retriever", label: "Retriever" },
    { slot: "vector_store", label: "Vector Store" },
    { slot: "prompt_builder", label: "Prompt Builder" },
    { slot: "llm", label: "LLM" },
  ],
};

// Set PROJECT_CUSTOM to null to exercise the empty-state branch.
export const PROJECT_CUSTOM: ScanProfile = {
  profile_id: "profile:project-custom-v1",
  kind: "project_custom",
  name: "Project custom version",
  version_label: "project-custom-v1",
  derived_from: "rag-core-v1",
  read_only: false,
  description:
    "Uses confirmed mappings from this project while keeping the system default unchanged.",
  core_components: [],
  stats: { confirmed: 8, pending: 3, skipped: 2 },
};

// Which profile the NEXT scan will use.
export const SELECTED_PROFILE_ID = "profile:project-custom-v1";

// -- Mapping status lists -------------------------------------------------
export const CONFIRMED: ConfirmedMappingRow[] = [
  {
    mapping_id: "mapping:retriever-1",
    node_path: "src/rag/retriever.py",
    node_kind: "python_module",
    target_slot: "retriever",
    target_label: "Retriever",
    source: "ai_suggested",
    evidence: [
      { evidence_id: "evidence:retriever-call", file: "src/rag/retriever.py", symbol: "embed_query()", line: 42 },
      { evidence_id: "evidence:retriever-store", file: "src/rag/retriever.py", symbol: "search()", line: 67 },
    ],
    updated_at: "2026-06-08T09:12:00Z",
  },
  {
    mapping_id: "mapping:qdrant-1",
    node_path: "src/vector/qdrant_store.py",
    node_kind: "python_module",
    target_slot: "vector_store",
    target_label: "Vector Store",
    source: "user_confirmed",
    evidence: [
      { evidence_id: "evidence:qdrant-client", file: "src/vector/qdrant_store.py", symbol: "QdrantClient", line: 11 },
      { evidence_id: "evidence:qdrant-upsert", file: "src/vector/qdrant_store.py", symbol: "upsert()", line: 58 },
    ],
    updated_at: "2026-06-08T09:20:00Z",
  },
  {
    mapping_id: "mapping:routes-1",
    node_path: "src/api/routes.py",
    node_kind: "python_module",
    target_slot: "api_or_orchestrator",
    target_label: "API / Orchestrator",
    source: "fallback_rule",
    evidence: [
      { evidence_id: "evidence:routes-app", file: "src/api/routes.py", symbol: "create_app()", line: 9 },
    ],
    updated_at: "2026-06-08T08:55:00Z",
  },
];

export const PENDING: PendingProposalRow[] = [
  {
    unmapped_id: "unmapped:user-profile",
    node_path: "src/components/UserProfile.jsx",
    node_kind: "react_component",
    candidate_count: 3,
    best_candidate: "UserAccountView",
    evidence_count: 2,
  },
  {
    unmapped_id: "unmapped:rerank",
    node_path: "src/rag/rerank.py",
    node_kind: "python_module",
    candidate_count: 2,
    best_candidate: "Reranker",
    evidence_count: 1,
  },
];

export const SKIPPED: SkippedDecisionRow[] = [
  {
    decision_id: "skip:redis",
    node_path: "src/cache/redis_cache.py",
    node_kind: "python_module",
    reason: "Not enough evidence",
    skipped_at: "2026-06-07T16:40:00Z",
  },
  {
    decision_id: "skip:guardrails",
    node_path: "src/utils/guardrails.py",
    node_kind: "python_module",
    reason: "Needs backend confirmation",
    skipped_at: "2026-06-07T17:02:00Z",
  },
];

// -- Mapping proposal (REAL contract shape: MappingProposal) --------------
// Keyed by source_unmapped_id so a node click can fetch its proposal.
export const PROPOSALS: Record<string, MappingProposal> = {
  "unmapped:user-profile": {
    proposal_id: "proposal:user-profile",
    project_id: PROJECT.project_id,
    source_unmapped_id: "unmapped:user-profile",
    source_path: "src/components/UserProfile.jsx",
    status: "pending_user_confirmation",
    evidence_packet: {
      project_id: PROJECT.project_id,
      source_unmapped_id: "unmapped:user-profile",
      source_file: "src/components/UserProfile.jsx",
      observed_kind: "react_view",
      reason: "The scanner found component evidence without a canonical target.",
      evidence_ids: [
        "evidence:import:account-store",
        "evidence:jsx:profile-fields",
        "evidence:jsx:form-fields",
        "evidence:path:components-dir",
      ],
      rule_ids: [],
      line_ranges: ["8", "31", "44"],
      masked_evidence_values: [],
      masked_snippets: [],
      available_slots: [],
      context_limits: {},
    },
    provider_name: "nvidia-nim",
    provider_error_reason: null,
    user_description: null,
    candidates: [
      {
        candidate_id: "candidate:1",
        candidate_type: "non_baseline_capability_candidate",
        recommendation_level: "recommended",
        source: "ai_suggested",
        target_slot: null,
        component_name: null,
        component_kind: null,
        provider: "nvidia-nim",
        proposed_capability_candidate_id: "capability-candidate:user-profile",
        proposed_capability_candidate_name: "User Profile",
        proposed_capability_candidate_kind: "react_view",
        label: "Review as a non-map capability signal",
        rationale:
          "The file shows a user-facing capability signal, but the sample does not claim it belongs to canonical map topology.",
        evidence_ids: ["evidence:import:account-store", "evidence:jsx:profile-fields"],
        evidence_refs: [
          {
            evidence_id: "evidence:import:account-store",
            file: "src/components/UserProfile.jsx",
            symbol: "useAccountStore()",
            line: 8,
          },
          {
            evidence_id: "evidence:jsx:profile-fields",
            file: "src/components/UserProfile.jsx",
            symbol: "<ProfileFields/>",
            line: 31,
          },
        ],
        uncertainty_reason: null,
      },
      {
        candidate_id: "candidate:2",
        candidate_type: "needs_more_information",
        recommendation_level: "alternative",
        source: "ai_suggested",
        target_slot: null,
        component_name: null,
        component_kind: null,
        provider: "nvidia-nim",
        label: "Needs more information",
        rationale:
          "Contains editable form fields and a save handler, which overlap with the settings surface, but lacks settings-specific routes.",
        evidence_ids: ["evidence:jsx:form-fields"],
        evidence_refs: [
          {
            evidence_id: "evidence:jsx:form-fields",
            file: "src/components/UserProfile.jsx",
            symbol: "handleSave()",
            line: 44,
          },
        ],
        uncertainty_reason: "Overlaps with two UI slots; form fields alone are not decisive.",
      },
      {
        candidate_id: "candidate:3",
        candidate_type: "skip_for_now",
        recommendation_level: "fallback",
        source: "fallback_rule",
        target_slot: null,
        component_name: null,
        component_kind: null,
        provider: "deterministic",
        proposed_capability_candidate_id: null,
        proposed_capability_candidate_name: null,
        proposed_capability_candidate_kind: null,
        label: "Skip for now",
        rationale:
          "Leave this sample evidence unresolved and keep the unknown component visible.",
        evidence_ids: ["evidence:path:components-dir"],
        evidence_refs: [
          {
            evidence_id: "evidence:path:components-dir",
            file: "src/components/UserProfile.jsx",
            label: "lives under src/components/ — no matching slot",
          },
        ],
        uncertainty_reason: "Created by rule, not from a code-interaction match.",
      },
    ],
    available_actions: ["accept", "edit", "reject", "skip_for_now"],
    created_at: "2026-06-08T09:30:00Z",
    updated_at: "2026-06-08T09:30:00Z",
  },
};
