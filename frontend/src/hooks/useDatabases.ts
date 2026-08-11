// frontend/src/hooks/useDatabases.ts
import { useState, useEffect, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8765";
// const apiBase = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8765";
// 以下、${API_BASE} を ${apiBase} に書き換える

export function useDatabases() {
  const [dbList, setDbList] = useState([]);
  const [loading, setLoading] = useState(false);

  // 🌟 一覧取得（コンソールログを抑制して静かに実行）
  const fetchDbList = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/system/databases`);
      if (res.ok) {
        const data = await res.json();
        setDbList(data.databases || []);
      }
      // 💡 404などのエラー時は何も出力しない（静音化）
    } catch (err) {
      // 💡 サーバー起動前などの接続エラー時もコンソールを汚さない
    }
  }, []);

  // 削除処理
  const deleteDb = async (name: string) => {
    if (!window.confirm(`${name} を削除しますか？`)) return false;

    try {
      const res = await fetch(`${API_BASE}/api/system/delete-db/${name}`, {
        method: "DELETE"
      });
      if (res.ok) {
        const data = await res.json();
        if (data.status === "success") {
          console.log(`🗑️ DB削除成功: ${name}`); // 👈 アクションを起こした時だけ出す
          await fetchDbList();
          return true;
        }
      }
      return false;
    } catch (err) {
      console.error("削除エラー:", err);
      return false;
    }
  };

  const downloadDb = (name: string) => {
    window.open(`${API_BASE}/api/system/download-db/${name}`, '_blank');
  };

  // 自動更新（裏で静かに回り続ける）
  useEffect(() => {
    fetchDbList();
    const timer = setInterval(fetchDbList, 5000);
    return () => clearInterval(timer);
  }, [fetchDbList]);

  return { dbList, loading, fetchDbList, deleteDb, downloadDb };
}