// frontend/src/components/blocks/MarkdownChatBlock.jsx
import React from 'react';

/**
 * AIからの通常テキスト（Markdown）を表示するブロック
 * @param {string} text - AIから渡されるメインのテキスト
 */
export default function MarkdownChatBlock({ text }) {
  if (!text) return null;

  return (
    <div className="w-full text-slate-800 dark:text-slate-200 leading-relaxed space-y-2 text-sm md:text-base">
      {/* 簡易的に改行を反映させるための whitespace-pre-wrap 
        ※将来的に本格的なMarkdown表示にする場合は、<ReactMarkdown>{text}</ReactMarkdown> に差し替えます
      */}
      <div className="whitespace-pre-wrap break-words">
        {text}
      </div>
    </div>
  );
}