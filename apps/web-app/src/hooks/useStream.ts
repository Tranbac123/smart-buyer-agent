import { useState, useCallback, useRef } from 'react';

interface StreamOptions {
  onMessage: (chunk: string) => void;
  onComplete: () => void;
  onError: (error: Error) => void;
}

export function useStream() {
  const [isStreaming, setIsStreaming] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const startStream = useCallback(async (url: string, body: any, options: StreamOptions) => {
    setIsStreaming(true);
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('Response body is not readable');
      }

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          options.onComplete();
          break;
        }

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(line => line.trim() !== '');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
              options.onComplete();
              break;
            }
            try {
              const parsed = JSON.parse(data);
              options.onMessage(parsed.content || parsed.message || data);
            } catch {
              options.onMessage(data);
            }
          }
        }
      }
    } catch (error: any) {
      if (error.name !== 'AbortError') {
        options.onError(error);
      }
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  }, []);

  const stopStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
    }
  }, []);

  return {
    isStreaming,
    startStream,
    stopStream,
  };
}

