import { useCallback, useEffect, useState } from "react";
import { createConversation, getConversation } from "../api/conversations";
import type { ConversationDetail, Message } from "../api/conversations";
import { sendMessage, streamUrl } from "../api/messages";
import { useSSEStream } from "../hooks/useSSEStream";
import { ChatWindow } from "../components/ChatWindow";
import { EscalationBanner } from "../components/EscalationBanner";

export function ChatPage() {
  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [streamingUrl, setStreamingUrl] = useState<string | null>(null);
  const [streamingMessageId, setStreamingMessageId] = useState<number | null>(null);
  const [partialContent, setPartialContent] = useState("");

  useEffect(() => {
    createConversation().then((c) =>
      setConversation({ id: c.id, status: c.status, messages: [] })
    );
  }, []);

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
    }
  );

  const handleSend = async (content: string) => {
    if (!conversation) return;
    const { message_id } = await sendMessage(conversation.id, content);
    await refreshConversation();
    setStreamingMessageId(message_id);
    setStreamingUrl(streamUrl(conversation.id, message_id));
  };

  if (!conversation) return <div>Loading...</div>;

  const displayMessages: Message[] = streamingMessageId
    ? conversation.messages.map((m) =>
        m.id === streamingMessageId ? { ...m, content: partialContent } : m
      )
    : conversation.messages;

  return (
    <div className="chat-page">
      <EscalationBanner status={conversation.status} />
      <ChatWindow
        messages={displayMessages}
        onSend={handleSend}
        disabled={conversation.status === "escalated"}
      />
    </div>
  );
}
