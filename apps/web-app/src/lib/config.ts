/**
 * Configuration
 */

export const config = {
  // API Base URL
  apiUrl:
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000",
  
  // API Version
  apiVersion: "v1",
  
  // Endpoints
  endpoints: {
    chat: "/v1/chat",
    smartBuyer: "/v1/smart-buyer",
    smartBuyerChat: "/v1/smart-buyer/chat",
    deepResearch: "/v1/deep-research",
    health: "/health",
  },
  
  // Features
  features: {
    streaming: true,
    multiSession: true,
    autoSave: true,
  },
  
  // UI Settings
  ui: {
    maxMessageLength: 4000,
    historyLimit: 100,
    typingDelay: 50,
  },
};
