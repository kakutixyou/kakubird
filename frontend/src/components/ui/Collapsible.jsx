import React from 'react';

/**
 * <summary>と<details>を使ったアコーディオンUI
 */
export function Collapsible({ summaryText, detailsText }) {
  return (
    <div className="space-y-2">
      <div className="font-medium text-slate-800 dark:text-slate-200">
        {summaryText}
      </div>
      <details className="group border border-slate-200 dark:border-slate-700 rounded-lg bg-slate-50 dark:bg-slate-900/50 p-2">
        <summary className="cursor-pointer text-xs font-semibold text-indigo-600 dark:text-indigo-400 select-none">
          <span className="group-open:hidden">▶ 詳細を見る</span>
          <span className="hidden group-open:inline">▼ 閉じる</span>
        </summary>
        <div className="mt-2 text-sm whitespace-pre-wrap text-slate-600 dark:text-slate-400 border-t border-slate-200 dark:border-slate-700 pt-2">
          {detailsText}
        </div>
      </details>
    </div>
  );
}