/**
 * New Chat Button Component
 * Creates a new chat session and navigates to it
 */

import { useRouter } from "next/router";
import type { ChatSession } from "@/types/chat";
import styles from "@/styles/NewChatButton.module.css";

interface NewChatButtonProps {
  onNewChat: () => ChatSession;
}

export default function NewChatButton({ onNewChat }: NewChatButtonProps) {
  const router = useRouter();

  const handleNewChat = () => {
    const session = onNewChat();
    router.push(`/chat/${session.id}`);
  };

  return (
    <button
      className={styles.button}
      onClick={handleNewChat}
    >
      <svg
        className={styles.icon}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 4v16m8-8H4"
        />
      </svg>
      New Chat
    </button>
  );
}

