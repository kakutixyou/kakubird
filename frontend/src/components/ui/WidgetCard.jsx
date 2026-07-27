import React from 'react';

/**
 * GitHub検索結果やUIブロックを囲うための、枠線付きのカードUI
 */
export function WidgetCard({ icon, title, children }) {
  return (
    <div className="flex flex-col items-start w-full my-2">
      <span className="text-[10px] font-semibold text-indigo-400 px-1 mb-1 uppercase tracking-wider flex items-center gap-1">
        <span>{icon}</span>
        {title}
      </span>
      <div className="w-full bg-white dark:bg-slate-800 border-2 border-indigo-100 dark:border-indigo-900/50 rounded-xl p-4 shadow-sm space-y-4">
        {children}
      </div>
    </div>
  );
}