/** API types and fetch wrappers for the backend API */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  customer_email?: string;
  customer_name?: string;
}

export interface ChatResponse {
  response: string;
  conversation_id: string;
  ticket_created: boolean;
  escalated: boolean;
  ticket_id?: string;
}

export interface Conversation {
  id: string;
  customer_id: string | null;
  status: "active" | "escalated" | "closed";
  language: string;
  summary: string | null;
  created_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}

export interface Ticket {
  id: string;
  conversation_id: string;
  subject: string;
  description: string;
  category: "billing" | "bug" | "account" | "other";
  status: "open" | "in_progress" | "resolved";
  priority: "low" | "normal" | "high" | "urgent";
  created_at: string;
}

export interface Handoff {
  id: string;
  conversation_id: string;
  reason: string;
  assigned_to: string | null;
  created_at: string;
}

export interface IngestRequest {
  source: string;
  content: string;
  title?: string;
  section?: string;
  language?: string;
}

/** Fetch wrapper with error handling */
async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

/** Chat API */
export const chatApi = {
  sendMessage: (request: ChatRequest) =>
    fetchApi<ChatResponse>("/api/v1/chat", {
      method: "POST",
      body: JSON.stringify(request),
    }),

  getConversation: (conversationId: string) =>
    fetchApi<Conversation>(`/api/v1/conversations/${conversationId}`),

  getMessages: (conversationId: string, limit = 50) =>
    fetchApi<Message[]>(`/api/v1/conversations/${conversationId}/messages?limit=${limit}`),
};

/** Tickets API */
export const ticketsApi = {
  list: (status?: string, limit = 100) =>
    fetchApi<Ticket[]>(`/api/v1/tickets${status ? `?status=${status}` : ""}&limit=${limit}`),

  get: (ticketId: string) =>
    fetchApi<Ticket>(`/api/v1/tickets/${ticketId}`),

  updateStatus: (ticketId: string, status: Ticket["status"]) =>
    fetchApi<Ticket>(`/api/v1/tickets/${ticketId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
};

/** Ingest API */
export const ingestApi = {
  ingest: (request: IngestRequest) =>
    fetchApi<{ status: string; chunks_ingested: number }>("/api/v1/ingest", {
      method: "POST",
      body: JSON.stringify(request),
    }),

  ingestBatch: (requests: IngestRequest[]) =>
    fetchApi<{ results: Array<{ status: string; source: string; error?: string }> }>("/api/v1/ingest/batch", {
      method: "POST",
      body: JSON.stringify(requests),
    }),
};