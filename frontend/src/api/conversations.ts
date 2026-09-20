import { apiFetch } from "./client";

export interface Message {
  id: number;
  conversation_id: number;
  role: "user" | "agent" | "system";
  agent_id: number | null;
  content: string;
  severity: number | null;
  escalated: boolean;
  created_at: string;
}

export interface Conversation {
  id: number;
  status: "active" | "escalated" | "closed";
  created_at: string;
}

export interface ConversationDetail {
  id: number;
  status: string;
  messages: Message[];
}

export interface ConversationSummary {
  id: number;
  status: string;
  created_at: string;
  preview: string | null;
}

export function createConversation(): Promise<Conversation> {
  return apiFetch<Conversation>("/conversations", { method: "POST" });
}

export function getConversation(id: number): Promise<ConversationDetail> {
  return apiFetch<ConversationDetail>(`/conversations/${id}`);
}

export function listConversations(): Promise<ConversationSummary[]> {
  return apiFetch<ConversationSummary[]>("/conversations");
}
