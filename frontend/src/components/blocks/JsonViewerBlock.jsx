// frontend/src/components/blocks/JsonViewerBlock.jsx
import React from 'react';

export default function JsonViewerBlock({ block }) {
  const { title, data } = block.props || {};
  const jsonString = typeof data === 'object' ? JSON.stringify(data, null, 2) : data;
  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden bg-slate-950 text-slate-200 text-xs font-mono">
      <div className="bg-slate-900 px-3 py-1.5 border-b border-slate-800 flex justify-between items-center">
        <span className="font-sans font-medium text-slate-400">{title || "JSON Viewer"}</span>
        <button 
          onClick={() => navigator.clipboard.writeText(jsonString)} 
          className="font-sans px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded transition-all text-[10px]"
        >
          コピー
        </button>
      </div>
      <pre className="p-3 overflow-x-auto max-h-60 whitespace-pre-wrap select-all">{jsonString}</pre>
    </div>
  );
};
