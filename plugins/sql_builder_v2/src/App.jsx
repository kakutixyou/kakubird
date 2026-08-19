/**
 * App.jsx - メインコンポーネント (Beat Saber Style)
 * * 構成:
 * - パネル1: データベース接続・スキーマ表示・エクスポート
 * - パネル2: AI SQLビルダー
 * - パネル3: エディタ・実行結果
 * - パネル4: クエリ実行履歴
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { supabase } from "./utils/supabaseClient";
import { AuthPanel } from "./components/AuthPanel";
import { useSQL } from "./hooks/useSQL";
import { SqlBuilderPanel } from "./components/SqlBuilderPanel";
import { checkDangerousQuery } from "./utils/sqlCheck";
import { SchemaPanel } from "./components/SchemaPanel";
import { ConfirmDialog } from "./components/ConfirmDialog";
import { SqlExampleModal } from "./components/SqlExampleModal";
import "./index.css"; // ← 先ほどのネオンCSSがここに書かれている想定
import { ApiKeyManager } from "./components/ApiKeyManager"; 

// ─── サブコンポーネント ───────────────────────────────────────────────────────

/** 実行結果のデータテーブル */
function ResultTable({ result, error, loading }) {
  if (loading) return (
    <div className="result-empty">
      <div className="spinner" />
      <span>実行中...</span>
    </div>
  );

  if (error) return (
    <div className="result-error" style={{ color: '#ff4444', textShadow: '0 0 5px #ff4444' }}>
      <div className="error-icon">⚠</div>
      <pre className="error-text">{error}</pre>
    </div>
  );

  if (result.columns.length === 0 && result.affected_rows > 0) return (
    <div className="result-success" style={{ color: '#00ffff' }}>
      <span>✓ {result.affected_rows} 行に影響しました</span>
      <span className="exec-time">{result.execution_time_ms}ms</span>
    </div>
  );

  if (result.columns.length === 0) return (
    <div className="result-empty">
      <span>SQLを入力して実行（Ctrl+Enter）</span>
    </div>
  );

  return (
    <div className="result-wrap">
      <div className="result-meta" style={{ color: '#00ffff', marginBottom: '10px' }}>
        <span>{result.row_count.toLocaleString()} 行</span>
        <span className="exec-time" style={{ marginLeft: '10px' }}>{result.execution_time_ms}ms</span>
      </div>
      <div className="table-scroll" style={{ overflowX: 'auto', maxHeight: '300px' }}>
        <table className="result-table" style={{ width: '100%', borderCollapse: 'collapse', color: 'white' }}>
          <thead>
            <tr>
              {result.columns.map(col => (
                <th key={col} style={{ borderBottom: '2px solid #00ffff', padding: '8px', textAlign: 'left' }}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {result.rows.map((row, ri) => (
              <tr key={ri} style={{ borderBottom: '1px solid rgba(0, 255, 255, 0.2)' }}>
                {row.map((cell, ci) => (
                  <td key={ci} style={{ padding: '8px' }}>
                    {cell === null ? <span className="null-val" style={{ color: '#888' }}>NULL</span> : String(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** 実行履歴（ビートセイバーパネル化） */
function HistoryPanel({ history, onSelect }) {
  const safeHistory = Array.isArray(history) ? history : [];

  return (
    <aside className="beat-saber-panel history-panel">
      <h2>History</h2>
      {safeHistory.length === 0 ? (
        <div className="history-empty">まだ履歴はありません</div>
      ) : (
        <ul className="history-list" style={{ listStyle: 'none', padding: 0, margin: 0, overflowY: 'auto', flexGrow: 1 }}>
          {safeHistory.map((item, i) => (
            <li 
              key={i} 
              className="history-item" 
              onClick={() => onSelect(item.sql)}
              style={{ cursor: 'pointer', padding: '10px', borderBottom: '1px solid rgba(0,255,255,0.2)' }}
            >
              <div className="history-content">
                <div className="history-sql" style={{ fontSize: '0.9em', color: '#fff' }}>
                  {item.sql ? item.sql.slice(0, 60) + "..." : ""}
                </div>
                <div className="history-meta" style={{ fontSize: '0.8em', color: '#00ffff' }}>
                  {item.result?.success ? "✓" : "⚠"} {item.result?.row_count ?? 0}行 · {item.result?.execution_time_ms ?? 0}ms
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}

// ─── メインコンポーネント ─────────────────────────────────────────────────────

export default function App() {
  // =
  // 1. 全ての Hook
  // =

  const [session, setSession] = useState(null);
  const [isOfflineMode, setIsOfflineMode] = useState(false);
  const [isRemoteMode, setIsRemoteMode] = useState(false);
  
  const [apiKey, setApiKey] = useState("");
  const [showSettings, setShowSettings] = useState(false);

  const [sql, setSql] = useState("SELECT * FROM products LIMIT 10;");
  const [showExamples, setShowExamples] = useState(false);
  const textareaRef = useRef(null);

  const [confirmDialog, setConfirmDialog] = useState({
    isOpen: false,
    message: "",
    pendingSql: null,
  });

  const sqlHook = useSQL();
  const {
    dbPath, schema, result, loading, error, history,
    execute, openDB, exportDBToJson
  } = sqlHook;

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      if (session) setIsRemoteMode(true);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleExecute = useCallback(() => {
    const check = checkDangerousQuery(sql);
    if (check.isDangerous) {
      setConfirmDialog({
        isOpen: true,
        message: check.message,
        pendingSql: sql,
      });
      return;
    }
    execute(sql, isRemoteMode, apiKey);
  }, [sql, execute, isRemoteMode, apiKey]);

  const handleConfirmAction = () => {
    if (confirmDialog.pendingSql) {
      execute(confirmDialog.pendingSql, isRemoteMode, apiKey);
    }
    setConfirmDialog({ isOpen: false, message: "", pendingSql: null });
  };

  const handleCancelAction = () => {
    setConfirmDialog({ isOpen: false, message: "", pendingSql: null });
  };

  const handleKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      handleExecute();
    }
  };

  const handleExportJson = async () => {
    const data = await exportDBToJson();
    if (!data) return;

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${dbPath ? dbPath.split("/").pop() : 'database'}_export.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // =
  // 2. 画面の出し分け
  // =

  if (!session && !isOfflineMode) {
    // ログイン画面も世界観に合わせる場合、コンテナでラップ
    return (
      <div className="beat-saber-container" style={{ height: '100vh', alignItems: 'center' }}>
        <div className="beat-saber-panel">
          <h2>Authentication</h2>
          <AuthPanel onSkip={() => setIsOfflineMode(true)} />
        </div>
      </div>
    );
  }

  // =
  // 3. メイン画面の描画 (Beat Saber 4パネルレイアウト)
  // =
  return (
    <div className="app">
      {/* 画面上部のタイトル */}
      <div className="titlebar" style={{ textAlign: 'center', padding: '10px', color: '#00ffff', textShadow: '0 0 10px #00ffff' }}>
        <h1 style={{ margin: 0, fontSize: '1.8em' }}>SQL Builder v2</h1>
        {dbPath && <span className="db-indicator">● {dbPath.split("/").pop()}</span>}
      </div>

      {/* 4つのパネルを並べるコンテナ */}
      <div className="beat-saber-container">
        
        {/* パネル1: スキーマ */}
        <div className="beat-saber-panel">
          <h2>Schema</h2>
          <SchemaPanel 
            schema={schema} 
            dbPath={dbPath} 
            onOpenDB={openDB} 
            onExportJson={handleExportJson}
          />
        </div>

        {/* パネル2: AI SQLビルダー */}
        <div className="beat-saber-panel">
          <h2>AI SQL Builder</h2>
          <SqlBuilderPanel 
            useSQLHook={sqlHook} 
            onApplySql={(generatedSql) => setSql(generatedSql)} 
          />
        </div>

        {/* パネル3: エディタ ＆ 実行結果 (少し幅広に設定) */}
        <div className="beat-saber-panel" style={{ flexGrow: 1, minWidth: '350px' }}>
          <h2>Editor & Result</h2>
          
          <div className="editor-toolbar" style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '10px' }}>
            <button className="example-btn" onClick={() => setShowExamples(true)} style={{ background: 'transparent', color: '#00ffff', border: '1px solid #00ffff', cursor: 'pointer' }}>
              📘 使用例
            </button>
            
            <label style={{ marginLeft: "auto", cursor: "pointer", display: "flex", alignItems: "center", fontSize: "0.9em", color: '#fff' }}>
              <input type="checkbox" checked={isRemoteMode} onChange={(e) => setIsRemoteMode(e.target.checked)} style={{ marginRight: "6px" }} />
              外部API
            </label>

            {isRemoteMode && (
              <button className="settings-btn" onClick={() => setShowSettings(true)} style={{ background: 'transparent', color: '#00ffff', border: '1px solid #00ffff', cursor: 'pointer' }}>
                ⚙️ API設定
              </button>
            )}
            
            <button
              className="run-btn"
              onClick={handleExecute}
              disabled={loading || !sql.trim()}
              style={{ background: '#00ffff', color: '#001f3f', border: 'none', padding: '5px 15px', fontWeight: 'bold', cursor: loading ? 'not-allowed' : 'pointer' }}
            >
              {loading ? "実行中..." : "▶ 実行 (Ctrl+Enter)"}
            </button>
          </div>
          
          <textarea
            ref={textareaRef}
            className="sql-editor"
            value={sql}
            onChange={e => setSql(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="SQLを入力するか、生成してください..."
            spellCheck={false}
            style={{ width: '100%', minHeight: '120px', background: 'rgba(0,0,0,0.3)', color: '#00ffff', border: '1px solid #00ffff', padding: '10px', boxSizing: 'border-box' }}
          />

          <hr style={{ borderColor: 'rgba(0,255,255,0.3)', margin: '15px 0' }}/>

          <div className="result-section">
            <ResultTable result={result} error={error} loading={loading} />
          </div>
        </div>

        {/* パネル4: 実行履歴 */}
        <HistoryPanel
          history={history}
          onSelect={(selectedSQL) => setSql(selectedSQL)}
        />
        
      </div>

      {/* モーダル類 */}
      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        title="危険なクエリの確認"
        message={confirmDialog.message}
        onConfirm={handleConfirmAction}
        onCancel={handleCancelAction}
      />
      
      <SqlExampleModal
        isOpen={showExamples}
        onClose={() => setShowExamples(false)}
        onSelect={(selectedSql) => {
          setSql(selectedSql);
          setShowExamples(false);
        }}
      />

{showSettings && (
  <div 
    className="modal-overlay" 
    onClick={(e) => {
      // 背景クリックで閉じる処理。ただしパネル自体をクリックしても閉じないようにする
      if (e.target === e.currentTarget) setShowSettings(false);
    }}
    style={{
      position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: "rgba(0,0,0,0.8)", // 濃いめの抹茶背景にするならここを調整
      zIndex: 2000,
      display: "flex", alignItems: "center", justifyContent: "center",
      padding: "20px"
    }}
  >
    {/* ApiKeyManager 自体がパネルの装飾を持つようにしたので、外側はこれだけでOK */}
    <ApiKeyManager onClose={() => setShowSettings(false)} />
  </div>
)}

    </div>
  );
}