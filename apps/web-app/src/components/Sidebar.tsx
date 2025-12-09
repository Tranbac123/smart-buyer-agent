/**
 * Sidebar Component
 * Contains New Chat button and Chat List
 */

import NewChatButton from "./NewChatButton";
import ChatList from "./ChatList";
import { useChatHistory } from "@/hooks/useChatHistory";
import styles from "@/styles/Sidebar.module.css";

export default function Sidebar() {
  const { sessions, createNew, remove } = useChatHistory();

  return (
    <div className={styles.sidebar}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.branding}>
          <div className={styles.logo}>
            <span className={styles.logoText}>QX</span>
          </div>
          <div>
            <h1 className={styles.brandName}>QuantumX AI</h1>
            <p className={styles.brandTagline}>Smart AI Assistant</p>
          </div>
        </div>
        
        <NewChatButton onNewChat={createNew} />
      </div>

      {/* Chat List */}
      <div className={styles.chatList}>
        <ChatList sessions={sessions} onDelete={remove} />
      </div>

      {/* Footer */}
      <div className={styles.footer}>
        <div className={styles.status}>
          <div className={styles.statusIndicator}>
            <div className={styles.statusDot}></div>
            <span>All systems operational</span>
          </div>
          <div>Version 0.1.0</div>
        </div>
      </div>
    </div>
  );
}
