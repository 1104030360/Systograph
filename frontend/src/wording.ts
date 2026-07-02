import { createContext, createElement, useContext, type ReactNode } from "react";

export interface Wording {
  pageSubtitle: string;
  sampleBadge: string;
  sampleBadgeHint: string;
  newScanUnavailable: string;
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
  sourceAi: string;
  sourceRule: string;
  sourceUser: string;
  sourceDeterministic: string;
}

export const COPY: Wording = {
  pageSubtitle: "Choose the scan template Kai-Mind uses the next time it scans this project.",
  sampleBadge: "Sample data",
  sampleBadgeHint: "This page shows example mappings. It is not connected to your project yet.",
  newScanUnavailable: "New scan is not available from this page yet. Use Start scan in the viewer toolbar.",
  tabSystem: "Built-in template",
  tabCustom: "Project template",
  galleryOpen: "Open",
  systemName: "Built-in template",
  systemDesc: "The default template Kai-Mind uses to recognize common AI system parts.",
  customName: "Project template",
  customDesc: "A saved template for this project, made from the matches you confirm.",
  readOnlyBadge: "Read-only",
  derivedBadge: "Based on built-in",
  derivedShort: "based on built-in",
  nextScanWillUse: "Next scan will use",
  localAiTitle: "Scan template",
  localAiBody:
    "A scan template tells Kai-Mind how to name detected files. The project template keeps confirmed matches for future scans.",
  baselineHead: "Template parts",
  baselineNote: "These are the common pieces of a local AI or RAG project.",
  useForNextScan: "Use for next scan",
  inUse: "In use",
  statusHead: "Mapping progress",
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
  noCustomBody: "Start by reviewing files Kai-Mind could not place. Confirmed matches will be saved as this project's template.",
  reviewUnmapped: "Review pending files",
  buildDesc: "Review the files below and confirm the mappings that should be saved to this project template.",
  modalTitle: "Review mapping suggestions",
  unmappedTag: "Pending review",
  unmappedNodeLabel: "Detected file",
  candidateWord: "Suggestion",
  recommendedLabel: "Suggested first",
  basedOnEvidence: "Evidence",
  otherSuggestions: (n) => `Other suggestions (${n})`,
  skipThisNode: "Decide later",
  verdictPre: "This file may map to",
  verdictPost: ".",
  whyLabel: "Why this is suggested",
  acceptBtn: "Confirm",
  editBtn: "Edit",
  rejectBtn: "Reject",
  lookingForSuggestions: "Looking for mapping suggestions...",
  suggestionsUnavailable: "Mapping suggestions are unavailable right now.",
  fallbackSuggestions: "Suggestion lookup timed out, so Kai-Mind is showing rule-based suggestions.",
  noSuggestionsFound: "No mapping suggestions found.",
  noSuggestionSummary: "Kai-Mind needs more evidence before it can suggest a mapping for this file.",
  sourceAi: "Suggested",
  sourceRule: "Rule suggestion",
  sourceUser: "You confirmed it",
  sourceDeterministic: "Rule suggestion",
};

const WordingContext = createContext<Wording>(COPY);

export function WordingProvider({ children }: { children: ReactNode }) {
  return createElement(WordingContext.Provider, { value: COPY }, children);
}

export function useWording(): Wording {
  return useContext(WordingContext);
}
