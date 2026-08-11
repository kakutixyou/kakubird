import { useState, useMemo } from "react";
import { sqlExamples } from "../data/sqlExamples";

export function SqlExampleModal({ isOpen, onClose, onSelect }) {
  // 1. カテゴリーの取得 (Hook)
  const categories = useMemo(() => {
    const cats = [...new Set(sqlExamples.map(item => item.category))];
    return cats;
  }, []);

  // 2. 選択状態の管理 (Hook)
  const [selectedCategory, setSelectedCategory] = useState(categories[0] || "");

  // 3. データのグルーピング (Hook) ★これを早期リターンの上に移動しました
  const grouped = useMemo(() => {
    const res = {};
    sqlExamples.forEach(item => {
      if (!res[item.category]) res[item.category] = [];
      res[item.category].push(item);
    });
    return res;
  }, []);

  // ★すべてのHookを呼び出し終わってから、早期リターンする
  if (!isOpen) return null;

  const handleSelect = (sql) => {
    if (onSelect) onSelect(sql);
    onClose(); // 選択したら閉じる
  };

  return (
    <div className="example-overlay" onClick={onClose}>
      <div className="example-modal-v2" onClick={(e) => e.stopPropagation()}>
        
        {/* ヘッダー */}
        <div className="example-header">
          <div className="header-info">
            <span className="header-icon">📘</span>
            <div>
              <div className="header-title">SQL Examples</div>
              <div className="header-subtitle">テーマを選んでクエリをコピー</div>
            </div>
          </div>
          <button className="close-x" onClick={onClose}>✕</button>
        </div>

        <div className="example-container">
          {/* 左ペイン：カテゴリー選択サイドバー */}
          <aside className="example-sidebar">
            {categories.map(cat => (
              <button
                key={cat}
                className={`sidebar-item ${selectedCategory === cat ? "active" : ""}`}
                onClick={() => setSelectedCategory(cat)}
              >
                {cat}
                <span className="item-count">{grouped[cat]?.length || 0}</span>
              </button>
            ))}
          </aside>

          {/* 右ペイン：選択されたカテゴリーのカード一覧 */}
          <main className="example-content">
            <div className="content-grid">
              {grouped[selectedCategory]?.map((item, i) => (
                <div
                  key={i}
                  className="example-card-v2"
                  onClick={() => handleSelect(item.sql)}
                >
                  <div className="card-header">
                    <span className="card-title">{item.title}</span>
                  </div>
                  <div className="card-desc">{item.description}</div>
                  <div className="card-preview">
                    <code>{item.sql.slice(0, 80)}{item.sql.length > 80 ? "..." : ""}</code>
                  </div>
                  <div className="card-footer">このクエリを使用する →</div>
                </div>
              ))}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}