/**
 * Chat types
 */

export type ChatSession = {
  id: string;
  title: string;
  createdAt: number;
  lastMessageAt?: number;
};

export type Message = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
  metadata?: {
    intent?: string;
    flow_type?: string;
    top_recommendations?: any[];
    explanation?: any;
  };
};

export type ChatHistory = {
  sessionId: string;
  messages: Message[];
};

export type SendMessageRequest = {
  message: string;
  sessionId: string;
  context?: {
    flow_type?: string;
    intent?: string;
    max_results?: number;
    sites?: string[];
  };
};

export type SendMessageResponse = {
  response: string;
  type: string;
  intent?: string;
  flow_type?: string;
  session_id: string;
  metadata?: any;
  top_recommendations?: any[];
  explanation?: any;
};
