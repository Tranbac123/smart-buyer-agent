/**
 * Chat types
 */

export type ChatSession = {
  id: string;
  title: string;
  createdAt: number;
  lastMessageAt?: number;
};

export type SmartBuyerRecommendation = {
  rank?: number;
  score?: number;
  product?: {
    name?: string;
    price?: number;
    site?: string;
    url?: string;
  };
};

export type SmartBuyerExplanation = {
  winner?: string;
  confidence: number;
  best_by_criterion: Record<string, any>;
  tradeoffs: string[];
  per_option: Record<string, any>[];
  summary: string;
};

export type MessageMetadata = {
  intent?: string;
  flow_type?: string;
  top_recommendations?: SmartBuyerRecommendation[];
  explanation?: SmartBuyerExplanation | Record<string, any>;
  summary_text?: string;
};

export type Message = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
  metadata?: MessageMetadata;
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

export type SmartBuyerChatRequest = {
  message: string;
  conversationId?: string;
  topK?: number;
  prefs?: Record<string, any>;
  criteria?: Array<Record<string, any>>;
};

export type SmartBuyerChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  metadata?: {
    intent?: string;
    flow_type?: string;
    top_recommendations?: SmartBuyerRecommendation[];
    explanation?: SmartBuyerExplanation | Record<string, any>;
    summary_text?: string | null;
  };
};

export type SmartBuyerOffer = {
  id?: string;
  site: string;
  title: string;
  price: number | string;
  url: string;
  currency: string;
  rating?: number;
  shop_name?: string;
  tags?: string[];
};

export type SmartBuyerOptionScore = {
  option_id: string;
  total_score: number;
  rank: number;
};

export type SmartBuyerScoring = {
  best?: string;
  confidence: number;
  option_scores: SmartBuyerOptionScore[];
};

export type SmartBuyerChatResponse = {
  conversation_id: string;
  messages: SmartBuyerChatMessage[];
  offers: SmartBuyerOffer[];
  scoring: SmartBuyerScoring;
  explanation: SmartBuyerExplanation;
  metadata: Record<string, any>;
  summary_text?: string | null;
};
