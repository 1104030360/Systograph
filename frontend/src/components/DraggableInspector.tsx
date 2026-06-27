import { useRef, useState, type CSSProperties, type PointerEvent, type ReactNode } from "react";

type Point = { x: number; y: number };
type DragState = {
  pointerId: number;
  origin: Point;
  offset: Point;
};

export function DraggableInspector({ children }: { children: ReactNode }) {
  const panelRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<DragState | null>(null);
  const [offset, setOffset] = useState<Point>({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);

  function startDrag(event: PointerEvent<HTMLDivElement>) {
    if (window.matchMedia("(max-width: 880px)").matches) return;
    if (!(event.target instanceof Element) || !event.target.closest(".inspector-head")) return;
    if (event.target.closest("button, a, input, textarea, select")) return;

    dragRef.current = {
      pointerId: event.pointerId,
      origin: { x: event.clientX, y: event.clientY },
      offset,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
    setDragging(true);
    event.preventDefault();
  }

  function moveDrag(event: PointerEvent<HTMLDivElement>) {
    const drag = dragRef.current;
    const panel = panelRef.current;
    const frame = panel?.parentElement;
    if (!drag || drag.pointerId !== event.pointerId || !panel || !frame) return;

    const panelRect = panel.getBoundingClientRect();
    const frameRect = frame.getBoundingClientRect();
    const baseLeft = panelRect.left - offset.x;
    const baseTop = panelRect.top - offset.y;
    const padding = 8;
    const next = {
      x: drag.offset.x + event.clientX - drag.origin.x,
      y: drag.offset.y + event.clientY - drag.origin.y,
    };

    setOffset({
      x: Math.min(
        frameRect.right - padding - baseLeft - panelRect.width,
        Math.max(frameRect.left + padding - baseLeft, next.x),
      ),
      y: Math.min(
        frameRect.bottom - padding - baseTop - panelRect.height,
        Math.max(frameRect.top + padding - baseTop, next.y),
      ),
    });
  }

  function stopDrag(event: PointerEvent<HTMLDivElement>) {
    if (dragRef.current?.pointerId !== event.pointerId) return;
    dragRef.current = null;
    setDragging(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  return (
    <div
      ref={panelRef}
      className={dragging ? "inspector is-dragging" : "inspector"}
      style={{ "--inspector-x": `${offset.x}px`, "--inspector-y": `${offset.y}px` } as CSSProperties}
      onPointerDown={startDrag}
      onPointerMove={moveDrag}
      onPointerUp={stopDrag}
      onPointerCancel={stopDrag}
    >
      {children}
    </div>
  );
}
