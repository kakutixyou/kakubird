import React from 'react';

export default function FileDownloadBlock({ block }) {
  const { title, filename, fileType, size, url } = block.props || {};

  return (
    <div className="w-full max-w-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start gap-4">
        {/* アイコン部分 */}
        <div className="flex-shrink-0 w-12 h-12 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-lg flex items-center justify-center text-2xl">
          {fileType === 'db' ? '🗄️' : fileType === 'json' ? '｛' : '📄'}
        </div>
        
        {/* テキスト部分 */}
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-bold text-slate-800 dark:text-slate-200 truncate">
            {title || 'ファイルダウンロード'}
          </h4>
          <p className="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5">
            {filename} <span className="mx-1">•</span> {size}
          </p>
        </div>
      </div>

      {/* ダウンロードボタン */}
      <a
        href={url}
        download={filename}
        className="mt-4 w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors active:scale-95"
      >
        <span>⬇️</span> ダウンロードを実行
      </a>
    </div>
  );
}