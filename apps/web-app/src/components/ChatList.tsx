/**
 * Chat List Component
 * Displays list of chat sessions
 */

import Link from "next/link";
import { useRouter } from "next/router";
import { useChatHistory } from "@/hooks/useChatHistory";

export default function ChatList() {
  const { sessions, remove } = useChatHistory();
  const router = useRouter();
  const currentId = router.query.id as string;

  if (!sessions.length) {
    return (
      <div className="text-sm text-gray-500 text-center py-4">
        No conversations yet
      </div>
    );
  }

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (confirm("Delete this conversation?")) {
      remove(id);
      
      // If deleting current chat, redirect to home
      if (currentId === id) {
        router.push("/");
      }
    }
  };

  return (
    <ul className="space-y-1">
      {sessions.map((session) => {
        const isActive = currentId === session.id;
        
        return (
          <li key={session.id}>
            <Link
              href={`/chat/${session.id}`}
              className={`
                group flex items-center justify-between px-3 py-2 rounded-lg
                transition-colors text-sm
                ${
                  isActive
                    ? "bg-blue-50 text-blue-700"
                    : "hover:bg-gray-100 text-gray-700"
                }
              `}
            >
              <div className="flex-1 truncate">
                <div className="font-medium truncate">{session.title}</div>
                <div className="text-xs text-gray-500">
                  {formatDate(session.lastMessageAt || session.createdAt)}
                </div>
              </div>
              
              <button
                onClick={(e) => handleDelete(e, session.id)}
                className="opacity-0 group-hover:opacity-100 ml-2 p-1 hover:bg-red-50 hover:text-red-600 rounded transition-all"
                title="Delete conversation"
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
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </button>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

function formatDate(timestamp: number): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  
  return date.toLocaleDateString();
}

