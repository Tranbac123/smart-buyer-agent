/**
 * Chat Hook - Per-Session State Management
 */

import { useState, useCallback, useEffect, useRef } from "react";
import { storage } from "@/lib/storage";
import { sendSmartBuyerChat } from "@/lib/api";
import type { Message, SmartBuyerChatMessage } from "@/types/chat";
import { useChatHistory } from "./useChatHistory";

const getChatKey = (sessionId: string) => `qx.chat.history.${sessionId}`;

type PersistedChatState = {
  messages: Message[];
  conversationId?: string;
};

const emptyState: PersistedChatState = { messages: [] };

function parsePersistedState(
  value: PersistedChatState | Message[]
): PersistedChatState {
  if (Array.isArray(value)) {
    return { messages: value };
  }
  if (value && Array.isArray(value.messages)) {
    return { messages: value.messages, conversationId: value.conversationId };
  }
  return emptyState;
}

export function useChat(sessionId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamingMessage, setStreamingMessage] = useState<string>("");
  const abortControllerRef = useRef<AbortController | null>(null);
  const { updateLastMessage, updateTitle } = useChatHistory();

  useEffect(() => {
    if (!sessionId) return;
    const saved = storage.get<PersistedChatState | Message[]>(
      getChatKey(sessionId),
      emptyState
    );
    const parsed = parsePersistedState(saved);
    setMessages(parsed.messages);
    setConversationId(parsed.conversationId);
  }, [sessionId]);

  const persistState = useCallback(
    (msgs: Message[], nextConversationId: string | undefined = conversationId) => {
      if (!sessionId) return;
      setMessages(msgs);
      setConversationId(nextConversationId);
      storage.set(getChatKey(sessionId), {
        messages: msgs,
        conversationId: nextConversationId,
      });
      updateLastMessage(sessionId);
    },
    [sessionId, conversationId, updateLastMessage]
  );

  useEffect(() => {
    if (messages.length === 1 && messages[0].role === "user") {
      const firstMessage = messages[0].content;
      const title =
        firstMessage.length > 50 ? `${firstMessage.slice(0, 50)}...` : firstMessage;
      updateTitle(sessionId, title);
    }
  }, [messages, sessionId, updateTitle]);

  const send = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return;

      setError(null);
      setIsLoading(true);
      setStreamingMessage("Thinking...");

      const trimmed = content.trim();
      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: trimmed,
        timestamp: Date.now(),
      };
      const optimisticMessages = [...messages, userMessage];
      persistState(optimisticMessages);

      abortControllerRef.current = new AbortController();

      try {
        const response = await sendSmartBuyerChat(
          {
            message: trimmed,
            conversationId,
          },
          abortControllerRef.current.signal
        );

        const assistantMessages = response.messages
          .filter((msg) => msg.role === "assistant")
          .map((msg) => normalizeChatMessage(msg, response.summary_text));

        persistState(
          [...optimisticMessages, ...assistantMessages],
          response.conversation_id
        );
        setStreamingMessage("");
      } catch (err: any) {
        if (err.name === "AbortError") {
          setError("Request cancelled");
        } else {
          setError(err.message || "Failed to send message");
          console.error("Chat error:", err);
        }
      } finally {
        setIsLoading(false);
        setStreamingMessage("");
        abortControllerRef.current = null;
      }
    },
    [conversationId, isLoading, messages, persistState]
  );

  const cancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsLoading(false);
      setStreamingMessage("");
    }
  }, []);

  const clear = useCallback(() => {
    persistState([], undefined);
    setStreamingMessage("");
    setError(null);
  }, [persistState]);

  const retry = useCallback(() => {
    if (messages.length === 0) return;
    
    const lastUserMessage = [...messages]
      .reverse()
      .find((message) => message.role === "user");
    
    if (lastUserMessage) {
      const index = messages.findIndex((m) => m.id === lastUserMessage.id);
      const trimmed = messages.slice(0, index + 1);
      persistState(trimmed);
      send(lastUserMessage.content);
    }
  }, [messages, persistState, send]);

  return {
    messages,
    streamingMessage,
    isLoading,
    error,
    send,
    cancel,
    clear,
    retry,
  };
}

function normalizeChatMessage(
  message: SmartBuyerChatMessage,
  fallbackSummary?: string | null
): Message {
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    timestamp: new Date(message.created_at).getTime(),
    metadata: message.metadata
      ? {
          intent: message.metadata.intent,
          flow_type: message.metadata.flow_type,
          top_recommendations: message.metadata.top_recommendations,
          explanation: message.metadata.explanation,
          summary_text: message.metadata.summary_text ?? fallbackSummary ?? undefined,
        }
      : fallbackSummary
      ? { flow_type: "smart_buyer", summary_text: fallbackSummary }
      : undefined,
  };
}
