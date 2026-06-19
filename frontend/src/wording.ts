import { createContext, createElement, useContext, type ReactNode } from "react";

/* ============================================================================
   Wording drafts for the Scan Template + Mapping Proposal surfaces.

   These are product-copy drafts, not final feature modes:
     A `direct`  - shortest task-first wording.
     B `guided`  - adds one light hint where a concept first appears.
     C `precise` - keeps product terms, but avoids internal ids in primary UI.
   Once a direction is chosen, delete the unused sets and the header toggle.
   ========================================================================== */
export type WordingMode = "direct" | "guided" | "precise";

export interface Wording {
  pageSubtitle: string;
  tabSystem: string;
  tabCustom: string;
  galleryOpen: string;
  systemName: string;
  systemDesc: string;
  customName: string;
  customDesc: string;
  readOnlyBadge: string;
  derivedBadge: string;
  derivedShort: string;
  nextScanWillUse: string;
  localAiTitle: string;
  localAiBody: string;
  baselineHead: string;
  baselineNote: string;
  useForNextScan: string;
  inUse: string;
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
  noCustomTitle: string;
  noCustomBody: string;
  reviewUnmapped: string;
  buildDesc: string;
  modalTitle: string;
  unmappedTag: string;
  unmappedNodeLabel: string;
  candidateWord: string;
  recommendedLabel: string;
  basedOnEvidence: string;
  otherSuggestions: (n: number) => string;
  skipThisNode: string;
  verdictPre: string;
  verdictPost: string;
  whyLabel: string;
  acceptBtn: string;
  editBtn: string;
  rejectBtn: string;
  lookingForSuggestions: string;
  suggestionsUnavailable: string;
  fallbackSuggestions: string;
  noSuggestionsFound: string;
  noSuggestionSummary: string;
  suggestionsFoundSummary: (n: number) => string;
  sourceAi: string;
  sourceRule: string;
  sourceUser: string;
  sourceDeterministic: string;
}

export const COPY_DIRECT: Wording = {
  pageSubtitle: "Choose the setup for the next project scan.",
  tabSystem: "Built-in setup",
  tabCustom: "Project setup",
  galleryOpen: "Open",
  systemName: "Built-in setup",
  systemDesc: "The default setup Kai-Mind starts from.",
  customName: "Project setup",
  customDesc: "Your confirmed matches for this project. The built-in setup stays unchanged.",
  readOnlyBadge: "Read-only",
  derivedBadge: "Project-only",
  derivedShort: "project-only",
  nextScanWillUse: "Next scan will use",
  localAiTitle: "Local AI setup",
  localAiBody: "Pick how Kai-Mind names files it finds in this project. Confirmed matches are saved here only.",
  baselineHead: "Default parts",
  baselineNote: "The main AI system parts Kai-Mind looks for.",
  useForNextScan: "Use this next",
  inUse: "In use",
  statusHead: "Matches",
  statusNote: "Confirmed files, files to review, and items left for later.",
  tabConfirmed: "Confirmed",
  tabPending: "To review",
  tabSkipped: "Skipped",
  colDetectedNode: "File we found",
  colMappedTo: "Matched to",
  colSource: "How we matched it",
  colEvidence: "Evidence",
  colCandidates: "Suggestions",
  colBestCandidate: "Suggested match",
  reviewProposal: "Review",
  noCustomTitle: "No project setup yet",
  noCustomBody: "Review files Kai-Mind could not place. Your confirmed matches will become this project's setup.",
  reviewUnmapped: "Review files",
  buildDesc: "Review the files below. Confirmed matches will become this project's setup.",
  modalTitle: "Review suggestions",
  unmappedTag: "Needs review",
  unmappedNodeLabel: "File to review",
  candidateWord: "Suggestion",
  recommendedLabel: "Suggested first",
  basedOnEvidence: "Evidence",
  otherSuggestions: (n) => `Other suggestions (${n})`,
  skipThisNode: "Decide later",
  verdictPre: "This file looks like",
  verdictPost: ".",
  whyLabel: "Why",
  acceptBtn: "Use this",
  editBtn: "Edit",
  rejectBtn: "Not this",
  lookingForSuggestions: "Looking for suggestions...",
  suggestionsUnavailable: "Suggestions are unavailable right now.",
  fallbackSuggestions: "Showing rule-based suggestions instead.",
  noSuggestionsFound: "No suggestions found.",
  noSuggestionSummary: "Kai-Mind does not have a suggestion for this file yet.",
  suggestionsFoundSummary: (n) =>
    `Kai-Mind found ${n} suggestion${n === 1 ? "" : "s"} for this file. Review the first one, then choose what to do.`,
  sourceAi: "Suggested",
  sourceRule: "Rule suggestion",
  sourceUser: "You confirmed it",
  sourceDeterministic: "Rule suggestion",
};

