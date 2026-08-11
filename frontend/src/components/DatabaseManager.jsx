// To/frontend/src/components/DatabaseManager.tsx
import React, { useEffect } from 'react';
import { useDatabases } from '../hooks/useDatabases';

export default function DatabaseManager() {
  // 🌟 フックから取得。dbListがundefinedの場合に備えてデフォルト値を空配列にする
  const { dbList = [], fetchDbList, deleteDb, downloadDb } = useDatabases();

  // 🌟 もしフック側で初回通信をしていない場合は、ここでマウント時に取得する
  useEffect(() => {
    if (fetchDbList) {
      fetchDbList();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // dbListが配列でない場合（APIエラー時など）の安全対策
  const safeDbList = Array.isArray(dbList) ? dbList : [];

  return (
    <div className="bg-white border rounded-xl shadow-sm overflow-hidden">
      <div className="bg-gray-50 px-4 py-3 border-b flex justify-between items-center">
        <h3 className="text-sm font-bold text-gray-700 flex items-center gap-2">
          <span>🗄️</span> 生成済みデータベース
        </h3>
        <button onClick={fetchDbList} className="text-xs text-blue-600 hover:underline">
          更新
        </button>
      </div>

      <div className="p-4">
        {safeDbList.length === 0 ? (
          <p className="text-xs text-gray-400 text-center py-4">データがありません</p>
        ) : (
          <div className="grid grid-cols-1 gap-2">
            {safeDbList.map((db) => (
              <div key={db.name} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100">
                <div className="flex flex-col">
                  <span className="text-sm font-bold text-gray-700">🗄️ {db.name}</span>
                  <span className="text-[10px] text-gray-400">
                    {db.size_kb} KB / {db.modified_at}
                  </span>
                </div>
                <div className="flex gap-2">
                  <button 
                    onClick={() => downloadDb(db.name)} 
                    className="text-blue-600 text-[10px] font-bold border border-blue-200 px-2 py-1 rounded bg-white"
                  >
                    DL 📥
                  </button>
                  <button 
                    onClick={() => deleteDb(db.name)} 
                    className="text-red-600 text-[10px] font-bold border border-red-200 px-2 py-1 rounded bg-red-50"
                  >
                    削除 🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}