// Chat-related TypeScript types for the Financial Assistant

/**
 * Represents a chat message in the conversation
 */
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: Date;
}

/**
 * Stream response chunk from the backend
 */
export interface StreamResponse {
  content: string;
  type?: 'text' | 'tool_call' | 'error' | 'complete';
  toolName?: string;
  toolInput?: Record<string, unknown>;
}

/**
 * API request body for chat endpoint
 */
export interface ApiChatRequest {
  messages: Array<{
    role: 'user' | 'assistant';
    content: string;
  }>;
}

/**
 * API response for chat endpoint
 */
export interface ApiChatResponse {
  content: string;
}
