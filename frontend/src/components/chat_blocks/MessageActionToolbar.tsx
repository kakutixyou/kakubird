// frontend/src/components/chat_blocks/MessageActionToolbar.tsx
import React from 'react';

export interface MessageActionToolbarProps {
  msgId: string;
  rawText: string;
  isLiked: boolean;
  isCopied: boolean;
  handlerName?: string;
  toolCategory?: string;
  onCopy: (id: string, text: string) => void;
  onLike: (id: string, text: string) => void;
  onOptionSelect?: (payload: unknown) => void;
}

export function MessageActionToolbar({
  msgId,
  rawText,
  isLiked,
  isCopied,
  handlerName,
  toolCategory,
  onCopy,
  onLike,
  onOptionSelect,
}: MessageActionToolbarProps): React.ReactElement {
  return (
    <div className="mt-3 pt-2 border-t border-slate-100 dark:border-slate-700/80 space-y-1.5 text-xs text-slate-500 dark:text-slate-400">
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => onCopy(msgId, rawText)}
          className="hover:text-blue-600 dark:hover:text-blue-400 flex items-center gap-1 transition"
        >
          <span>📋</span>
          <span>{isCopied ? 'コピー済' : 'コピー'}</span>
        </button>

        <button
          type="button"
          onClick={() => onLike(msgId, rawText)}
          className={`flex items-center gap-1 transition ${
            isLiked ? 'text-amber-500 font-bold' : 'hover:text-amber-500'
          }`}
        >
          <span>👍</span>
          {isLiked && <span>済</span>}
        </button>

        <button
          type="button"
          onClick={() =>
            onOptionSelect?.({ action: 'send_chat', text: '高評価リスト見せて' })
          }
          className="hover:text-amber-600 dark:hover:text-amber-300 flex items-center gap-1 transition"
        >
          <span>⭐</span>
          <span>高評価リスト</span>
        </button>

        <button
          type="button"
          onClick={() =>
            onOptionSelect?.({ action: 'send_chat', text: '進捗解析 (Dev)' })
          }
          className="hover:text-indigo-600 dark:hover:text-indigo-300 flex items-center gap-1 transition"
        >
          <span>📊</span>
          <span>進捗解析 (Dev)</span>
        </button>

        {(handlerName || toolCategory) && (
          <span className="ml-auto text-[10px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400">
            {handlerName ? `Handler: ${handlerName}` : `Tool: ${toolCategory}`}
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-400">
        <button
          type="button"
          onClick={() =>
            onOptionSelect?.({ action: 'send_chat', text: 'Dev Actions' })
          }
          className="hover:text-slate-600 dark:hover:text-slate-200 transition"
        >
          🛠️ Dev Actions / 🎓 ポイント
        </button>
        <span>・</span>
        <button
          type="button"
          onClick={() =>
            onOptionSelect?.({ action: 'send_chat', text: '定期購入の管理を開いて' })
          }
          className="text-amber-600 dark:text-amber-400 hover:underline font-semibold"
        >
          💳 定期購入の管理 (1円サブスク・ガチャ券10枚)
        </button>
      </div>
    </div>
  );
}

export default MessageActionToolbar;
