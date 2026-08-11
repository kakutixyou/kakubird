// To/frontend/src/components/blocks/ChatActionBlock.jsx
import React from 'react';

export default function ChatActionBlock({ block, onOptionSelect }) {
  const { title = "次のアクションを選択肢から実行できます：", actions = [] } = block?.props || {};
  
  return (
    <div className="bg-indigo-50/50 dark:bg-slate-900/60 border border-indigo-100 dark:border-slate-800 p-3 rounded-xl space-y-2">
      <p className="text-xs font-medium text-slate-700 dark:text-slate-300">{title}</p>
      <div className="flex flex-wrap gap-2">
        {actions.map((act, idx) => (
          <button
            key={idx}
            onClick={() => onOptionSelect && onOptionSelect({ value: act.next_prompt || act.label, label: act.label })}
            className="text-xs bg-white dark:bg-slate-800 hover:bg-indigo-600 dark:hover:bg-indigo-600 border border-slate-200 dark:border-slate-700 hover:border-indigo-600 text-slate-700 dark:text-slate-300 hover:text-white px-3 py-1.5 rounded-lg font-medium shadow-sm transition-all active:scale-95 flex items-center gap-1.5"
          >
            <span>{act.icon || "⚙️"}</span>
            {act.label}
          </button>
        ))}
      </div>
    </div>
  );
}