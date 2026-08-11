/**
 * useChatHistory.js
 * =================
 * Custom React hook to manage the conversation history and displayed messages
 * for the AI Chat component.
 */

import { useState, useCallback } from 'react';

/**
 * @typedef {Object} DisplayMessage
 * @property {'user'|'ai'} role
 * @property {string} text
 * @property {string} [source]  - Which AI/API answered (e.g. "sql", "css")
 * @property {boolean} [isError]
 */

/**
 * @typedef {Object} HistoryEntry
 * @property {'user'|'assistant'} role
 * @property {string} content
 */

const DEFAULT_GREETING = 'こんにちは！SQLやCSSに関する質問があれば何でも聞いてください。';

/**
 * useChatHistory – manage displayed messages and API-compatible history.
 *
 * @param {string} [initialGreeting] - The first assistant message shown to the user.
 * @returns {{
 *   messages: DisplayMessage[],
 *   chatHistory: HistoryEntry[],
 *   addUserMessage: (text: string) => void,
 *   addAIMessage: (text: string, source?: string) => void,
 *   addErrorMessage: (text?: string) => void,
 *   clearHistory: () => void,
 * }}
 */
export function useChatHistory(initialGreeting = DEFAULT_GREETING) {
  const [messages, setMessages] = useState([
    { role: 'ai', text: initialGreeting },
  ]);

  /** OpenAI-style history sent with each API request */
  const [chatHistory, setChatHistory] = useState([]);

  const addUserMessage = useCallback((text) => {
    setMessages((prev) => [...prev, { role: 'user', text }]);
  }, []);

  const addAIMessage = useCallback((text, source = '') => {
    setMessages((prev) => [...prev, { role: 'ai', text, source }]);
    setChatHistory((prev) => [
      ...prev,
      { role: 'assistant', content: text },
    ]);
  }, []);

  const addErrorMessage = useCallback((text = 'エラーが発生しました') => {
    setMessages((prev) => [...prev, { role: 'ai', text, isError: true }]);
  }, []);

  /**
   * Append the user message to the history *before* sending to the API
   * so the AI sees the full conversation turn.
   */
  const appendUserToHistory = useCallback((text) => {
    setChatHistory((prev) => [...prev, { role: 'user', content: text }]);
  }, []);

  const clearHistory = useCallback(() => {
    setMessages([{ role: 'ai', text: initialGreeting }]);
    setChatHistory([]);
  }, [initialGreeting]);

  return {
    messages,
    chatHistory,
    addUserMessage,
    addAIMessage,
    addErrorMessage,
    appendUserToHistory,
    clearHistory,
  };
}

export default useChatHistory;
