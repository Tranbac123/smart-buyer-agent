/**
 * Chat Window Component
 * Main chat interface with messages and input
 */

import { useEffect, useRef } from "react";
import { useChat } from "@/hooks/useChat";
import MessageBubble from "./MessageBubble";
import ChatInput from "./ChatInput";

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
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Chat</h2>
            <p className="text-sm text-gray-500">
              Ask anything - I can help with shopping, research, and more!
            </p>
          </div>
          
          {error && (
            <button
              onClick={retry}
              className="text-sm text-red-600 hover:text-red-700 font-medium"
            >
              Retry
            </button>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4 bg-gray-50">
        {messages.length === 0 && !streamingMessage && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mb-4">
              <span className="text-white font-bold text-2xl">QX</span>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              Welcome to QuantumX AI
            </h3>
            <p className="text-gray-600 max-w-md">
              I'm your smart AI assistant. I can help you with:
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6 max-w-3xl">
              <div className="bg-white p-4 rounded-lg border border-gray-200">
                <div className="text-2xl mb-2">🛍️</div>
                <h4 className="font-semibold mb-1">Smart Shopping</h4>
                <p className="text-sm text-gray-600">
                  Compare prices, find deals, get recommendations
                </p>
              </div>
              <div className="bg-white p-4 rounded-lg border border-gray-200">
                <div className="text-2xl mb-2">🔬</div>
                <h4 className="font-semibold mb-1">Deep Research</h4>
                <p className="text-sm text-gray-600">
                  In-depth analysis, fact-checking, comprehensive reports
                </p>
              </div>
              <div className="bg-white p-4 rounded-lg border border-gray-200">
                <div className="text-2xl mb-2">💬</div>
                <h4 className="font-semibold mb-1">Chat</h4>
                <p className="text-sm text-gray-600">
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
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <svg
                className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5"
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
              <div>
                <h4 className="font-semibold text-red-900">Error</h4>
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 bg-white px-6 py-4">
        <ChatInput
          onSend={handleSend}
          onCancel={cancel}
          isLoading={isLoading}
          disabled={isLoading}
        />
      </div>
    </div>
  );
}
