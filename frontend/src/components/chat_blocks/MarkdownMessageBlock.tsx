// frontend/src/components/chat_blocks/MarkdownMessageBlock.tsx
import React from 'react';

export interface MarkdownMessageBlockProps {
  text: string;
}

export function MarkdownMessageBlock({
  text,
}: MarkdownMessageBlockProps): React.ReactElement {
  // <summary>...</summary> <details>...</details> 形式が含まれている場合は見やすく整形しつつ原文も保持
  const summaryMatch = text.match(/<summary>([\s\S]*?)<\/summary>/i);
  const detailsMatch = text.match(/<details>([\s\S]*?)<\/details>/i);

  if (summaryMatch && detailsMatch) {
    return (
      <div className="space-y-2">
        <div className="font-bold text-slate-900 dark:text-white">
          {summaryMatch[1].trim()}
        </div>
        <div className="text-xs text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-900/60 p-2.5 rounded-xl border border-slate-200/80 dark:border-slate-700/70">
          {detailsMatch[1].trim()}
        </div>
      </div>
    );
  }

  return <div className="whitespace-pre-wrap break-words">{text}</div>;
}

export default MarkdownMessageBlock;
