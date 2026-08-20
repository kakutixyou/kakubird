import { useState, useCallback, useEffect } from "react";

// --- 設定 ---
const CHAT_ENDPOINT = import.meta.env.VITE_CHAT_ENDPOINT || "http://127.0.0.1:8765/api/chat";
const API_BASE = "http://kakubird.onrender.com";
const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT || "http://127.0.0.1:8765/api/sql/run";
const ENV_REMOTE_API_KEY = import.meta.env.VITE_REMOTE_API_KEY || "";

// window.electronAPI が存在しない場合（ブラウザ開発時）のモック
const api = window.electronAPI ?? {
  execute: async (sql, dbPath) => {
    console.warn("[DEV] Mock execution");
    await new Promise(r => setTimeout(r, 400));
    return { success: true, columns: ["id", "name"], rows: [[1, "Mock Data"]], row_count: 1 };
  },
  getTables:  async () => ({}),
  getHistory: async () => [],
  openDBFile: async () => "/mock/path/sample.sqlite",
  analyze: async (text) => {
    console.warn("[DEV] Mock analyze:", text);
    return { error: "ブラウザ環境のためAI解析はモックです" };
  },
  build: async (type, parts) => {
    console.warn("[DEV] Mock build:", type, parts);
    return { error: "ブラウザ環境のためビルドはモックです" };
  },
  getTemplates: async () => [],
  onBackendCrashed: (callback) => {},
  exportJSON: async (path) => ({ success: true, data: { mock: "data" } }),
};

const INITIAL_RESULT = {
  columns: [],
  rows: [],
  row_count: 0,
  affected_rows: 0,
  execution_time_ms: 0,
  query_id: null,
};

