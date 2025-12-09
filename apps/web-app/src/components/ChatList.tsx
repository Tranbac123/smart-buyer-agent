/**
 * Chat List Component
 * Displays list of chat sessions
 */

import Link from "next/link";
import { useRouter } from "next/router";
import type { ChatSession } from "@/types/chat";
import styles from "@/styles/ChatList.module.css";

interface ChatListProps {
  sessions: ChatSession[];
  onDelete: (id: string) => void;
}

export default function ChatList({ sessions, onDelete }: ChatListProps) {
  const router = useRouter();
  const currentId = router.query.id as string;

  if (!sessions.length) {
    return (
      <div className={styles.empty}>
        No conversations yet
      </div>
    );
  }

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (confirm("Delete this conversation?")) {
      onDelete(id);
      
      // If deleting current chat, redirect to home
      if (currentId === id) {
        router.push("/");
      }
    }
  };

  return (
    <ul className={styles.list}>
      {sessions.map((session) => {
        const isActive = currentId === session.id;
        
        return (
          <li key={session.id} className={styles.item}>
            <Link
              href={`/chat/${session.id}`}
              className={`${styles.link} ${isActive ? styles.active : ''}`}
            >
              <div className={styles.content}>
                <div className={styles.title}>{session.title}</div>
                <div className={styles.timestamp}>
                  {formatDate(session.lastMessageAt || session.createdAt)}
                </div>
              </div>
              
              <button
                onClick={(e) => handleDelete(e, session.id)}
                className={styles.deleteButton}
                title="Delete conversation"
              >
                <svg
                  className={styles.deleteIcon}
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

