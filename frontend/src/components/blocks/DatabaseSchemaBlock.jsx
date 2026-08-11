// frontend/src/components/blocks/DatabaseSchemaBlock.jsx

import React from 'react';

export default function DatabaseSchemaBlock({ block }) {
  // 安全にprops取得
  const tables = block?.props?.tables || [];

  // テーブルが空の場合
  if (!tables.length) {
    return (
      <div className="text-sm text-slate-400 border border-dashed border-slate-300 dark:border-slate-700 rounded-lg p-4">
        テーブル情報がありません。
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {tables.map((table, tableIdx) => (
        <div
          key={table.name || tableIdx}
          className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-sm"
        >
          {/* ========================================= */}
          {/* Header */}
          {/* ========================================= */}
          <div className="border-b border-slate-200 dark:border-slate-700 px-4 py-3 bg-slate-50 dark:bg-slate-800/60">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-slate-800 dark:text-slate-100">
                  {table.label || table.name}
                </h3>

                {table.name && (
                  <p className="text-xs text-slate-500 dark:text-slate-400 font-mono mt-1">
                    {table.name}
                  </p>
                )}
              </div>

              {/* カラム数 */}
              <div className="text-[11px] px-2 py-1 rounded-full bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300 font-semibold">
                {table.columns?.length || 0} columns
              </div>
            </div>

            {/* テーブル説明 */}
            {table.description && (
              <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">
                {table.description}
              </p>
            )}
          </div>

          {/* ========================================= */}
          {/* Table */}
          {/* ========================================= */}
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead className="bg-slate-100 dark:bg-slate-800">
                <tr>
                  <th className="text-left px-4 py-3 font-semibold text-slate-700 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700">
                    カラム
                  </th>

                  <th className="text-left px-4 py-3 font-semibold text-slate-700 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700">
                    型
                  </th>

                  <th className="text-left px-4 py-3 font-semibold text-slate-700 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700">
                    説明
                  </th>
                </tr>
              </thead>

              <tbody>
                {table.columns?.map((col, colIdx) => (
                  <tr
                    key={col.name || colIdx}
                    className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors"
                  >
                    {/* Column Name */}
                    <td className="px-4 py-3 border-b border-slate-100 dark:border-slate-800">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-indigo-600 dark:text-indigo-400 font-semibold">
                          {col.name}
                        </span>

                        {/* Primary Key */}
                        {String(col.type || '')
                          .toUpperCase()
                          .includes('PRIMARY KEY') && (
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300 font-bold">
                            PK
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Type */}
                    <td className="px-4 py-3 border-b border-slate-100 dark:border-slate-800">
                      <span className="font-mono text-xs text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded">
                        {col.type || '-'}
                      </span>
                    </td>

                    {/* Description */}
                    <td className="px-4 py-3 border-b border-slate-100 dark:border-slate-800 text-slate-600 dark:text-slate-400">
                      {col.description || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* ========================================= */}
          {/* Footer */}
          {/* ========================================= */}
          <div className="px-4 py-2 text-[11px] text-slate-400 border-t border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/40">
            Database Schema Viewer
          </div>
        </div>
      ))}
    </div>
  );
}