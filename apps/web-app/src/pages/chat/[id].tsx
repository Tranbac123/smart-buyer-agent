/**
 * Dynamic Chat Page
 * Multi-session chat with sidebar
 */

import { useRouter } from "next/router";
import { useEffect } from "react";
import ChatWindow from "@/components/ChatWindow";
import Sidebar from "@/components/Sidebar";
import { useChatHistory } from "@/hooks/useChatHistory";

export default function ChatById() {
  const router = useRouter();
  const { query } = router;
  const id = String(query.id || "");
  const { getSession, createNew } = useChatHistory();

  useEffect(() => {
    // If session doesn't exist, create it or redirect
    if (id && !getSession(id)) {
      // Redirect to home if session not found
      router.push("/");
    }
  }, [id, getSession, router]);

  if (!id) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0">
        <Sidebar />
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col">
        <ChatWindow sessionId={id} />
      </main>
    </div>
  );
}

