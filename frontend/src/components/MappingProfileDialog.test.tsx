import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MappingProfileDialog } from "./MappingProfileDialog";

vi.mock("../pages/ScanTemplatePage", () => ({
  ScanTemplatePage: ({ onClose }: { onClose: () => void }) => (
    <div>
      <h1>Mapping profile content</h1>
      <button type="button" onClick={onClose}>Close content</button>
    </div>
  ),
}));

describe("MappingProfileDialog", () => {
  it("renders as a modal instead of a full-screen route and closes with Escape", () => {
    const onClose = vi.fn();
    render(<MappingProfileDialog onClose={onClose} onOpenProposal={() => {}} />);

    expect(screen.getByRole("dialog", { name: "Mapping profile" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Mapping profile content" })).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("closes from the backdrop without closing for clicks inside the dialog", () => {
    const onClose = vi.fn();
    const { container } = render(<MappingProfileDialog onClose={onClose} onOpenProposal={() => {}} />);
    const scrim = container.querySelector(".mapping-profile-scrim");
    const dialog = screen.getByRole("dialog", { name: "Mapping profile" });

    fireEvent.mouseDown(dialog);
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.mouseDown(scrim!);
    expect(onClose).toHaveBeenCalledOnce();
  });
});
