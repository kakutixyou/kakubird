// frontend/src/utils/renderSmartContent.jsx
import React from 'react';

export const renderSmartContent = (text) => {
  if (typeof text !== 'string') {
    return (
      <div className="text-red-400 text-sm">
        データ形式エラー: {String(text)}
      </div>
    );
  }

  // 
  // summary/details UI
  // 
  if (text.includes('<summary>') && text.includes('<details>')) {
    const summaryText = text.match(/<summary>([\s\S]*?)<\/summary>/)?.[1] || '結論';
    const detailsText = text.match(/<details>([\s\S]*?)<\/details>/)?.[1] || '';

    return (
      <div className="space-y-2">
        <div className="font-medium text-slate-800 dark:text-slate-200">
          {summaryText}
        </div>

        {detailsText && (
          <details className="group border border-slate-200 dark:border-slate-700 rounded-lg bg-slate-50 dark:bg-slate-900/50 p-2">
            <summary className="cursor-pointer text-xs font-semibold text-indigo-600 dark:text-indigo-400 select-none">
              <span className="group-open:hidden">▶ 詳細を見る</span>
              <span className="hidden group-open:inline">▼ 閉じる</span>
            </summary>
            <div className="mt-2 text-sm whitespace-pre-wrap text-slate-600 dark:text-slate-400 border-t border-slate-200 dark:border-slate-700 pt-2">
              {detailsText}
            </div>
          </details>
        )}
      </div>
    );
  }

  // 
  // Normal Text
  // 
  return (
    <div className="whitespace-pre-wrap">
      {text}
    </div>
  );
};