import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { EscalationBanner } from "./EscalationBanner";

describe("EscalationBanner", () => {
  it("renders nothing when status is active", () => {
    const { container } = render(<EscalationBanner status="active" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders banner when status is escalated", () => {
    render(<EscalationBanner status="escalated" />);
    expect(
      screen.getByText(/moved to a human agent/i)
    ).toBeInTheDocument();
  });
});
