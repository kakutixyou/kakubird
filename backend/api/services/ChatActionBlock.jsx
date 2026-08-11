
import React from 'react';

export default function ChatActionBlock({ block, onOptionSelect }) {
  const { title = "次のアクション:", actions = [] } = block.props || {};

  if (!actions || actions.length === 0) return null;

  return (
    <div className="mt-2 w-full">
      <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2 ml-1">
        {title}
      </p>
      <div className="flex flex-wrap gap-2">
        {actions.map((act, idx) => (
          <button
            key={idx}
            onClick={() => {
              if (onOptionSelect) {
                // next_promptがあればそれを、なければlabelをチャット送信
                onOptionSelect({
                  value: act.next_prompt || act.label,
                  label: act.label
                });
              }
            }}
            className="group flex items-center gap-2 bg-white dark:bg-slate-800 border border-indigo-200 dark:border-indigo-900/50 hover:border-indigo-500 dark:hover:border-indigo-400 text-slate-700 dark:text-slate-300 px-4 py-2 rounded-full text-sm font-medium shadow-sm transition-all hover:shadow hover:-translate-y-0.5 active:translate-y-0 active:scale-95"
          >
            <span className="opacity-80 group-hover:opacity-100 transition-opacity">
              {act.icon || "✨"}
            </span>
            {act.label}
          </button>
        ))}
      </div>
    </div>
  );
}