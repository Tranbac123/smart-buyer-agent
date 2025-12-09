/**
 * Dynamic Chat Page
 * Multi-session chat with sidebar
 */

import { useRouter } from "next/router";
import { useEffect } from "react";
import ChatWindow from "@/components/ChatWindow";
import Sidebar from "@/components/Sidebar";
import { useChatHistory } from "@/hooks/useChatHistory";
import styles from "@/styles/ChatLayout.module.css";

export default function ChatById() {
  const router = useRouter();
  const { query } = router;
  const id = String(query.id || "");
  const { getSession } = useChatHistory();

  useEffect(() => {
    // If session doesn't exist, create it or redirect
    if (id && !getSession(id)) {
      // Redirect to home if session not found
      router.push("/");
    }
  }, [id, getSession, router]);

  if (!id) {
    return (
      <div className={styles.loading}>
        <div>Loading...</div>
      </div>
    );
  }

  return (
    <div className={styles.layout}>
      {/* Sidebar */}
      <aside className={styles.sidebar}>
        <Sidebar />
      </aside>

      {/* Main Chat Area */}
      <main className={styles.main}>
        <ChatWindow sessionId={id} />
      </main>
    </div>
  );
}

