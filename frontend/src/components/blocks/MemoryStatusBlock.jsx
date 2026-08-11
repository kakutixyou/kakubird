// frontend/src/components/blocks/MemoryStatusBlock.jsx
import React from 'react';

export default function MemoryStatusBlock({ block }) {
  // バックエンドから渡された props を展開
  const { data, title } = block.props || {};

  if (!data) return null;

  return (
    <div className="w-full bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-lg p-4 font-sans">
      <div className="flex items-center gap-2 mb-3 border-b border-indigo-100 dark:border-indigo-800 pb-2">
        <span className="text-xl">🧠</span>
        <h3 className="font-bold text-indigo-700 dark:text-indigo-300">
          {title || '記憶データベース更新完了'}
        </h3>
      </div>

      <div className="space-y-2 text-sm text-slate-700 dark:text-slate-300">
        <div className="flex justify-between">
          <span className="font-semibold">学習ソース:</span>
          <a 
            href={data.source_url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-blue-500 hover:underline truncate ml-2 max-w-[200px]"
          >
            {data.source_url}
          </a>
        </div>

        <div className="flex justify-between">
          <span className="font-semibold">新規チャンク数:</span>
          <span className="bg-indigo-100 dark:bg-indigo-800 px-2 py-0.5 rounded text-indigo-800 dark:text-indigo-200">
            +{data.new_chunks_saved} pieces
          </span>
        </div>

        <div className="flex justify-between">
          <span className="font-semibold">現在の総記憶量:</span>
          <span>{data.total_chunks_in_memory} pieces</span>
        </div>
      </div>

      {/* 記憶した内容のプレビュー */}
      <div className="mt-4">
        <span className="text-xs text-slate-500 dark:text-slate-400 mb-1 block">
          記憶データの断片プレビュー:
        </span>
        <div className="bg-slate-900 text-green-400 font-mono text-xs p-3 rounded-md overflow-x-auto max-h-32 overflow-y-auto">
          {data.sample_chunk_preview}
        </div>
      </div>
    </div>
  );
}