// src/components/ApiKeyManager.jsx
import { useState, useEffect } from "react";
// import AiChatPanel from "./AiChatPanel";jimbo（連携先で使います)
export function ApiKeyManager({ onClose }) {
  const [keys, setKeys] = useState([]);
  const [clientName, setClientName] = useState("jimbo"); 
  const [scope, setScope] = useState("read_only");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const API_BASE = "http://127.0.0.1:8765/api/auth";

  useEffect(() => {
    fetchKeys();
  }, []);

  const fetchKeys = async () => {
    try {
      const res = await fetch(`${API_BASE}/list`);
      if (!res.ok) throw new Error("キーの取得に失敗しました");
      const data = await res.json();
      setKeys(data);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleGenerate = async () => {
    if (!clientName.trim()) {
      setError("連携先アプリ名を入力してください");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_name: clientName, scope: scope }),
      });
      if (!res.ok) throw new Error("キーの生成に失敗しました");
      await fetchKeys();
      setClientName("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("このAPIキーを削除しますか？")) return;

    try {
      const res = await fetch(`${API_BASE}/delete/${id}`, {
        method: "DELETE",
      });

      if (!res.ok) throw new Error("削除に失敗しました");

      // 再取得してリストを更新
      await fetchKeys();
    } catch (err) {
      setError(err.message);
    }
  };

  const copyToClipboard = async (text) => {
    try {
      // フォーカスを強制的に戻す
      window.focus();

      await navigator.clipboard.writeText(text);
      alert("APIキーをコピーしました！");
    } catch (err) {
      console.error("Clipboard error:", err);

      // fallback
      const textarea = document.createElement("textarea");
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);

      alert("コピーしました！（fallback）");
    }
  };

  return (
    <div className="beat-saber-modal-content" style={contentStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <h2 style={titleStyle}>⚙️ API Master Console</h2>
        <button onClick={onClose} style={closeBtnStyle}>✕</button>
      </div>

      {error && <div style={{ color: "#ff4444", marginBottom: "10px", fontSize: "0.9em", textShadow: "0 0 5px #f00" }}>{error}</div>}

      <div style={generateBoxStyle}>
        <h3 style={subTitleStyle}>＋ Create New Key</h3>
        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <input
            type="text"
            value={clientName}
            onChange={(e) => setClientName(e.target.value)}
            placeholder="App Name (e.g. jimbo)"
            style={inputStyle}
          />
          
          <select 
            value={scope} 
            onChange={(e) => setScope(e.target.value)}
            style={selectStyle}
          >
            {/* セキュリティを考慮した、より詳細な権限オプション */}
            <option value="admin">Admin (Full Access)</option>
            <option value="read_only">Read-Only (SELECT Only)</option>
            <option value="data_editor">Data Editor (INSERT/UPDATE)</option>
            <option value="schema_manager">Schema Manager (DDL Only)</option>
            <option value="css_generator">CSS Style API (Design Only)</option>
          </select>

          <button 
            onClick={handleGenerate} 
            disabled={loading}
            style={generateBtnStyle}
          >
            {loading ? "..." : "GENERATE"}
          </button>
        </div>
      </div>

      <div style={{ marginTop: "20px" }}>
        <h3 style={subTitleStyle}>Active API Keys</h3>
        {keys.length === 0 ? (
          <p style={{ color: "rgba(255,255,255,0.5)", fontSize: "0.9em" }}>No keys active.</p>
        ) : (
          <ul style={listStyle}>
            {keys.map((k) => (
              <li key={k.id} style={listItemStyle}>
                <div style={{ flexGrow: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ fontWeight: "bold", fontSize: "1em", color: "#fff" }}>{k.client_name}</span>
                    <span style={getBadgeStyle(k.scope)}>
                      {k.scope?.toUpperCase().replace('_', ' ')}
                    </span>
                  </div>
                  <div style={{ fontSize: "0.8em", color: "#00ffff", fontFamily: "monospace", marginTop: "4px", opacity: 0.7 }}>
                    {k.key_value.substring(0, 8)}...{k.key_value.substring(k.key_value.length - 4)}
                  </div>
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                  <button onClick={() => copyToClipboard(k.key_value)} style={copyBtnStyle}>
                    COPY
                  </button>
                  <button onClick={() => handleDelete(k.id)} style={deleteBtnStyle} title="削除">
                    {/* SVGのゴミ箱アイコン */}
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                      <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z"/>
                      <path fillRule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
                    </svg>
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

// === ビートセイバー風インラインスタイル ===
const contentStyle = {
  backgroundColor: "#001f3f", // 深い青
  color: "#fff",
  padding: "30px",
  borderRadius: "12px",
  width: "100%",
  maxWidth: "600px", // 少し横幅を広げました
  border: "3px solid #00ffff", // 水色の枠
  boxShadow: "0 0 20px #00ffff, inset 0 0 10px #00ffff", // 発光
};

const titleStyle = { margin: 0, fontSize: "1.4em", color: "#00ffff", textShadow: "0 0 10px #00ffff" };
const subTitleStyle = { margin: "0 0 10px 0", fontSize: "1em", color: "#fff", opacity: 0.8 };

const generateBoxStyle = {
  backgroundColor: "rgba(0,0,0,0.3)",
  padding: "15px",
  borderRadius: "6px",
  border: "1px solid rgba(0, 255, 255, 0.3)"
};

const inputStyle = {
  flex: "1 1 150px", padding: "10px", borderRadius: "4px", 
  border: "1px solid #00ffff", background: "rgba(0,0,0,0.5)", color: "#fff", outline: "none"
};

const selectStyle = {
  flex: "1 1 150px", padding: "10px", borderRadius: "4px", border: "1px solid #00ffff",
  backgroundColor: "#001f3f", color: "#fff", cursor: "pointer", outline: "none"
};

const generateBtnStyle = {
  backgroundColor: "#00ffff", color: "#001f3f", border: "none", padding: "10px 20px",
  borderRadius: "4px", cursor: "pointer", fontWeight: "bold"
};

const closeBtnStyle = {
  background: "none", border: "none", fontSize: "1.5em", cursor: "pointer", color: "#00ffff"
};

const listStyle = {
  listStyle: "none", padding: 0, margin: 0, maxHeight: "250px", overflowY: "auto"
};

const listItemStyle = {
  display: "flex", justifyContent: "space-between", alignItems: "center",
  padding: "12px 0", borderBottom: "1px solid rgba(0, 255, 255, 0.2)"
};

const copyBtnStyle = {
  backgroundColor: "transparent", border: "1px solid #00ffff", color: "#00ffff",
  padding: "5px 12px", borderRadius: "4px", cursor: "pointer", fontSize: "0.8em"
};

const deleteBtnStyle = {
  backgroundColor: "transparent", border: "1px solid #ff4444", color: "#ff4444",
  padding: "5px 8px", borderRadius: "4px", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center"
};

const getBadgeStyle = (scope) => {
  let bgColor = "#00aaff"; // default blue
  let glowColor = "#00aaff";

  switch(scope) {
    case "admin":
      bgColor = "#ff0000"; glowColor = "#ff0000"; break;
    case "data_editor":
      bgColor = "#ffaa00"; glowColor = "#ffaa00"; break;
    case "schema_manager":
      bgColor = "#b000ff"; glowColor = "#b000ff"; break;
    case "css_generator":
      bgColor = "#00ffaa"; glowColor = "#00ffaa"; break; // Neon green for CSS
    default:
      break;
  }

  return {
    fontSize: "0.7em", padding: "2px 8px", borderRadius: "10px", fontWeight: "bold",
    backgroundColor: bgColor,
    color: "#fff",
    boxShadow: `0 0 5px ${glowColor}`
  };
};