// SqlBuilderPanel.jsx の冒頭に追加
import { useState, useRef } from "react";

export function SqlBuilderPanel({ onApplySql, useSQLHook }) {
  const { analyze, build } = useSQLHook;
  const [inputText, setInputText] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const buildTimer = useRef(null);          // ← debounce用

  const handleAnalyze = async () => {
    if (!inputText.trim()) return;
    setIsAnalyzing(true);
    try {
      const res = await analyze(inputText);
      if (res.error) throw new Error(res.error);
      setAnalysisResult(res);
    } catch (err) {
      alert("解析エラー: " + err.message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handlePartChange = (key, newValue) => {
    if (!analysisResult) return;

    // UIは即座に更新（入力感を損なわない）
    const updatedParts = analysisResult.parts.map(p =>
      p.key === key ? { ...p, value: newValue } : p
    );
    setAnalysisResult(prev => ({ ...prev, parts: updatedParts }));

    // APIへの送信は300ms後に1回だけ（連打防止）
    clearTimeout(buildTimer.current);
    buildTimer.current = setTimeout(async () => {
      const partsDict = updatedParts.reduce((acc, p) => {
        acc[p.key] = p.value;
        return acc;
      }, {});
      try {
        const buildRes = await build(analysisResult.type, partsDict);
        if (buildRes && !buildRes.error) {
          setAnalysisResult(prev => ({ ...prev, sql: buildRes.sql }));
        }
      } catch (err) {
        console.error("ビルドエラー:", err);
      }
    }, 300);
  };

  return (
    <div className="sql-builder-panel" style={styles.panel}>
      <div style={styles.inputGroup}>
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="例: 商品の中で500円より高いものは？"
          style={styles.input}
          onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
        />
        <button onClick={handleAnalyze} disabled={isAnalyzing || !inputText}>
          {isAnalyzing ? "解析中..." : "✨ AIでSQL生成"}
        </button>
      </div>

      {analysisResult && (
        <div style={styles.resultArea}>
          <div style={styles.header}>
            <strong>{analysisResult.icon} {analysisResult.title}</strong>
            <span style={{ fontSize: "0.8em", color: "#888", marginLeft: 8 }}>
              {analysisResult.description}
            </span>
          </div>

          {/* 編集可能なパーツ群 */}
          <div style={styles.partsGrid}>
            {analysisResult.parts.map(part => (
              <div key={part.key} style={styles.partItem}>
                <label style={styles.label}>{part.label}</label>
                <input
                  type="text"
                  value={part.value}
                  onChange={(e) => handlePartChange(part.key, e.target.value)}
                  style={styles.partInput}
                />
              </div>
            ))}
          </div>

          {/* 生成されたSQLのプレビューと反映ボタン */}
          <div style={styles.previewArea}>
            <pre style={styles.sqlPreview}>{analysisResult.sql}</pre>
            <button 
              onClick={() => onApplySql(analysisResult.sql)}
              style={styles.applyButton}
            >
              📝 エディタに反映
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// （簡易的なインラインスタイル。App.cssに移動することをおすすめします）
const styles = {
  panel: { background: "#1e1e24", padding: "16px", borderBottom: "1px solid #333" },
  inputGroup: { display: "flex", gap: "8px", marginBottom: "16px" },
  input: { flex: 1, padding: "8px", borderRadius: "4px", border: "1px solid #444", background: "#111", color: "#fff" },
  resultArea: { background: "#2a2a35", padding: "16px", borderRadius: "8px" },
  header: { marginBottom: "12px" },
  partsGrid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "16px" },
  partItem: { display: "flex", flexDirection: "column", gap: "4px" },
  label: { fontSize: "0.85em", color: "#aaa" },
  partInput: { padding: "6px", borderRadius: "4px", border: "1px solid #555", background: "#111", color: "#fff" },
  previewArea: { display: "flex", alignItems: "flex-start", gap: "12px" },
  sqlPreview: { flex: 1, margin: 0, padding: "12px", background: "#000", color: "#4af", borderRadius: "4px", overflowX: "auto" },
  applyButton: { padding: "8px 16px", background: "#4caf50", color: "#fff", border: "none", borderRadius: "4px", cursor: "pointer", whiteSpace: "nowrap" }
};