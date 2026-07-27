import React from 'react';

/**
 * チャットの吹き出し用UIコンポーネント
 */
export function ChatBubble({ role, children }) {
  const isUser = role === 'user';
  const isSystem = role === 'system';

  // ユーザー、システム、AIでスタイルを出し分ける
  let baseStyle = "max-w-[90%] rounded-2xl px-4 py-3 text-sm shadow-sm ";
  
  if (isUser) {
    baseStyle += "bg-indigo-600 text-white rounded-br-none";
  } else if (isSystem) {
    baseStyle += "bg-slate-100 dark:bg-slate-800 text-slate-500 font-mono text-xs w-full text-center rounded-lg border border-slate-200 dark:border-slate-700";
  } else {
    baseStyle += "bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded-bl-none border border-slate-100 dark:border-slate-700/60";
  }

  return (
    <div className={baseStyle}>
      {children}
    </div>
  );
}

/**
 * 吹き出しの上のラベル（You, AI Engineerなど）
 */
export function ChatLabel({ role }) {
  const labelText = role === 'user' ? 'You' : role === 'system' ? 'System' : 'AI Engineer';
  const isUser = role === 'user';

  return (
    <span className={`text-[10px] font-semibold text-slate-400 px-1 mb-1 uppercase tracking-wider ${isUser ? 'self-end' : 'self-start'}`}>
      {labelText}
    </span>
  );
}