/**
 * Hook to manage chat session history
 */

import { useCallback, useMemo, useSyncExternalStore } from "react";
import { storage } from "@/lib/storage";
import type { ChatSession } from "@/types/chat";

const KEY = "qx.chat.sessions";
type Listener = () => void;

let sessionsCache: ChatSession[] = [];
let sortedSessionsCache: ChatSession[] = [];
const listeners = new Set<Listener>();
let hasHydrated = false;

function emit() {
  const currentListeners = Array.from(listeners);
  currentListeners.forEach((listener) => listener());
}

function subscribe(listener: Listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot() {
  return sortedSessionsCache;
}

function sortSessions(sessions: ChatSession[]): ChatSession[] {
  return sessions.slice().sort((a, b) => {
    const timeA = a.lastMessageAt || a.createdAt;
    const timeB = b.lastMessageAt || b.createdAt;
    return timeB - timeA; // Newest first
  });
}

function hydrateFromStorage() {
  if (hasHydrated) return;
  sessionsCache = storage.get<ChatSession[]>(KEY, []);
  sortedSessionsCache = sortSessions(sessionsCache);
  hasHydrated = true;
}

function persist(next: ChatSession[]) {
  sessionsCache = next;
  sortedSessionsCache = sortSessions(next);
  storage.set(KEY, next);
  emit();
}

function generateId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return Math.random().toString(16).slice(2);
}

export function useChatHistory() {
  if (!hasHydrated) {
    hydrateFromStorage();
  }

  const sessions = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  const createNew = useCallback((title = "New chat"): ChatSession => {
    hydrateFromStorage();
    const session: ChatSession = {
      id: generateId(),
      title,
      createdAt: Date.now(),
    };
    persist([session, ...sessionsCache]);
    return session;
  }, []);

  const remove = useCallback((id: string): void => {
    hydrateFromStorage();
    persist(sessionsCache.filter((s) => s.id !== id));
    storage.remove(`qx.chat.history.${id}`);
  }, []);

  const updateTitle = useCallback((id: string, title: string): void => {
    hydrateFromStorage();
    persist(
      sessionsCache.map((s) => (s.id === id ? { ...s, title } : s))
    );
  }, []);

  const updateLastMessage = useCallback((id: string): void => {
    hydrateFromStorage();
    persist(
      sessionsCache.map((s) =>
        s.id === id ? { ...s, lastMessageAt: Date.now() } : s
      )
    );
  }, []);

  const getSession = useCallback((id: string): ChatSession | undefined => {
    hydrateFromStorage();
    return sessionsCache.find((s) => s.id === id);
  }, []);

  return useMemo(
    () => ({
      sessions,
      createNew,
      remove,
      updateTitle,
      updateLastMessage,
      getSession,
    }),
    [sessions, createNew, remove, updateTitle, updateLastMessage, getSession]
  );
}

