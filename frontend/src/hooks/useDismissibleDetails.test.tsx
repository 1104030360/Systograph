import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useDismissibleDetails } from "./useDismissibleDetails";

function Harness() {
  const detailsRef = useDismissibleDetails();
  return (
    <>
      <details ref={detailsRef} open>
        <summary>Tools</summary>
        <button type="button">Inside action</button>
      </details>
      <button type="button">Outside action</button>
    </>
  );
}

describe("useDismissibleDetails", () => {
  it("keeps the menu open for an interaction inside it", () => {
    render(<Harness />);

    fireEvent.pointerDown(screen.getByRole("button", { name: "Inside action" }));

    expect(screen.getByText("Tools").closest("details")).toHaveAttribute("open");
  });

  it("closes the menu when the user interacts outside it", () => {
    render(<Harness />);

    fireEvent.pointerDown(screen.getByRole("button", { name: "Outside action" }));

    expect(screen.getByText("Tools").closest("details")).not.toHaveAttribute("open");
  });

  it("closes the menu and returns focus to its summary on Escape", () => {
    render(<Harness />);

    fireEvent.keyDown(window, { key: "Escape" });

    const summary = screen.getByText("Tools");
    expect(summary.closest("details")).not.toHaveAttribute("open");
    expect(summary).toHaveFocus();
  });
});
