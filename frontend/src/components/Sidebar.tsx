import type { ConversationSummary } from "../api/conversations";

interface SidebarProps {
  conversations: ConversationSummary[];
  activeId: number | null;
  onSelect: (id: number) => void;
  onNewChat: () => void;
}

export function Sidebar({ conversations, activeId, onSelect, onNewChat }: SidebarProps) {
  return (
    <aside className="sidebar">
      <button className="sidebar__new-chat" onClick={onNewChat}>
        New chat
      </button>
      <div className="sidebar__list">
        {conversations.map((c) => (
          <button
            key={c.id}
            className={
              "sidebar__row" + (c.id === activeId ? " sidebar__row--active" : "")
            }
            onClick={() => onSelect(c.id)}
          >
            {c.preview ?? "New conversation"}
          </button>
        ))}
      </div>
    </aside>
  );
}
