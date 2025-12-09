/**
 * Message Bubble Component
 * Displays a single chat message
 */

import type { Message } from "@/types/chat";
import styles from "@/styles/MessageBubble.module.css";

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
}

export default function MessageBubble({
  message,
  isStreaming = false,
}: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";

  return (
    <div className={`${styles.container} ${isUser ? styles.user : styles.assistant}`}>
      <div className={`${styles.bubble} ${isUser ? styles.user : styles.assistant}`}>
        {/* Content */}
        <div className={`${styles.content} prose`}>
          {message.content.split("\n").map((line, i) => (
            <p key={i}>
              {line || <br />}
            </p>
          ))}
        </div>

        {/* Streaming indicator */}
        {isStreaming && (
          <div className={styles.streamingIndicator}>
            <div className={styles.streamingDot} />
            <div className={styles.streamingDot} />
            <div className={styles.streamingDot} />
          </div>
        )}

        {/* Metadata - for Smart Buyer responses */}
        {isAssistant && message.metadata && (
          <div className={styles.metadata}>
            {/* Intent/Flow Type */}
            {(message.metadata.intent || message.metadata.flow_type) && (
              <div className={styles.flowType}>
                <span className={styles.flowIcon}>
                  {getFlowIcon(message.metadata.flow_type || message.metadata.intent)}
                </span>
                <span>
                  {formatFlowType(message.metadata.flow_type || message.metadata.intent)}
                </span>
              </div>
            )}

            {/* Top Recommendations */}
            {message.metadata.top_recommendations &&
              message.metadata.top_recommendations.length > 0 && (
                <div className={styles.recommendations}>
                  <div className={styles.recommendationsTitle}>
                    Top Recommendations:
                  </div>
                  {message.metadata.top_recommendations.slice(0, 3).map(
                    (rec: any, i: number) => (
                      <div
                        key={i}
                        className={styles.recommendationCard}
                      >
                        <div className={styles.recommendationRank}>
                          #{rec.rank ?? i + 1}{" "}
                          {typeof rec.score === "number"
                            ? `- Score: ${rec.score.toFixed(2)}`
                            : null}
                        </div>
                        {rec.product && (
                          <div className={styles.recommendationDetails}>
                            {rec.product.name}
                            {formatPrice(rec.product.price)}
                          </div>
                        )}
                      </div>
                    )
                  )}
                </div>
              )}
          </div>
        )}

        {/* Timestamp */}
        <div className={styles.timestamp}>
          {formatTime(message.timestamp)}
        </div>
      </div>
    </div>
  );
}

function formatTime(timestamp: number): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getFlowIcon(flowType: string): string {
  switch (flowType) {
    case "smart_buyer":
      return "🛍️";
    case "deep_research":
      return "🔬";
    case "code_agent":
      return "💻";
    default:
      return "💬";
  }
}

function formatFlowType(flowType: string): string {
  switch (flowType) {
    case "smart_buyer":
      return "Smart Buyer";
    case "deep_research":
      return "Deep Research";
    case "code_agent":
      return "Code Agent";
    case "chat":
      return "Chat";
    default:
      return flowType;
  }
}

function formatPrice(value?: number | string | null): string {
  if (value === undefined || value === null) return "";
  if (typeof value === "number" && !Number.isNaN(value)) {
    return ` - ${value.toLocaleString()} VND`;
  }
  if (typeof value === "string" && value.trim().length > 0) {
    return ` - ${value.trim()}`;
  }
  return "";
}
