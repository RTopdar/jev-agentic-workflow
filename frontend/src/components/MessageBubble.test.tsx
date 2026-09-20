import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { MessageBubble } from "./MessageBubble";

describe("MessageBubble", () => {
  it("renders user message without agent badge", () => {
    render(
      <MessageBubble
        message={{
          id: 1,
          conversation_id: 1,
          role: "user",
          agent_id: null,
          content: "hi there",
          severity: null,
          escalated: false,
          created_at: "2026-09-21T00:00:00Z",
        }}
      />
    );
    expect(screen.getByText("hi there")).toBeInTheDocument();
    expect(screen.queryByTestId("agent-badge")).not.toBeInTheDocument();
  });

  it("renders agent message with agent badge", () => {
    render(
      <MessageBubble
        message={{
          id: 2,
          conversation_id: 1,
          role: "agent",
          agent_id: 5,
          content: "how can I help",
          severity: null,
          escalated: false,
          created_at: "2026-09-21T00:00:00Z",
        }}
      />
    );
    expect(screen.getByTestId("agent-badge")).toBeInTheDocument();
  });
});