export const COPY_GUIDED: Wording = {
  pageSubtitle: "Choose which setup Kai-Mind uses the next time it scans this project.",
  tabSystem: "Built-in setup",
  tabCustom: "Project setup",
  galleryOpen: "Open",
  systemName: "Built-in setup",
  systemDesc: "The default template Kai-Mind uses to recognize common AI system parts.",
  customName: "Project setup",
  customDesc: "A saved version for this project, made from the matches you confirm.",
  readOnlyBadge: "Read-only",
  derivedBadge: "Based on built-in",
  derivedShort: "based on built-in",
  nextScanWillUse: "Next scan will use",
  localAiTitle: "What this setup controls",
  localAiBody:
    "A setup tells Kai-Mind how to name detected files. The built-in setup is the default; the project setup keeps your confirmed matches.",
  baselineHead: "Parts Kai-Mind looks for",
  baselineNote: "These are the common pieces of a local AI or RAG project.",
  useForNextScan: "Use for next scan",
  inUse: "In use",
  statusHead: "Mapping progress",
  statusNote: "Matches you confirmed, suggestions that need review, and files parked for later.",
  tabConfirmed: "Confirmed",
  tabPending: "To review",
  tabSkipped: "Skipped",
  colDetectedNode: "File we found",
  colMappedTo: "Matched to",
  colSource: "How we matched it",
  colEvidence: "Evidence",
  colCandidates: "Suggestions",
  colBestCandidate: "Suggested match",
  reviewProposal: "Review",
  noCustomTitle: "No project setup yet",
  noCustomBody:
    "Start by reviewing files Kai-Mind could not place. Confirmed matches will be saved as this project's setup.",
  reviewUnmapped: "Review files to place",
  buildDesc: "Review the files below and save the matches that fit this project.",
  modalTitle: "Review suggested matches",
  unmappedTag: "Needs review",
  unmappedNodeLabel: "File Kai-Mind could not place",
  candidateWord: "Suggestion",
  recommendedLabel: "Suggested first",
  basedOnEvidence: "Evidence",
  otherSuggestions: (n) => `Other suggestions (${n})`,
  skipThisNode: "Decide later",
  verdictPre: "This file may be",
  verdictPost: ".",
  whyLabel: "Why this is suggested",
  acceptBtn: "Use this match",
  editBtn: "Edit",
  rejectBtn: "Not this",
  lookingForSuggestions: "Looking for suggestions...",
  suggestionsUnavailable: "Kai-Mind could not load suggestions right now.",
  fallbackSuggestions: "The AI suggestion service timed out, so Kai-Mind is showing rule-based suggestions.",
  noSuggestionsFound: "No suggestions found.",
  noSuggestionSummary: "Kai-Mind needs more evidence before it can suggest a match for this file.",
  suggestionsFoundSummary: (n) =>
    `Kai-Mind found ${n} suggestion${n === 1 ? "" : "s"} for this file. Review the first suggestion, then use it, edit it, reject it, or decide later.`,
  sourceAi: "Suggested",
  sourceRule: "Rule suggestion",
  sourceUser: "You confirmed it",
  sourceDeterministic: "Rule suggestion",
};

export const COPY_PRECISE: Wording = {
  pageSubtitle: "Choose the scan template Kai-Mind applies to this project.",
  tabSystem: "Built-in template",
  tabCustom: "Project template",
  galleryOpen: "Open",
  systemName: "Built-in template",
  systemDesc: "The read-only template Kai-Mind uses as the starting point for scans.",
  customName: "Project template",
  customDesc: "Your project-specific template, built from confirmed matches. The built-in template is not changed.",
  readOnlyBadge: "Read-only",
  derivedBadge: "Based on built-in",
  derivedShort: "based on built-in",
  nextScanWillUse: "Next scan will use",
  localAiTitle: "Scan template",
  localAiBody:
    "A scan template maps detected files to named AI system parts. Use the project template when you want future scans to remember your confirmed matches.",
  baselineHead: "Template parts",
  baselineNote: "The core AI system parts this template can map files to.",
  useForNextScan: "Use for next scan",
  inUse: "In use",
  statusHead: "Template mapping status",
  statusNote: "Confirmed mappings update the project template. Suggestions stay pending until you review them.",
  tabConfirmed: "Confirmed mappings",
  tabPending: "Pending review",
  tabSkipped: "Skipped",
  colDetectedNode: "Detected file",
  colMappedTo: "Mapped to",
  colSource: "How we matched it",
  colEvidence: "Evidence",
  colCandidates: "Suggestions",
  colBestCandidate: "Suggested mapping",
  reviewProposal: "Review",
  noCustomTitle: "No project template yet",
  noCustomBody:
    "Review pending files to create a project template. The built-in template remains read-only.",
  reviewUnmapped: "Review pending files",
  buildDesc: "Review pending files and confirm the mappings that should be saved to this project template.",
  modalTitle: "Review mapping suggestions",
  unmappedTag: "Pending review",
  unmappedNodeLabel: "Detected file",
  candidateWord: "Suggestion",
  recommendedLabel: "Suggested first",
  basedOnEvidence: "Evidence",
  otherSuggestions: (n) => `Other suggestions (${n})`,
  skipThisNode: "Decide later",
  verdictPre: "Suggested mapping:",
  verdictPost: "",
  whyLabel: "Reason",
  acceptBtn: "Confirm",
  editBtn: "Edit",
  rejectBtn: "Reject",
  lookingForSuggestions: "Looking for mapping suggestions...",
  suggestionsUnavailable: "Mapping suggestions are unavailable right now.",
  fallbackSuggestions: "AI suggestions timed out. Showing rule-based mapping suggestions.",
  noSuggestionsFound: "No mapping suggestions found.",
  noSuggestionSummary: "There is not enough evidence to suggest a mapping for this file yet.",
  suggestionsFoundSummary: (n) =>
    `Kai-Mind found ${n} mapping suggestion${n === 1 ? "" : "s"} for this file. Review the first suggestion, then confirm, edit, reject, or decide later.`,
  sourceAi: "Suggested",
  sourceRule: "Rule suggestion",
  sourceUser: "User confirmed",
  sourceDeterministic: "Rule suggestion",
};

const WordingContext = createContext<Wording>(COPY_DIRECT);

export function WordingProvider({ mode, children }: { mode: WordingMode; children: ReactNode }) {
  const copy = mode === "guided" ? COPY_GUIDED : mode === "precise" ? COPY_PRECISE : COPY_DIRECT;
  return createElement(WordingContext.Provider, { value: copy }, children);
}

export function useWording(): Wording {
  return useContext(WordingContext);
}
