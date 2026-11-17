// frontend/src/components/AiChatMessageList.tsx
import React, { useState } from 'react';
import { BlockDispatcher, MessageActionToolbar } from './chat_blocks';
import GradingResultWidget, { GradingSessionData } from './widgets/GradingResultWidget';

export interface AiChatMessageListProps {
  messages?: any[];
  isLoading?: boolean;
  onOptionSelect?: (selectedOptions: unknown) => void;
  onOpenManualEdit?: (block: unknown) => void;
  onInsertCode?: (codeSnippet: string) => void;
  apiBaseUrl?: string;
}

const DEFAULT_WELCOME_TEXT =
  '<summary>アプリ開発AIとしてスタンバイしました！</summary> <details>AIモードを標準にして、チャットボットモードへも切り替えられます。</details>';

const DEFAULT_API_BASE_URL: string = String(
  (import.meta as any).env?.VITE_API_BASE_URL || 'http://127.0.0.1:8765'
).replace(/\/+$/, '');

function isGradingMessage(msg: any): boolean {
  if (!msg || typeof msg !== 'object') return false;
  return (
    msg.type === 'grading_result' ||
    msg.response_type === 'grading_result' ||
    msg.handler === 'GradingHandler' ||
    msg?.metadata?.type === 'grading_result' ||
    msg?.content?.response_type === 'grading_result' ||
    Array.isArray(msg?.content?.submissions) ||
    Array.isArray(msg?.data?.submissions)
  );
}

function extractGradingPayload(msg: any): Partial<GradingSessionData> | undefined {
  if (!msg || typeof msg !== 'object') return undefined;
  if (msg.content && typeof msg.content === 'object') {
    if (Array.isArray(msg.content.submissions)) {
      return msg.content as Partial<GradingSessionData>;
    }
    if (msg.content.content && typeof msg.content.content === 'object') {
      return msg.content.content as Partial<GradingSessionData>;
    }
  }
  if (msg.data && typeof msg.data === 'object' && Array.isArray(msg.data.submissions)) {
    return msg.data as Partial<GradingSessionData>;
  }
  return undefined;
}

/**
 * AiChatMessageList:
 * 各種 Handler (ChatHandler, OcrRecruitHandler, StockHandler, GameSimHandler, GradingHandler 等) および
 * tools/ フォルダー (math, sql, search, filesystem, blender, unity, grading 等) の応答を受け付け、
 * 実際のブロック描画とツールバーは `./chat_blocks/` 配下のサブモジュールへ委譲します。
 * 採点支援 (`grading_result`) の場合は `BlockDispatcher` を書き換えずに直接 `GradingResultWidget` を描画します。
 */
export default function AiChatMessageList({
  messages = [],
  isLoading = false,
  onOptionSelect,
  onOpenManualEdit,
  onInsertCode,
  apiBaseUrl = DEFAULT_API_BASE_URL,
}: AiChatMessageListProps): React.ReactElement {
  const [likedIds, setLikedIds] = useState<Record<string, boolean>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const displayMessages =
    Array.isArray(messages) && messages.length > 0
      ? messages
      : [
          {
            id: 'welcome-msg',
            role: 'assistant',
            sender: 'AI ENGINEER',
            content: DEFAULT_WELCOME_TEXT,
          },
        ];

  const handleCopy = (id: string, text: string) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).catch(() => {});
    }
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1800);
  };

  const handleLike = async (id: string, text: string) => {
    setLikedIds((prev) => ({ ...prev, [id]: true }));
    try {
      await fetch(`${apiBaseUrl}/api/to/ratings/like`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, source: 'user_like' }),
      });
    } catch {}
  };

  return (
    <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4 bg-white dark:bg-slate-900">
      {displayMessages.map((msg: any, index: number) => {
        const msgId = String(msg.id || `msg-${index}`);
        const isUser = msg.role === 'user' || msg.sender === 'user';
        const rawText =
          typeof msg.content === 'string'
            ? msg.content
            : typeof msg.content?.message === 'string'
            ? msg.content.message
            : typeof msg.message === 'string'
            ? msg.message
            : typeof msg.text === 'string'
            ? msg.text
            : JSON.stringify(msg.content || msg.text || '');

        const handlerName = msg?.handler || msg?.metadata?.handler;
        const toolCategory = msg?.tool || msg?.metadata?.tool;
        const isGrading = !isUser && isGradingMessage(msg);

        return (
          <div
            key={msgId}
            className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
          >
            <span className="text-[11px] font-bold tracking-wider uppercase text-slate-400 mb-1">
              {isUser ? 'YOU' : msg.sender || 'AI ENGINEER'}
            </span>

            <div
              className={`${
                isGrading ? 'w-full max-w-[98%]' : 'max-w-[92%]'
              } rounded-2xl border px-4 py-3 text-sm leading-relaxed shadow-sm ${
                isUser
                  ? 'bg-blue-600 text-white border-blue-500'
                  : 'bg-white text-slate-800 border-slate-200 dark:bg-slate-800 dark:text-slate-100 dark:border-slate-700'
              }`}
            >
              {isGrading ? (
                <div className="space-y-3">
                  {typeof msg.message === 'string' && msg.message && (
                    <div className="text-sm text-slate-700 dark:text-slate-200">
                      {msg.message}
                    </div>
                  )}
                  <GradingResultWidget
                    initialData={extractGradingPayload(msg)}
                    apiBaseUrl={apiBaseUrl}
                    onOptionSelect={onOptionSelect as any}
                  />
                </div>
              ) : (
                <BlockDispatcher
                  msg={msg}
                  rawText={rawText}
                  onOptionSelect={onOptionSelect}
                  onOpenManualEdit={onOpenManualEdit}
                  onInsertCode={onInsertCode}
                />
              )}

              {!isUser && (
                <MessageActionToolbar
                  msgId={msgId}
                  rawText={rawText}
                  isLiked={!!likedIds[msgId]}
                  isCopied={copiedId === msgId}
                  handlerName={handlerName || (isGrading ? 'GradingHandler' : undefined)}
                  toolCategory={toolCategory || (isGrading ? 'grading' : undefined)}
                  onCopy={handleCopy}
                  onLike={handleLike}
                  onOptionSelect={onOptionSelect}
                />
              )}
            </div>
          </div>
        );
      })}

      {isLoading && (
        <div className="text-xs text-slate-400 animate-pulse px-2">
          🤖 AIが応答を生成中...
        </div>
      )}
    </div>
  );
}