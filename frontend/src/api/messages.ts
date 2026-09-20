import { apiFetch, BASE_URL } from "./client";

export interface SendMessageResponse {
  message_id: number;
}

export function sendMessage(
  conversationId: number,
  content: string
): Promise<SendMessageResponse> {
  return apiFetch<SendMessageResponse>(`/conversations/${conversationId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export function streamUrl(conversationId: number, messageId: number): string {
  return `${BASE_URL}/conversations/${conversationId}/messages/${messageId}/stream`;
}