// ==
// ここから下がカスタムHook本体
// ==
export function useSQL() {
  const [dbPath, setDbPath]     = useState(null);
  const [schema, setSchema]     = useState({});
  const [result, setResult]     = useState(INITIAL_RESULT);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);
  const [history, setHistory]   = useState([]);
  
  // ✅ 修正：ファイル上部にあったものを、useSQL の中に移動しました
  const [chatHistory, setChatHistory] = useState([]);

  // バックエンド監視
  useEffect(() => {
    if (api.onBackendCrashed) {
      api.onBackendCrashed(({ code, signal }) => {
        setError(` バックエンドが異常終了しました (Code: ${code})。`);
        setLoading(false);
      });
    }
  }, []);

  // 履歴ロード
  useEffect(() => {
    api.getHistory().then(setHistory).catch(() => {});
  }, []);

  // DBオープン
  const openDB = useCallback(async () => {
    const path = await api.openDBFile();
    if (!path) return;
    setDbPath(path);
    setResult(INITIAL_RESULT);
    setError(null);
    try {
      const tables = await api.getTables(path);
      setSchema(tables);
    } catch (err) {
      setError(`スキーマ取得エラー: ${err.message}`);
    }
  }, []);

  // SQL実行
  const execute = useCallback(async (sql, isRemote = false, apiKey = "") => {
    if (!sql.trim()) return;
    if (!isRemote && !dbPath) {
      setError("先にSQLiteファイルを開いてください");
      return;
    }

    setLoading(true);
    setError(null);

    console.log(`[useSQL] 🏃‍♂️ 実行スタート！ モード: ${isRemote ? "🌐 外部API" : "💻 ローカル"}`);
    console.log(`[useSQL] 📦 処理するSQL:`, sql);

    try {
      let res;
      if (isRemote) {
        console.log(`[useSQL] 🚀 FastAPI (${API_ENDPOINT}) にリクエスト送信中...`);
        
        const tokenToUse = apiKey || ENV_REMOTE_API_KEY;

        const response = await fetch(API_ENDPOINT, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-api-key": tokenToUse
          },
          body: JSON.stringify({ sql }) 
        });
        
        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          console.error(`[useSQL] ❌ APIエラー受信 (HTTP ${response.status}):`, errData);
          throw new Error(errData.detail || errData.error || "API実行エラー");
        }
        
        res = await response.json();
        
        console.log(`[useSQL] 📥 FastAPIからのレスポンス受信成功！:`, res);
        res.success = res.status === "success" || res.success;
      } else {
        res = await api.execute(sql, dbPath);
        console.log(`[useSQL] 📥 ローカル実行の結果:`, res);
      }

      if (!res.success) {
        setError(res.error ?? "Unknown error");
        setResult(INITIAL_RESULT);
      } else {
        setResult({
          columns:           res.columns || [],
          rows:              res.rows || [],
          row_count:         res.row_count || 0,
          affected_rows:     res.affected_rows || 0,
          execution_time_ms: res.execution_time_ms || 0,
          query_id:          res.query_id || null,
        });

        setHistory(prev => [
          { sql, result: res, timestamp: Date.now() },
          ...prev.slice(0, 49),
        ]);
      }
    } catch (err) {
      console.error(`[useSQL] 💥 例外エラー発生:`, err);
      setError(`実行エラー: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [dbPath]);

  // ✅ 修正：ファイル上部にあった chat 関数も中に入れました（これで dbPath や setLoading が使えます）
// 💡 修正点1: 第3引数に apiKey を追加
  const chat = useCallback(async (message, mode = "custom", apiKey = "") => {
    setLoading(true);
    setError(null);

    // 💡 画面から渡されたキーがあれば使い、無ければ .env の設定を使う
    const tokenToUse = apiKey || ENV_REMOTE_API_KEY;

    try {
      const response = await fetch(CHAT_ENDPOINT, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          // 💡 修正点2: バックエンドが待ち受けている Authorization ヘッダーを追加
          // tokenToUse があれば "Bearer トークン" の形にし、無ければ空文字にする
          ...(tokenToUse && { "Authorization": `Bearer ${tokenToUse}` })
        },
        body: JSON.stringify({
          message,
          mode,
          db_type: "sqlite",
          db_path: dbPath || "",
          history: chatHistory,
        }),
      });

      if (!response.ok) {
        // APIキーが無効な場合（401 Unauthorized など）のエラーもここでキャッチできます
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "チャットエラー（APIキーが無効、またはサーバーエラー）");
      }

      const data = await response.json();
if (tokenToUse) {
        console.log("🔑 [認証成功] APIキーが正常に発動しました！AIと通信開始します🚀");
      }
      setChatHistory(prev => [
        ...prev,
        { role: "user",      content: message },
        { role: "assistant", content: data.reply },
      ]);

      return data; 

    } catch (err) {
      setError(`通信エラー: ${err.message}`);
      return null;
    } finally {
      setLoading(false);
    }
  }, [dbPath, chatHistory]);

  // --- AI・ビルド系機能 ---
  const analyze = async (text) => {
    try {
      const res = await fetch(`${API_BASE}/api/nlp/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "解析に失敗しました");
      return data; 
    } catch (err) {
      return { error: err.message };
    }
  };

  const build = async (type, parts) => {
    try {
      const res = await fetch(`${API_BASE}/api/nlp/build`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type, parts }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "ビルドに失敗しました");
      return data; 
    } catch (err) {
      return { error: err.message };
    }
  };

  const getTemplates = useCallback(() => api.getTemplates(), []);
  
  const exportDBToJson = useCallback(async () => {
    if (!dbPath) return null;
    try {
      const res = await window.electronAPI.exportJSON(dbPath);
      if (!res.success) throw new Error(res.error);
      return res.data;
    } catch (err) {
      setError(`エクスポートエラー: ${err.message}`);
      return null;
    }
  }, [dbPath]);

  return {
    dbPath, schema, result, loading, error, history,
    execute, openDB, analyze, build, getTemplates, exportDBToJson,
    chat, chatHistory, // ちゃんと return されています
  };
}