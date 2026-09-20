import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Sidebar } from "./Sidebar";

const conversations = [
  { id: 2, status: "active", created_at: "2026-09-21T00:00:00Z", preview: "second chat" },
  { id: 1, status: "active", created_at: "2026-09-20T00:00:00Z", preview: null },
];

describe("Sidebar", () => {
  it("renders a row per conversation with preview or fallback text", () => {
    render(
      <Sidebar
        conversations={conversations}
        activeId={2}
        onSelect={vi.fn()}
        onNewChat={vi.fn()}
      />
    );
    expect(screen.getByText("second chat")).toBeInTheDocument();
    expect(screen.getByText("New conversation")).toBeInTheDocument();
  });

  it("calls onSelect with the conversation id when a row is clicked", () => {
    const onSelect = vi.fn();
    render(
      <Sidebar
        conversations={conversations}
        activeId={2}
        onSelect={onSelect}
        onNewChat={vi.fn()}
      />
    );
    fireEvent.click(screen.getByText("second chat"));
    expect(onSelect).toHaveBeenCalledWith(2);
  });

  it("calls onNewChat when the new chat button is clicked", () => {
    const onNewChat = vi.fn();
    render(
      <Sidebar
        conversations={conversations}
        activeId={2}
        onSelect={vi.fn()}
        onNewChat={onNewChat}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: /new chat/i }));
    expect(onNewChat).toHaveBeenCalled();
  });
});
