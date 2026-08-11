// electron/preload.js
/**
 * contextBridge: React(Renderer)に公開するAPIを最小限に絞る
 * * ここに書いたもの「だけ」がReactから触れる。
 * Node.jsのfsやchild_processには一切触れないセキュアな設計。
 */

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {

  // ── SQL生成（自然言語解析・構築） ────────────────────────────────────
// ── データエクスポート ────────────────────────────────────────────────
  exportJSON: (dbPath) =>
    ipcRenderer.invoke("sql:export-json", { db_path: dbPath }),
  /**
   * 日本語テキストを解析して SQLテンプレートを返す
   * @param {string} text - 自然言語のクエリ
   */
  analyze: (text) => 
    ipcRenderer.invoke("sql:analyze", { text }),

  /**
   * 編集済みパーツから SQL を再構築する
   * @param {string} type - クエリタイプ (例: "SELECT")
   * @param {Object} parts - クエリの構成パーツ
   */
  build: (type, parts) => 
    ipcRenderer.invoke("sql:build", { type, parts }),

  /**
   * 全テンプレート一覧を取得
   */
  getTemplates: () => 
    ipcRenderer.invoke("sql:templates"),


  // ── SQL実行・データベース管理 ────────────────────────────────────────

  /**
   * SQLを実行して結果を返す
   * @param {string} sql - 実行するSQL文
   * @param {string} dbPath - SQLiteファイルのパス
   * @param {Array}  params - プレースホルダーの値 (省略可)
   * @returns {Promise<ExecuteResult>}
   */
  execute: (sql, dbPath, params = []) =>
    ipcRenderer.invoke("sql:execute", { sql, db_path: dbPath, params }),

  /**
   * DBのテーブル一覧とスキーマを取得
   * @param {string} dbPath - SQLiteファイルのパス
   * @returns {Promise<Record<string, Column[]>>}
   */
  getTables: (dbPath) =>
    ipcRenderer.invoke("sql:get-tables", { db_path: dbPath }),

  /**
   * クエリ実行履歴を取得
   * @param {number} limit - 取得件数 (デフォルト50)
   */
  getHistory: (limit = 50) =>
    ipcRenderer.invoke("sql:history", { limit }),


  // ── OS・ファイル操作 ────────────────────────────────────────────────

  /**
   * OSのファイルダイアログでSQLiteファイルを選ばせる
   * @returns {Promise<string | null>} ファイルパス or null(キャンセル)
   */
  openDBFile: () =>
    ipcRenderer.invoke("dialog:open-db"),


  // ── バックエンド監視（main.js連動）──────────────────────────────────

  /**
   * Pythonバックエンドの異常終了を検知する
   */
  onBackendCrashed: (callback) => {
    ipcRenderer.removeAllListeners("backend:crashed");
    ipcRenderer.on("backend:crashed", (_event, data) => callback(data));
  }
});
// App.jsxのマウント時（useEffect）に読み込む

// ── 型定義（エディタの補完用） ────────────────────────────────────────

/**
 * @typedef {Object} ExecuteResult
 * @property {boolean}   success
 * @property {string[]}  columns
 * @property {any[][]}   rows
 * @property {number}    row_count
 * @property {number}    execution_time_ms
 * @property {number}    affected_rows
 * @property {string|null} error
 * @property {string}    query_id
 */