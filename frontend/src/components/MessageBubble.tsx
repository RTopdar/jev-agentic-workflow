import type { Message } from "../api/conversations";
import { AgentBadge } from "./AgentBadge";

export function MessageBubble({ message }: { message: Message }) {
  return (
    <div className={`message-row message-row--${message.role}`}>
      <div className="message-bubble">
        {message.role === "agent" && message.agent_id !== null && (
          <AgentBadge agentId={message.agent_id} />
        )}
        <p className="message-bubble__text">{message.content}</p>
      </div>
    </div>
  );
}
