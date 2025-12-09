/**
 * Chat Input Component
 * Text input with send button
 */

import { useState, useRef, KeyboardEvent } from "react";
import styles from "@/styles/ChatInput.module.css";

interface ChatInputProps {
  onSend: (message: string) => void;
  onCancel?: () => void;
  isLoading?: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export default function ChatInput({
  onSend,
  onCancel,
  isLoading = false,
  disabled = false,
  placeholder = "Ask anything – I can help with shopping, research, and more!",
}: ChatInputProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (!input.trim() || disabled) return;
    
    onSend(input.trim());
    setInput("");
    
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    
    // Auto-resize textarea
    const textarea = e.target;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
  };

  return (
    <div className={styles.container}>
      <div className={styles.inputWrapper}>
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className={styles.textarea}
        />
        
        {isLoading && onCancel && (
          <button
            onClick={onCancel}
            className={styles.cancelButton}
            title="Cancel"
          >
            <svg
              className={styles.cancelIcon}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        )}
      </div>

      <button
        onClick={handleSend}
        disabled={disabled || !input.trim()}
        className={styles.sendButton}
      >
        {isLoading ? (
          <>
            <div className={styles.spinner}></div>
            <span>Sending...</span>
          </>
        ) : (
          <>
            <span>Send</span>
            <svg
              className={styles.sendIcon}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
              />
            </svg>
          </>
        )}
      </button>
    </div>
  );
}

