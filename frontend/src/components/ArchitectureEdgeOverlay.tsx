import { useLayoutEffect, useRef, useState, type ReactNode } from "react";

export type ArchitectureConnection = {
  id: string;
  from: string;
  to: string;
  source: "declared-edge" | "projection-relationship";
  focused: boolean;
  selected: boolean;
  traceHighlighted: boolean;
};

type MeasuredConnection = ArchitectureConnection & { d: string };

type OverlaySize = {
  width: number;
  height: number;
};

type Props = {
  connections: ArchitectureConnection[];
  children: ReactNode;
};

function point(value: number): string {
  return value.toFixed(1);
}

function connectionPath(root: DOMRect, from: DOMRect, to: DOMRect): string {
  const fromCenterX = from.left + from.width / 2 - root.left;
  const fromCenterY = from.top + from.height / 2 - root.top;
  const toCenterX = to.left + to.width / 2 - root.left;
  const toCenterY = to.top + to.height / 2 - root.top;
  const deltaX = toCenterX - fromCenterX;
  const deltaY = toCenterY - fromCenterY;

  if (Math.abs(deltaY) > Math.max(48, Math.abs(deltaX) * 0.55)) {
    const direction = deltaY >= 0 ? 1 : -1;
    const x1 = fromCenterX;
    const y1 = (direction > 0 ? from.bottom : from.top) - root.top;
    const x2 = toCenterX;
    const y2 = (direction > 0 ? to.top : to.bottom) - root.top;
    const bend = Math.max(34, Math.abs(y2 - y1) * 0.38);
    return `M ${point(x1)} ${point(y1)} C ${point(x1)} ${point(y1 + direction * bend)}, ${point(x2)} ${point(y2 - direction * bend)}, ${point(x2)} ${point(y2)}`;
  }

  const direction = deltaX >= 0 ? 1 : -1;
  const x1 = (direction > 0 ? from.right : from.left) - root.left;
  const y1 = fromCenterY;
  const x2 = (direction > 0 ? to.left : to.right) - root.left;
  const y2 = toCenterY;
  const bend = Math.max(34, Math.abs(x2 - x1) * 0.42);
  return `M ${point(x1)} ${point(y1)} C ${point(x1 + direction * bend)} ${point(y1)}, ${point(x2 - direction * bend)} ${point(y2)}, ${point(x2)} ${point(y2)}`;
}

export function ArchitectureEdgeOverlay({ connections, children }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState<OverlaySize>({ width: 1, height: 1 });
  const [paths, setPaths] = useState<MeasuredConnection[]>([]);

  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const measure = () => {
      const root = container.getBoundingClientRect();
      const nodeElements = new Map(
        Array.from(container.querySelectorAll<HTMLElement>("[data-node-id]"))
          .map((element) => [element.dataset.nodeId, element] as const)
          .filter((entry): entry is [string, HTMLElement] => entry[0] != null),
      );
      const nextPaths = connections.flatMap((connection) => {
        const fromElement = nodeElements.get(connection.from);
        const toElement = nodeElements.get(connection.to);
        if (!fromElement || !toElement || connection.from === connection.to) return [];
        return [
          {
            ...connection,
            d: connectionPath(root, fromElement.getBoundingClientRect(), toElement.getBoundingClientRect()),
          },
        ];
      });

      setSize({
        width: Math.max(1, container.scrollWidth, root.width),
        height: Math.max(1, container.scrollHeight, root.height),
      });
      setPaths(nextPaths);
    };

    measure();
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(measure);
    observer?.observe(container);
    window.addEventListener("resize", measure);
    return () => {
      observer?.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, [connections]);

  return (
    <div className="dr-plane-stack" ref={containerRef} aria-label="AI Agent System, ten architecture planes">
      {children}
      <svg
        className="dr-edge-overlay"
        viewBox={`0 0 ${size.width} ${size.height}`}
        width={size.width}
        height={size.height}
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        {paths.map((connection) => (
          <path
            key={`${connection.source}:${connection.id}`}
            className={[
              "dr-edge-path",
              `is-${connection.source}`,
              connection.focused ? "is-focused" : "is-dimmed",
              connection.selected ? "is-selected" : "",
              connection.traceHighlighted ? "is-trace-highlight" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            data-connection-id={connection.id}
            data-connection-source={connection.source}
            d={connection.d}
          />
        ))}
      </svg>
    </div>
  );
}
