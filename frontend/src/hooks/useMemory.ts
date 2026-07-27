// frontend/src/hooks/useMemory.ts
// import console from 'console';
import { useState, useCallback } from 'react';

const API_BASE = (import.meta.env as any).VITE_API_BASE || 'http://127.0.0.1:8765';

export type ZipHistory = { id: string; filename: string; uploaded_at: string; scanned_files: number; total_chunks: number; status: string; };
export type ConversationMessage = { role: string; content: string; timestamp: string; };
export type Task = { title: string; status: string; priority: number; };
export type FileInfo = { path: string; language: string; size: number; };

export function useMemory() {
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [notes, setNotes] = useState<string[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [zipHistories, setZipHistories] = useState<ZipHistory[]>([]);
  const [loading, setLoading] = useState(true);

  const loadMemory = useCallback(async () => {
    setLoading(true);

    const safeFetch = async (endpoint: string) => {
      try {
        const response = await fetch(`${API_BASE}${endpoint}`);
        if (!response.ok) return null;
        return await response.json();
      } catch (err) {
        console.warn(`[useMemory] Fetch failed for ${endpoint}:`, err);
        return null;
      }
    };

    try {
      const [msgData, noteData, taskData, fileData, zipData] = await Promise.all([
        safeFetch('/api/memory/conversations'),
        safeFetch('/api/memory/notes'),
        safeFetch('/api/memory/tasks'),
        safeFetch('/api/memory/files'),
        safeFetch('/api/memory/zip-history')
      ]);

      if (msgData) setMessages(msgData.messages || []);
      if (noteData) setNotes(noteData.notes || []);
      if (taskData) setTasks(taskData.tasks || []);
      if (fileData) setFiles(fileData.files || []);
      if (zipData) setZipHistories(zipData.histories || []);
    } catch (error) {
      console.error('Memory loading critically failed', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleDeleteZip = useCallback(async (id: string, filename: string) => {
    if (!window.confirm(`「${filename}」の記憶を完全に削除してもよろしいですか？`)) return;
    try {
      const res = await fetch(`${API_BASE}/api/memory/zip-history/${id}`, { method: 'DELETE' });
      if (res.ok) {
        loadMemory();
      } else {
        alert("削除に失敗しました。");
      }
    } catch (error) {
      console.error('Delete failed', error);
    }
  }, [loadMemory]);
  const handleClearChatHistory = useCallback(async () => {
    if (!window.confirm('本当にすべての会話履歴を削除しますか？\n（この操作は元に戻せません）')) return;
    
    try {
      const res = await fetch(`${API_BASE}/api/memory/conversations`, { method: 'DELETE' });
      if (res.ok) {
        // 成功したら画面上の履歴も空にする
        setMessages([]);
      } else {
        alert("履歴の削除に失敗しました。");
      }
    } catch (error) {
      console.error('Failed to clear chat history', error);
      alert("通信エラーが発生しました。");
    }
  }, []);
  return {
    messages,
    notes,
    tasks,
    files,
    zipHistories,
    loading,
    loadMemory,
    handleDeleteZip,
    handleClearChatHistory
  };
}

// function fetch(arg0: string, arg1: { method: string; }) {
//   throw new Error('Function not implemented.');
// }
// function alert(arg0: string) {
//   throw new Error('Function not implemented.');
// }

