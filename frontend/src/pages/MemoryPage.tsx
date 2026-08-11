import React, { useEffect } from 'react';
import { useMemory } from '../hooks/useMemory';
import MemoryContent from '../components/MemoryContent';

export default function MemoryPage() {
  // ✅ 1. useMemory から handleClearChatHistory を受け取るように追加
  const { 
    messages, notes, tasks, files, zipHistories, loading, 
    loadMemory, handleDeleteZip, handleClearChatHistory 
  } = useMemory();

  useEffect(() => {
    loadMemory();
  }, [loadMemory]);

  return (
    <div className="p-8 bg-slate-50 dark:bg-slate-950 h-full overflow-y-auto">
      <div className="max-w-6xl mx-auto">
        <header className="mb-6 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">🧠 AI Memory Center</h1>
            <p className="text-sm text-slate-500">AIが保持しているプロジェクトの知識や会話履歴を一元管理します。</p>
          </div>
          <button onClick={loadMemory} className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl shadow-sm hover:bg-slate-50 text-sm font-medium transition-colors">
            🔄 同期リロード
          </button>
        </header>

        <MemoryContent 
          data={{ messages, notes, tasks, files, zipHistories, loading }}
          onDeleteZip={handleDeleteZip} 
          // ✅ 2. ダミー関数を消して、本物の関数を渡す
          onClearChatHistory={handleClearChatHistory}
        />
      </div>
    </div>
  );
}