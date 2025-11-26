/**
 * Message Bubble Component
 * Displays a single chat message
 */

import type { Message } from "@/types/chat";

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
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`
          max-w-[80%] rounded-lg px-4 py-3
          ${
            isUser
              ? "bg-blue-600 text-white"
              : "bg-white border border-gray-200 text-gray-900"
          }
        `}
      >
        {/* Content */}
        <div className="prose prose-sm max-w-none">
          {message.content.split("\n").map((line, i) => (
            <p key={i} className={isUser ? "text-white" : "text-gray-900"}>
              {line || <br />}
            </p>
          ))}
        </div>

        {/* Streaming indicator */}
        {isStreaming && (
          <div className="flex gap-1 mt-2">
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
            <div
              className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
              style={{ animationDelay: "0.1s" }}
            />
            <div
              className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
              style={{ animationDelay: "0.2s" }}
            />
          </div>
        )}

        {/* Metadata - for Smart Buyer responses */}
        {isAssistant && message.metadata && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            {/* Intent/Flow Type */}
            {(message.metadata.intent || message.metadata.flow_type) && (
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-medium text-gray-500">
                  {getFlowIcon(message.metadata.flow_type || message.metadata.intent)}
                </span>
                <span className="text-xs text-gray-600">
                  {formatFlowType(message.metadata.flow_type || message.metadata.intent)}
                </span>
              </div>
            )}

            {/* Top Recommendations */}
            {message.metadata.top_recommendations &&
              message.metadata.top_recommendations.length > 0 && (
                <div className="mt-2 space-y-2">
                  <div className="text-xs font-semibold text-gray-700">
                    Top Recommendations:
                  </div>
                  {message.metadata.top_recommendations.slice(0, 3).map((rec: any, i: number) => (
                    <div
                      key={i}
                      className="bg-gray-50 rounded p-2 text-xs space-y-1"
                    >
                      <div className="font-medium">
                        #{rec.rank} - Score: {rec.score?.toFixed(2)}
                      </div>
                      {rec.product && (
                        <div className="text-gray-600">
                          {rec.product.name} - {rec.product.price?.toLocaleString()} VNĐ
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
          </div>
        )}

        {/* Timestamp */}
        <div
          className={`
            text-xs mt-2
            ${isUser ? "text-blue-100" : "text-gray-500"}
          `}
        >
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
