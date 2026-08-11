/**
 * AIChatPanel.jsx
 * ===============
 * Main AI Chat component.
 *
 * Features:
 *  - Sends user messages to the appropriate API (SQL or CSS) automatically
 *  - Detects programming language / styling framework from user input
 *  - Maintains conversation history for multi-turn context
 *  - Displays which API answered (SQL API / CSS API)
 *
 * Console log legend:
 *  🔵  Front-end send / receive
 *  🟡  Language detection
 *  🔴  Errors / warnings
 *
 * Usage:
 * ```jsx
 * import { AIChatPanel } from '@my-awesome-builder/ai-chat-component';
 *
 * <AIChatPanel
 *   dbPath="/path/to/database.db"
 *   greeting="Hello! Ask me anything about SQL or CSS."
 * />
 * ```
 */

import React, { useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage.jsx';
import useChatHistory from '../hooks/useChatHistory.js';
import useAPIRouter from '../hooks/useAPIRouter.js';
import useLanguageDetection from '../hooks/useLanguageDetection.js';

/**
 * @param {object}  props
 * @param {string}  [props.dbPath='']           - SQLite DB path forwarded to the SQL API
 * @param {string}  [props.greeting]            - Override the initial greeting message
 * @param {object}  [props.endpointOverrides]   - Override specific API endpoints at runtime
 * @param {string}  [props.className='']        - Extra CSS class for the outer wrapper
 * @param {string}  [props.placeholder]         - Input placeholder text
 * @param {boolean} [props.showRoutingBadge]    - Show which API will be used as user types
 */
function AIChatPanel({
  dbPath = '',
  greeting,
  endpointOverrides = {},
  className = '',
  placeholder = 'SQLやCSSについて質問してください…',
  showRoutingBadge = true,
}) {
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const {
    messages,
    chatHistory,
    addUserMessage,
    addAIMessage,
    addErrorMessage,
    appendUserToHistory,
    clearHistory,
  } = useChatHistory(greeting);

  const { isLoading, send, previewRoute } = useAPIRouter({ dbPath, endpointOverrides });

  const { detect: detectLang, reset: resetLang } = useLanguageDetection();

  const [inputText, setInputText] = React.useState('');

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleInputChange = (e) => {
    const val = e.target.value;
    setInputText(val);
    if (showRoutingBadge) {
      if (val.trim()) {
        detectLang(val);
      } else {
        resetLang();
      }
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    const text = inputText.trim();
    if (!text || isLoading) return;

    const sendTimestamp = new Date().toISOString();
    const { intent: routeIntent, language: routeLang, confidence: routeConf } = previewRoute(text);

    // ── 1️⃣ Front-end: user sends message ─────────────────────────────────
    console.info(
      '%c🔵 [フロント - 1️⃣] ユーザーが質問を送信',
      'color: #3b82f6; font-weight: bold',
    );
    console.info('   📝 Message          :', text);
    console.info('   🌍 Detected Language:', routeLang);
    console.info('   📊 Confidence       :', `${(routeConf * 100).toFixed(0)}%`);
    console.info('   🛣️  Route Intent     :', routeIntent);
    console.info('   ⏱️  Timestamp        :', sendTimestamp);
    console.info('   📜 History turns    :', chatHistory.length);

    setInputText('');
    resetLang();
    addUserMessage(text);
    appendUserToHistory(text);

    try {
      const result = await send(text, chatHistory);
      const receiveTimestamp = new Date().toISOString();
      const totalMs = Date.now() - new Date(sendTimestamp).getTime();

      // ── 5️⃣ Front-end: response received ──────────────────────────────
      console.info(
        '%c🔵 [フロント - 5️⃣] レスポンス受信',
        'color: #3b82f6; font-weight: bold',
      );
      console.info('   ✅ Status           : 200 OK');
      console.info('   📦 Response Type    :', result.source ?? result.intent);
      console.info('   🌍 Language         :', result.language ?? routeLang);
      console.info('   💬 Reply            :', result.reply?.slice(0, 120));
      console.info('   ⏱️  Total time       :', `${totalMs}ms`);
      console.info('   🕐 Received at      :', receiveTimestamp);

      addAIMessage(result.reply, result.source);
      console.info('   ✅ メッセージ追加完了');
    } catch (error) {
      console.error(
        '%c🔴 [フロント] エラー発生',
        'color: #ef4444; font-weight: bold',
        error,
      );
      addErrorMessage('エラーが発生しました。もう一度お試しください。');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      handleSendMessage(e);
    }
  };

  // Preview badge: what API would be called for current input
  const { intent: previewIntent } = previewRoute(inputText);
  const routeBadgeLabel =
    previewIntent === 'sql' ? 'SQL API'
    : previewIntent === 'css' ? 'CSS API'
    : null;

  return (
    <div className={`ai-chat ${className}`} role="region" aria-label="AI Chat Panel">
      {/* Header */}
      <div className="ai-chat__header">
        <span className="ai-chat__header-icon" aria-hidden="true">🤖</span>
        <span className="ai-chat__header-title">AI Assistant</span>
        <button
          type="button"
          className="ai-chat__clear-btn"
          onClick={clearHistory}
          aria-label="チャット履歴をクリア"
          title="チャット履歴をクリア"
        >
          🗑️
        </button>
      </div>

      {/* Message list */}
      <div className="ai-chat__messages" aria-live="polite" aria-label="会話メッセージ">
        {messages.map((msg, idx) => (
          <ChatMessage
            key={idx}
            role={msg.role}
            text={msg.text}
            source={msg.source}
            isError={msg.isError}
          />
        ))}
        {isLoading && (
          <div className="ai-chat__loading" aria-label="AIが応答中">
            <span className="ai-chat__loading-dot" />
            <span className="ai-chat__loading-dot" />
            <span className="ai-chat__loading-dot" />
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <form className="ai-chat__form" onSubmit={handleSendMessage} noValidate>
        {showRoutingBadge && routeBadgeLabel && inputText.trim() && (
          <div className="ai-chat__route-preview" aria-live="polite">
            <span className="ai-chat__route-preview-label">送信先:</span>
            <span className="ai-chat__route-preview-badge">{routeBadgeLabel}</span>
          </div>
        )}
        <div className="ai-chat__input-row">
          <textarea
            ref={inputRef}
            className="ai-chat__input"
            value={inputText}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            rows={2}
            disabled={isLoading}
            aria-label="メッセージを入力"
          />
          <button
            type="submit"
            className="ai-chat__send-btn"
            disabled={!inputText.trim() || isLoading}
            aria-label="送信"
          >
            {isLoading ? '⏳' : '➤'}
          </button>
        </div>
        <p className="ai-chat__hint">
          Shift+Enter で改行 / Enter で送信
        </p>
      </form>
    </div>
  );
}

export default AIChatPanel;
