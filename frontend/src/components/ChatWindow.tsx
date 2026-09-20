import { useState } from "react";
import type { Message } from "../api/conversations";
import { MessageBubble } from "./MessageBubble";

interface ChatWindowProps {
  messages: Message[];
  onSend: (content: string) => void;
  disabled: boolean;
}

export function ChatWindow({ messages, onSend, disabled }: ChatWindowProps) {
  const [draft, setDraft] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!draft.trim() || disabled) return;
    onSend(draft);
    setDraft("");
  };

  return (
    <div className="chat-window">
      <div className="chat-window__messages">
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
      </div>
      <form onSubmit={handleSubmit}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={disabled}
          placeholder="Type a message..."
        />
        <button type="submit" disabled={disabled}>
          Send
        </button>
      </form>
    </div>
  );
}
