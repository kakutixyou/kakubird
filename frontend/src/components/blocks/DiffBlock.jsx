import React from 'react';

export default function DiffBlock({ block }) {
    const DiffBlock = ({ block }) => {
  const { title, diffs = [] } = block.props || {};
  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden bg-slate-50 dark:bg-slate-900 text-xs font-mono">
      {title && <div className="bg-slate-100 dark:bg-slate-800 px-3 py-1.5 border-b border-slate-200 dark:border-slate-700 font-sans font-medium text-slate-700 dark:text-slate-300">{title}</div>}
      <div className="divide-y divide-slate-100 dark:divide-slate-800 p-2 space-y-0.5">
        {diffs.map((line, idx) => {
          const isAdded = line.startsWith('+');
          const isRemoved = line.startsWith('-');
          return (
            <div key={idx} className={`px-2 py-0.5 rounded ${isAdded ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 font-bold' : isRemoved ? 'bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 line-through' : 'text-slate-600 dark:text-slate-400'}`}>
              {line}
            </div>
          );
        })}
      </div>
    </div>
  );
};
}