import { useCallback, useEffect, useState } from "react";
import {
  createConversation,
  getConversation,
  listConversations,
} from "../api/conversations";
import type { ConversationDetail, ConversationSummary, Message } from "../api/conversations";
import { sendMessage, streamUrl } from "../api/messages";
import { useSSEStream } from "../hooks/useSSEStream";
import { ChatWindow } from "../components/ChatWindow";
import { EscalationBanner } from "../components/EscalationBanner";
import { Sidebar } from "../components/Sidebar";
import "./ChatPage.css";

const LAST_CONVERSATION_KEY = "jev-chat:last-conversation-id";

function rememberConversation(id: number) {
  try {
    localStorage.setItem(LAST_CONVERSATION_KEY, String(id));
  } catch {
    // localStorage unavailable (private mode, blocked storage) — non-fatal
  }
}

function readRememberedConversation(): number | null {
  try {
    const raw = localStorage.getItem(LAST_CONVERSATION_KEY);
    return raw ? Number(raw) : null;
  } catch {
    return null;
  }
}

export function ChatPage() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [streamingUrl, setStreamingUrl] = useState<string | null>(null);
  const [streamingMessageId, setStreamingMessageId] = useState<number | null>(null);
  const [partialContent, setPartialContent] = useState("");

  const refreshSidebar = useCallback(async () => {
    setConversations(await listConversations());
  }, []);

  const selectConversation = useCallback(async (id: number) => {
    setConversation(await getConversation(id));
    rememberConversation(id);
  }, []);

  useEffect(() => {
    (async () => {
      const existing = await listConversations();
      setConversations(existing);

      const rememberedId = readRememberedConversation();
      const remembered = rememberedId
        ? existing.find((c) => c.id === rememberedId)
        : undefined;

      if (remembered) {
        await selectConversation(remembered.id);
      } else if (existing.length > 0) {
        await selectConversation(existing[0].id);
      } else {
        const created = await createConversation();
        rememberConversation(created.id);
        setConversation({ id: created.id, status: created.status, messages: [] });
        await refreshSidebar();
      }
    })();
  }, [refreshSidebar, selectConversation]);

  const refreshConversation = useCallback(async () => {
    if (!conversation) return;
    const detail = await getConversation(conversation.id);
    setConversation(detail);
  }, [conversation?.id]);

  useSSEStream(
    streamingUrl,
    (token) => setPartialContent((prev) => prev + token),
    () => {
      setStreamingUrl(null);
      setStreamingMessageId(null);
      setPartialContent("");
      refreshConversation();
      refreshSidebar();
    }
  );

  const handleSend = async (content: string) => {
    if (!conversation) return;
    const { message_id } = await sendMessage(conversation.id, content);
    await refreshConversation();
    setStreamingMessageId(message_id);
    setStreamingUrl(streamUrl(conversation.id, message_id));
  };

  const handleNewChat = async () => {
    const created = await createConversation();
    rememberConversation(created.id);
    await refreshSidebar();
    setConversation({ id: created.id, status: created.status, messages: [] });
  };

  const handleSelect = async (id: number) => {
    if (conversation?.id === id) return;
    setStreamingUrl(null);
    setStreamingMessageId(null);
    setPartialContent("");
    await selectConversation(id);
  };

  if (!conversation) {
    return <div className="chat-page__loading">Starting conversation…</div>;
  }

  const displayMessages: Message[] = streamingMessageId
    ? conversation.messages.map((m) =>
        m.id === streamingMessageId ? { ...m, content: partialContent } : m
      )
    : conversation.messages;

  return (
    <div className="chat-page">
      <Sidebar
        conversations={conversations}
        activeId={conversation.id}
        onSelect={handleSelect}
        onNewChat={handleNewChat}
      />
      <div className="chat-page__main">
        <EscalationBanner status={conversation.status} />
        <ChatWindow
          messages={displayMessages}
          onSend={handleSend}
          disabled={conversation.status === "escalated"}
        />
      </div>
    </div>
  );
}
