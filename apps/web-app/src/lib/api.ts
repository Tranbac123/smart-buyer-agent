/**
 * API Client
 * Handles communication with backend API
 */

import { config } from "./config";
import type { SendMessageRequest, SendMessageResponse } from "@/types/chat";

/**
 * Stream chunk types
 */
type StreamChunk =
  | { type: "content"; content: string }
  | { type: "metadata"; data: any }
  | { type: "error"; message: string }
  | { type: "done" };

/**
 * Send message to API with streaming support
 */
export async function* sendMessage(
  request: SendMessageRequest,
  signal?: AbortSignal
): AsyncGenerator<StreamChunk> {
  const url = `${config.apiUrl}${config.endpoints.chat}`;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
      signal,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.message || `HTTP ${response.status}`);
    }

    // Check if streaming is supported
    const contentType = response.headers.get("content-type");
    const isStreaming = contentType?.includes("text/event-stream");

    if (isStreaming && response.body) {
      // Process Server-Sent Events (SSE) stream
      yield* processSSEStream(response.body);
    } else {
      // Non-streaming response
      const data: SendMessageResponse = await response.json();
      
      // Yield content
      yield {
        type: "content",
        content: data.response,
      };

      // Yield metadata
      yield {
        type: "metadata",
        data: {
          intent: data.intent,
          flow_type: data.flow_type,
          top_recommendations: data.top_recommendations,
          explanation: data.explanation,
          metadata: data.metadata,
        },
      };
    }

    yield { type: "done" };
  } catch (error: any) {
    if (error.name === "AbortError") {
      throw error;
    }
    
    yield {
      type: "error",
      message: error.message || "Failed to send message",
    };
  }
}

/**
 * Process Server-Sent Events stream
 */
async function* processSSEStream(
  body: ReadableStream<Uint8Array>
): AsyncGenerator<StreamChunk> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) break;

      // Decode chunk
      buffer += decoder.decode(value, { stream: true });

      // Process complete lines
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        
        if (!trimmed || trimmed.startsWith(":")) continue;

        // Parse SSE format: "data: {...}"
        if (trimmed.startsWith("data:")) {
          const data = trimmed.slice(5).trim();
          
          if (data === "[DONE]") {
            return;
          }

          try {
            const parsed = JSON.parse(data);
            
            // Handle different chunk types
            if (parsed.type === "content" || parsed.content) {
              yield {
                type: "content",
                content: parsed.content || parsed.delta || "",
              };
            } else if (parsed.type === "metadata") {
              yield {
                type: "metadata",
                data: parsed.data,
              };
            } else if (parsed.type === "error") {
              yield {
                type: "error",
                message: parsed.message,
              };
            }
          } catch (err) {
            console.error("Failed to parse SSE data:", data, err);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Send message to Smart Buyer flow
 */
export async function* sendSmartBuyerMessage(
  request: SendMessageRequest,
  signal?: AbortSignal
): AsyncGenerator<StreamChunk> {
  const url = `${config.apiUrl}${config.endpoints.smartBuyer}`;

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      ...request,
      context: {
        ...request.context,
        flow_type: "smart_buyer",
      },
    }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  if (response.body) {
    yield* processSSEStream(response.body);
  }
}

/**
 * Send message to Deep Research flow
 */
export async function* sendDeepResearchMessage(
  request: SendMessageRequest,
  signal?: AbortSignal
): AsyncGenerator<StreamChunk> {
  const url = `${config.apiUrl}${config.endpoints.deepResearch}`;

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      ...request,
      context: {
        ...request.context,
        flow_type: "deep_research",
      },
    }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  if (response.body) {
    yield* processSSEStream(response.body);
  }
}

/**
 * Health check
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${config.apiUrl}${config.endpoints.health}`);
    return response.ok;
  } catch {
    return false;
  }
}
