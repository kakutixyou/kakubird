import { useState } from "react";

/** * テーブルスキーマ表示とエクスポート管理を行うサイドパネル
 * * @param {Object} schema - テーブル名とカラム情報のオブジェクト
 * @param {string} dbPath - 開いているデータベースのファイルパス
 * @param {Function} onOpenDB - DBを開くダイアログを呼び出す関数
 * @param {Function} onExportJson - JSONエクスポートを実行する関数
 */
export function SchemaPanel({ schema, dbPath, onOpenDB, onExportJson }) {
  // どのテーブルのトグル（アコーディオン）が開いているかを管理する状態
  const [expanded, setExpanded] = useState({});

  // テーブルの開閉を切り替える関数
  const toggleTable = (table) => {
    setExpanded(p => ({ ...p, [table]: !p[table] }));
  };

  return (
    <aside className="schema-panel">
      <div className="panel-header">
        <span className="panel-title">データベース</span>
        <button className="icon-btn" onClick={onOpenDB} title="DBを開く">
          ＋
        </button>
      </div>

      {dbPath ? (
        <div className="db-info-box">
          <div className="db-path" title={dbPath}>
            📁 {dbPath.split("/").pop()}
          </div>
          <button className="export-btn" onClick={onExportJson}>
            📥 全データをJSONで保存
          </button>
        </div>
      ) : (
        <button className="open-db-btn" onClick={onOpenDB}>
          SQLiteファイルを開く
        </button>
      )}

      <div className="schema-list">
        {Object.entries(schema).map(([table, columns]) => (
          <div key={table} className="schema-table">
            {/* テーブル名（クリックで開閉） */}
            <div className="schema-table-header" onClick={() => toggleTable(table)}>
              <span className="table-icon">▤</span>
              <span className="table-name">{table}</span>
              <span className="expand-icon">{expanded[table] ? "▾" : "▸"}</span>
            </div>
            
            {/* カラム一覧（開いている時だけ表示） */}
            {expanded[table] && (
              <ul className="schema-columns">
                {columns.map(col => (
                  <li key={col.name} className="schema-col">
                    <span className="col-name">{col.name}</span>
                    <span className="col-type">{col.type}</span>
                    {col.pk && <span className="col-pk">PK</span>}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </aside>
  );
}