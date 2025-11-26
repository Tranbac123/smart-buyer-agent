/**
 * New Chat Button Component
 * Creates a new chat session and navigates to it
 */

import { useRouter } from "next/router";
import { useChatHistory } from "@/hooks/useChatHistory";

export default function NewChatButton() {
  const router = useRouter();
  const { createNew } = useChatHistory();

  const handleNewChat = () => {
    const session = createNew();
    router.push(`/chat/${session.id}`);
  };

  return (
    <button
      className="w-full rounded-lg px-4 py-2 border border-gray-300 hover:bg-gray-50 transition-colors font-medium text-sm flex items-center justify-center gap-2"
      onClick={handleNewChat}
    >
      <svg
        className="w-4 h-4"
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

