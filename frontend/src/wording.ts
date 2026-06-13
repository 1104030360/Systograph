import { createContext, createElement, useContext, type ReactNode } from "react";

/* ============================================================================
   Wording layer for the Scan Template + Mapping Proposal surfaces.

   TEMPORARY: three parallel copy sets so the team can compare in-product and
   pick one.
     A `explained` — keeps domain terms, adds a plain gloss, demotes codes.
     B `casual`    — fully plain display names.
     C `hybrid`    — plain names (B) + a one-line gloss that introduces the term.
   Once a direction is chosen, delete the unused sets and the header toggle.
   ========================================================================== */
export type WordingMode = "explained" | "casual" | "hybrid";

export interface Wording {
  // gallery + page
  pageSubtitle: string;
  tabSystem: string;
  tabCustom: string;
  galleryOpen: string;
  // template identity
  systemName: string;
  systemDesc: string;
  customName: string;
  customDesc: string;
  readOnlyBadge: string;
  derivedBadge: string;
  derivedShort: string;
  // summary bar
  nextScanWillUse: string;
  localAiTitle: string;
  localAiBody: string;
  // system detail
  baselineHead: string;
  baselineNote: string;
  // actions
  useForNextScan: string;
  inUse: string;
  // mapping status
  statusHead: string;
  statusNote: string;
  tabConfirmed: string;
  tabPending: string;
  tabSkipped: string;
  colDetectedNode: string;
  colMappedTo: string;
  colSource: string;
  colEvidence: string;
  colCandidates: string;
  colBestCandidate: string;
  reviewProposal: string;
  // empty / build
  noCustomTitle: string;
  noCustomBody: string;
  reviewUnmapped: string;
  buildDesc: string;
  // proposal modal
  modalTitle: string;
  unmappedTag: string;
  unmappedNodeLabel: string;
  candidateWord: string;
  recommendedLabel: string;
  basedOnEvidence: string;
  otherSuggestions: (n: number) => string;
  skipThisNode: string;
  // candidate card (plain-sentence verdict)
  verdictPre: string; // text before the bold component name
  verdictPost: string; // text after the component name (e.g. ".")
  whyLabel: string;
  acceptBtn: string;
  editBtn: string;
  rejectBtn: string;
  // source provenance labels
  sourceAi: string;
  sourceRule: string;
  sourceUser: string;
  sourceDeterministic: string;
}

export const COPY_EXPLAINED: Wording = {
  pageSubtitle: "Choose how Kai-Mind maps detected components during the next scan.",
  tabSystem: "System default",
  tabCustom: "Project custom version",
  galleryOpen: "Open",
  systemName: "System default",
  systemDesc: "Built-in RAG mapping template used as the starting point for every scan.",
  customName: "Project custom version",
  customDesc:
    "This project's own version: it starts from the system default and adds the matches you've confirmed. The system default itself never changes.",
  readOnlyBadge: "Read-only",
  derivedBadge: "Derived from rag-core-v1",
  derivedShort: "from rag-core-v1",
  nextScanWillUse: "Next scan will use",
  localAiTitle: "Local AI setup",
  localAiBody:
    "Kai-Mind scans your project on this machine and uses this template to name what it finds. A project setup is the saved set of matches you have confirmed.",
  baselineHead: "Baseline components",
  baselineNote: "The core RAG slots every scan starts from.",
  useForNextScan: "Use for next scan",
  inUse: "In use",
  statusHead: "Mapping status",
  statusNote: "Decisions that shape the project custom version.",
  tabConfirmed: "Confirmed mappings",
  tabPending: "Pending proposals",
  tabSkipped: "Skipped decisions",
  colDetectedNode: "Detected node",
  colMappedTo: "Mapped to",
  colSource: "How we matched it",
  colEvidence: "Based on evidence",
  colCandidates: "Candidates",
  colBestCandidate: "Suggested match",
  reviewProposal: "Review proposal",
  noCustomTitle: "No project custom version yet",
  noCustomBody:
    "Confirm the unmapped nodes in this project and Kai-Mind will derive a custom version from rag-core-v1. The baseline stays read-only.",
  reviewUnmapped: "Review unmapped nodes",
  buildDesc: "Confirm the unmapped nodes below and Kai-Mind will derive a custom version from rag-core-v1.",
  modalTitle: "Review suggestions",
  unmappedTag: "Needs review",
  unmappedNodeLabel: "File to review",
  candidateWord: "Suggestion",
  recommendedLabel: "Suggested first",
  basedOnEvidence: "Based on evidence",
  otherSuggestions: (n) => `Other candidates (${n})`,
  skipThisNode: "Skip this node",
  verdictPre: "Best fit:",
  verdictPost: "",
  whyLabel: "Why we think so",
  acceptBtn: "Accept",
  editBtn: "Edit",
  rejectBtn: "Reject",
  sourceAi: "AI suggested",
  sourceRule: "Fallback rule",
  sourceUser: "User confirmed",
  sourceDeterministic: "Deterministic",
};

