import type { Message } from "../api/conversations";
import { AgentBadge } from "./AgentBadge";

export function MessageBubble({ message }: { message: Message }) {
  return (
    <div className={`message-bubble message-bubble--${message.role}`}>
      {message.role === "agent" && message.agent_id !== null && (
        <AgentBadge agentId={message.agent_id} />
      )}
      <p>{message.content}</p>
    </div>
  );
}
