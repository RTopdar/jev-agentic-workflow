import { describe, it, expect, vi, beforeEach } from "vitest";
import { sendMessage, streamUrl } from "./messages";

describe("sendMessage", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ message_id: 42 }),
      })
    ) as unknown as typeof fetch;
  });

  it("posts content and returns message_id", async () => {
    const result = await sendMessage(1, "hello");
    expect(result.message_id).toBe(42);
    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8000/conversations/1/messages",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("builds the correct stream url", () => {
    expect(streamUrl(1, 42)).toBe(
      "http://localhost:8000/conversations/1/messages/42/stream"
    );
  });
});
