/**
 * Hook to manage chat session history
 */

import { useEffect, useState } from "react";
import { storage } from "@/lib/storage";
import type { ChatSession } from "@/types/chat";

const KEY = "qx.chat.sessions";

export function useChatHistory() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);

  // Load sessions from localStorage on mount
  useEffect(() => {
    setSessions(storage.get<ChatSession[]>(KEY, []));
  }, []);

  // Save sessions to localStorage
  const save = (next: ChatSession[]) => {
    setSessions(next);
    storage.set(KEY, next);
  };

  /**
   * Create a new chat session
   */
  function createNew(title = "New chat"): ChatSession {
    const id = crypto.randomUUID();
    const session: ChatSession = {
      id,
      title,
      createdAt: Date.now(),
    };
    save([session, ...sessions]);
    return session;
  }

  /**
   * Remove a chat session
   */
  function remove(id: string): void {
    save(sessions.filter((s) => s.id !== id));
    
    // Also remove chat history for this session
    storage.remove(`qx.chat.history.${id}`);
  }

  /**
   * Update session title
   */
  function updateTitle(id: string, title: string): void {
    const updated = sessions.map((s) =>
      s.id === id ? { ...s, title } : s
    );
    save(updated);
  }

  /**
   * Update last message timestamp
   */
  function updateLastMessage(id: string): void {
    const updated = sessions.map((s) =>
      s.id === id ? { ...s, lastMessageAt: Date.now() } : s
    );
    save(updated);
  }

  /**
   * Get session by id
   */
  function getSession(id: string): ChatSession | undefined {
    return sessions.find((s) => s.id === id);
  }

  return {
    sessions,
    createNew,
    remove,
    updateTitle,
    updateLastMessage,
    getSession,
  };
}

