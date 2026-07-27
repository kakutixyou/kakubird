// To/frontend/src/components/blocks/SqlPreviewBlock.jsx
import React from 'react';

export default function SqlPreviewBlock({ block }) {
      const { source, raw_data, sql } = block.props || {};
      const codeToDisplay = sql || raw_data || "-- No SQL Provided";
      return (
        <div className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden bg-slate-900 text-indigo-200 text-xs font-mono">
          <div className="bg-slate-850 px-3 py-1.5 border-b border-slate-800 flex justify-between items-center text-slate-400 font-sans">
               <span>📄 {source || "generated_schema.sql"}</span>
            <button 
              onClick={() => navigator.clipboard.writeText(codeToDisplay)} 
              className="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[10px]">
              SQLコピー
            </button>
          </div>
          <pre className="p-3 overflow-x-auto text-emerald-400 dark:text-emerald-300 bg-slate-950 whitespace-pre">{codeToDisplay}</pre>
        </div>
      );
    };
