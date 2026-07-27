// frontend/src/components/Memory/MemoryContent.tsx
import React, { useState } from 'react';
import { ZipHistory, ConversationMessage, Task, FileInfo } from '../hooks/useMemory';

type MemoryContentProps = {
  data: {
    messages: ConversationMessage[];
    notes: string[];
    tasks: Task[];
    files: FileInfo[];
    zipHistories: ZipHistory[];
    loading: boolean;
  };
  onDeleteZip: (id: string, filename: string) => void;
  onClearChatHistory: () => void;
  isCompact?: boolean; // ドロワー用に文字サイズなどを小さくするフラグ
};

// export default function MemoryContent({ data, onDeleteZip, isCompact = false }: MemoryContentProps) {
export default function MemoryContent({ data, onDeleteZip, onClearChatHistory, isCompact = false }: MemoryContentProps) {
const [activeTab, setActiveTab] = useState('projects');
  const { messages, notes, tasks, files, zipHistories, loading } = data;

  const tabs = [
    { key: 'projects', label: isCompact ? '📦 PJ' : '📦 プロジェクト' },
    { key: 'conversations', label: isCompact ? '💬 会話' : '💬 会話履歴' },
    { key: 'notes', label: isCompact ? '📝 メモ' : '📝 メモ' },
    { key: 'tasks', label: isCompact ? '✅ タスク' : '✅ タスク' },
    ...(!isCompact ? [{ key: 'files', label: '📂 関連ファイル' }] : []),
  ] as { key: string; label: string }[];

  return (
    <div className="flex flex-col h-full bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
      {/* タブバー */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 text-center font-semibold transition-colors border-b-2 -mb-px ${
              isCompact ? 'py-2.5 text-[11px]' : 'px-5 py-3.5 text-sm'
            } ${
              activeTab === tab.key
                ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 border-indigo-600 dark:border-indigo-400 font-bold'
                : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 border-transparent'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 表示エリア */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading && (
          <div className="flex items-center justify-center py-12 text-slate-400 text-sm gap-2">
            <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
            同期中...
          </div>
        )}

        {/* 📦 プロジェクト */}
        {!loading && activeTab === 'projects' && (
          <div className="space-y-3">
            {zipHistories.length === 0 ? (
              <div className="text-center py-12 text-slate-400 border border-dashed rounded-xl text-xs bg-slate-50/50">
                記憶しているプロジェクトはありません。
              </div>
            ) : (
              zipHistories.map((project) => (
                <div key={project.id} className="border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 bg-slate-50/50 dark:bg-slate-800 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <div className="font-bold text-xs text-slate-800 dark:text-slate-100 flex items-center gap-1.5">
                      <span>📦</span> <span className="truncate max-w-[200px]">{project.filename}</span>
                    </div>
                    <div className="text-[10px] text-slate-400 mt-1 space-y-0.5">
                      <div>📅 読込: {project.uploaded_at}</div>
                      <div>📂 ファイル: {project.scanned_files} | 🧩 チャンク: {project.total_chunks}</div>
                    </div>
                  </div>
                  <div className="flex items-center justify-between sm:justify-end gap-2 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-200/60">
                    <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 font-bold text-[9px] rounded">記憶中</span>
                    <button onClick={() => onDeleteZip(project.id, project.filename)} className="text-[11px] text-red-500 hover:text-red-700 font-semibold">🗑️ 忘却</button>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

{/* 💬 会話履歴 */}
        {!loading && activeTab === 'conversations' && (
          <div className="space-y-3">
            
            {/* 🌟 ここに全消去ボタンを追加 🌟 */}
            {messages.length > 0 && (
              <div className="flex justify-end mb-4">
                <button 
                  onClick={onClearChatHistory}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-red-600 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 hover:text-red-700 transition-colors shadow-sm"
                >
                  <span>🗑️</span> 履歴をすべて消去
                </button>
              </div>
            )}

            {messages.length === 0 ? (
              <div className="text-center py-12 text-slate-400 border border-dashed rounded-xl text-xs bg-slate-50/50">
                会話履歴はありません。
              </div>
            ) : (
              messages.map((msg, index) => (
                <div key={index} className="border border-slate-100 dark:border-slate-800 rounded-xl p-3 bg-slate-50 text-xs">
                  <div className="text-[10px] text-slate-400 mb-1 font-mono">{msg.role} · {msg.timestamp}</div>
                  <div className="text-slate-700 dark:text-slate-300 whitespace-pre-wrap leading-relaxed">{msg.content}</div>
                </div>
              ))
            )}
          </div>
        )}
        {/* 📝 メモ */}
        {!loading && activeTab === 'notes' && (
          <div className="space-y-2">
            {notes.map((note, index) => (
              <div key={index} className="bg-amber-50 border border-amber-100 rounded-xl p-3 text-xs text-amber-900 leading-relaxed">
                {note}
              </div>
            ))}
          </div>
        )}

        {/* ✅ タスク */}
        {!loading && activeTab === 'tasks' && (
          <div className="space-y-2">
            {tasks.map((task, index) => (
              <div key={index} className="border border-slate-200 dark:border-slate-800 rounded-lg p-3 bg-white shadow-sm flex items-center justify-between">
                <div className="font-bold text-xs text-slate-800 truncate max-w-[200px]">{task.title}</div>
                <span className="px-1.5 py-0.5 bg-blue-50 text-blue-700 text-[10px] font-bold rounded">{task.status}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}