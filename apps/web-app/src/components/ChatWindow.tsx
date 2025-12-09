/**
 * Chat Window Component
 * Main chat interface with messages and input
 */

import { useEffect, useRef } from "react";
import { useChat } from "@/hooks/useChat";
import MessageBubble from "./MessageBubble";
import ChatInput from "./ChatInput";
import styles from "@/styles/ChatWindow.module.css";

interface ChatWindowProps {
  sessionId: string;
}

export default function ChatWindow({ sessionId }: ChatWindowProps) {
  const { messages, streamingMessage, isLoading, error, send, cancel, retry } =
    useChat(sessionId);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingMessage]);

  const handleSend = (content: string) => {
    send(content);
  };

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerInfo}>
          <h2>QuantumX AI</h2>
          <p>Ask anything – I can help with shopping, research, and more!</p>
          </div>
          
          {error && (
            <button
              onClick={retry}
            className={styles.retryButton}
            >
              Retry
            </button>
          )}
      </div>

      {/* Messages Area */}
      <div className={styles.messagesArea}>
        <div className={styles.messagesList}>
        {messages.length === 0 && !streamingMessage && (
            <div className={styles.emptyState}>
              <div className={styles.emptyLogo}>
                <span className={styles.emptyLogoText}>QX</span>
            </div>
              <h3 className={styles.emptyTitle}>
              Welcome to QuantumX AI
            </h3>
              <p className={styles.emptyDescription}>
              I&apos;m your smart AI assistant. I can help you with:
            </p>
              <div className={styles.emptyFeatures}>
                <div className={styles.emptyFeature}>
                  <div className={styles.emptyFeatureIcon}>🛍️</div>
                  <h4 className={styles.emptyFeatureTitle}>Smart Shopping</h4>
                  <p className={styles.emptyFeatureDesc}>
                  Compare prices, find deals, get recommendations
                </p>
              </div>
                <div className={styles.emptyFeature}>
                  <div className={styles.emptyFeatureIcon}>🔬</div>
                  <h4 className={styles.emptyFeatureTitle}>Deep Research</h4>
                  <p className={styles.emptyFeatureDesc}>
                  In-depth analysis, fact-checking, comprehensive reports
                </p>
              </div>
                <div className={styles.emptyFeature}>
                  <div className={styles.emptyFeatureIcon}>💬</div>
                  <h4 className={styles.emptyFeatureTitle}>Chat</h4>
                  <p className={styles.emptyFeatureDesc}>
                  General questions, quick answers, friendly conversation
                </p>
              </div>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {streamingMessage && (
          <MessageBubble
            message={{
              id: "streaming",
              role: "assistant",
              content: streamingMessage,
              timestamp: Date.now(),
            }}
            isStreaming
          />
        )}

        {error && (
            <div className={styles.errorMessage}>
              <svg
                className={styles.errorIcon}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <div className={styles.errorContent}>
                <h4>Error</h4>
                <p>{error}</p>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className={styles.inputArea}>
        <div className={styles.inputWrapper}>
        <ChatInput
          onSend={handleSend}
          onCancel={cancel}
          isLoading={isLoading}
          disabled={isLoading}
        />
        </div>
      </div>
    </div>
  );
}
