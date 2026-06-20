import { Check, GitBranch, Info, Sparkles, type LucideIcon } from "lucide-react";
import { useWording } from "../../wording";

const SOURCE_ICON: Record<string, { cls: string; Icon: LucideIcon }> = {
  ai_suggested: { cls: "ai", Icon: Sparkles },
  user_confirmed: { cls: "user", Icon: Check },
  fallback_rule: { cls: "rule", Icon: GitBranch },
  deterministic: { cls: "rule", Icon: GitBranch },
};

/** Provenance label for a mapping / candidate (AI / user / rule). */
export function SourceTag({ source }: { source: string }) {
  const w = useWording();
  const label: Record<string, string> = {
    ai_suggested: w.sourceAi,
    user_confirmed: w.sourceUser,
    fallback_rule: w.sourceRule,
    deterministic: w.sourceDeterministic,
  };
  const meta = SOURCE_ICON[source] ?? { cls: "", Icon: Info };
  const { Icon } = meta;
  return (
    <span className={`src-tag ${meta.cls}`}>
      <Icon size={13} className="ico" />
      {label[source] ?? source}
    </span>
  );
}