export const COPY_CASUAL: Wording = {
  pageSubtitle: "Pick which setup Kai-Mind uses the next time it scans your project.",
  tabSystem: "Built-in setup",
  tabCustom: "Your project's setup",
  galleryOpen: "Open",
  systemName: "Built-in setup",
  systemDesc: "The ready-made starting point Kai-Mind uses out of the box.",
  customName: "Your project's setup",
  customDesc:
    "A setup just for this project: the built-in one, plus the matches you've confirmed. The built-in setup stays untouched.",
  readOnlyBadge: "Can't edit",
  derivedBadge: "Based on the built-in setup",
  derivedShort: "based on built-in",
  nextScanWillUse: "Next scan will use",
  localAiTitle: "Local AI setup",
  localAiBody:
    "Kai-Mind scans this project locally. This setup tells it how to name files it finds, and your confirmed matches become this project's setup.",
  baselineHead: "What every scan looks for",
  baselineNote: "The main parts Kai-Mind tries to find in your code.",
  useForNextScan: "Use this next time",
  inUse: "In use",
  statusHead: "Matches",
  statusNote: "What's been sorted out, and what still needs you.",
  tabConfirmed: "Confirmed",
  tabPending: "To review",
  tabSkipped: "Skipped",
  colDetectedNode: "File we found",
  colMappedTo: "Matched to",
  colSource: "How we matched it",
  colEvidence: "What we found",
  colCandidates: "Suggestions",
  colBestCandidate: "Suggested match",
  reviewProposal: "Review",
  noCustomTitle: "You don't have a setup for this project yet",
  noCustomBody:
    "Review the files Kai-Mind couldn't place, and it'll build a setup just for this project from the built-in one. The built-in setup stays untouched.",
  reviewUnmapped: "Review unplaced files",
  buildDesc: "Sort out the files below, and Kai-Mind will build a setup just for this project from the built-in one.",
  modalTitle: "Review suggestions",
  unmappedTag: "Not sure yet",
  unmappedNodeLabel: "File we're not sure about",
  candidateWord: "Suggestion",
  recommendedLabel: "Suggested first",
  basedOnEvidence: "Why we think so",
  otherSuggestions: (n) => `Other suggestions (${n})`,
  skipThisNode: "Decide later",
  verdictPre: "This file looks like your",
  verdictPost: ".",
  whyLabel: "Why",
  acceptBtn: "Use this",
  editBtn: "Edit",
  rejectBtn: "Not this",
  sourceAi: "Suggested",
  sourceRule: "Rule suggestion",
  sourceUser: "You confirmed it",
  sourceDeterministic: "Rule suggestion",
};

/* C · mix — plain display names (from B), but each key concept is followed by a
   one-line gloss that introduces the underlying term, so users learn the
   vocabulary while they work. Best of both: friendly first, precise second. */
export const COPY_HYBRID: Wording = {
  pageSubtitle: "Pick which setup Kai-Mind uses the next time it scans your project.",
  tabSystem: "Built-in setup",
  tabCustom: "Your project's setup",
  galleryOpen: "Open",
  systemName: "Built-in setup",
  systemDesc: "The ready-made starting point Kai-Mind uses out of the box — the built-in template (rag-core-v1).",
  customName: "Your project's setup",
  customDesc:
    "A setup just for this project: the built-in one, plus the matches you've confirmed. It's a separate version (project-custom-v1), so the built-in setup never changes.",
  readOnlyBadge: "Read-only",
  derivedBadge: "Based on the built-in setup",
  derivedShort: "based on built-in",
  nextScanWillUse: "Next scan will use",
  localAiTitle: "Local AI setup",
  localAiBody:
    "Kai-Mind scans this project locally. This setup is the template that turns detected files into named parts of your AI system.",
  baselineHead: "What every scan looks for",
  baselineNote: "The main parts Kai-Mind tries to find — the core RAG slots.",
  useForNextScan: "Use this next time",
  inUse: "In use",
  statusHead: "Matches",
  statusNote: "What's been sorted out, and what still needs you.",
  tabConfirmed: "Confirmed",
  tabPending: "To review",
  tabSkipped: "Skipped",
  colDetectedNode: "File we found",
  colMappedTo: "Matched to",
  colSource: "How we matched it",
  colEvidence: "What we found",
  colCandidates: "Suggestions",
  colBestCandidate: "Suggested match",
  reviewProposal: "Review",
  noCustomTitle: "You don't have a setup for this project yet",
  noCustomBody:
    "Review the files Kai-Mind couldn't place, and it'll build a setup just for this project from the built-in one (a new version derived from rag-core-v1). The built-in setup stays untouched.",
  reviewUnmapped: "Review unplaced files",
  buildDesc:
    "Sort out the files below, and Kai-Mind will build a setup just for this project: a new version derived from the built-in one.",
  modalTitle: "Review suggestions",
  unmappedTag: "Not sure yet",
  unmappedNodeLabel: "File we're not sure about",
  candidateWord: "Suggestion",
  recommendedLabel: "Suggested first",
  basedOnEvidence: "Why we think so",
  otherSuggestions: (n) => `Other suggestions (${n})`,
  skipThisNode: "Decide later",
  verdictPre: "This file looks like your",
  verdictPost: ".",
  whyLabel: "Why",
  acceptBtn: "Use this",
  editBtn: "Edit",
  rejectBtn: "Not this",
  sourceAi: "Suggested",
  sourceRule: "Rule suggestion",
  sourceUser: "You confirmed it",
  sourceDeterministic: "Rule suggestion",
};

const WordingContext = createContext<Wording>(COPY_EXPLAINED);

export function WordingProvider({ mode, children }: { mode: WordingMode; children: ReactNode }) {
  const copy = mode === "casual" ? COPY_CASUAL : mode === "hybrid" ? COPY_HYBRID : COPY_EXPLAINED;
  return createElement(WordingContext.Provider, { value: copy }, children);
}

export function useWording(): Wording {
  return useContext(WordingContext);
}
