/**
 * Chat Hook - Per-Session State Management
 */

import { useState, useCallback, useEffect, useRef } from "react";
import { storage } from "@/lib/storage";
import { sendMessage } from "@/lib/api";
import type { Message } from "@/types/chat";
import { useChatHistory } from "./useChatHistory";

const getChatKey = (sessionId: string) => `qx.chat.history.${sessionId}`;

export function useChat(sessionId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamingMessage, setStreamingMessage] = useState<string>("");
  const abortControllerRef = useRef<AbortController | null>(null);
  const { updateLastMessage, updateTitle } = useChatHistory();

  // Load messages from localStorage on mount
  useEffect(() => {
    if (!sessionId) return;
    
    const saved = storage.get<Message[]>(getChatKey(sessionId), []);
    setMessages(saved);
  }, [sessionId]);

  // Save messages to localStorage whenever they change
  const saveMessages = useCallback(
    (msgs: Message[]) => {
      if (!sessionId) return;
      setMessages(msgs);
      storage.set(getChatKey(sessionId), msgs);
      updateLastMessage(sessionId);
    },
    [sessionId, updateLastMessage]
  );

  // Auto-generate title from first message
  useEffect(() => {
    if (messages.length === 1 && messages[0].role === "user") {
      const firstMessage = messages[0].content;
      const title = firstMessage.length > 50
        ? firstMessage.slice(0, 50) + "..."
        : firstMessage;
      updateTitle(sessionId, title);
    }
  }, [messages, sessionId, updateTitle]);

  /**
   * Send a message
   */
  const send = useCallback(
    async (content: string, context?: any) => {
      if (!content.trim() || isLoading) return;

      setError(null);
      setIsLoading(true);
      setStreamingMessage("");

      // Add user message
      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: content.trim(),
        timestamp: Date.now(),
      };

      const updatedMessages = [...messages, userMessage];
      saveMessages(updatedMessages);

      // Create abort controller for this request
      abortControllerRef.current = new AbortController();

      try {
        // Call API with streaming
        const stream = await sendMessage(
          {
            message: content.trim(),
            sessionId,
            context,
          },
          abortControllerRef.current.signal
        );

        // Process stream
        let fullResponse = "";
        let metadata: any = {};

        for await (const chunk of stream) {
          if (chunk.type === "content") {
            fullResponse += chunk.content;
            setStreamingMessage(fullResponse);
          } else if (chunk.type === "metadata") {
            metadata = chunk.data;
          } else if (chunk.type === "error") {
            throw new Error(chunk.message);
          }
        }

        // Add assistant message
        const assistantMessage: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: fullResponse,
          timestamp: Date.now(),
          metadata,
        };

        saveMessages([...updatedMessages, assistantMessage]);
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
        abortControllerRef.current = null;
      }
    },
    [messages, isLoading, sessionId, saveMessages]
  );

  /**
   * Cancel ongoing request
   */
  const cancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsLoading(false);
      setStreamingMessage("");
    }
  }, []);

  /**
   * Clear chat history for this session
   */
  const clear = useCallback(() => {
    saveMessages([]);
    setStreamingMessage("");
    setError(null);
  }, [saveMessages]);

  /**
   * Retry last message
   */
  const retry = useCallback(() => {
    if (messages.length === 0) return;
    
    // Find last user message
    const lastUserMessage = [...messages]
      .reverse()
      .find((m) => m.role === "user");
    
    if (lastUserMessage) {
      // Remove messages after last user message
      const index = messages.findIndex((m) => m.id === lastUserMessage.id);
      const trimmed = messages.slice(0, index);
      saveMessages(trimmed);
      
      // Resend
      send(lastUserMessage.content);
    }
  }, [messages, saveMessages, send]);

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
