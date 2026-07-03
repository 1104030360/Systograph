import { FlaskConical } from "lucide-react";

type Props = {
  visible: boolean;
};

export function SampleDataIndicator({ visible }: Props) {
  if (!visible) return null;

  return (
    <div className="sample-indicator" role="note" aria-label="Sample data indicator">
      <FlaskConical size={13} />
      Sample data — example map, not a real scan
    </div>
  );
}
