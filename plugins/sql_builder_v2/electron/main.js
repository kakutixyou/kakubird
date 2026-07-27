// electron/main.js
/**
 * Electron Main Process  v2
 *
 * 変更点 (アーキテクチャ版からの差分):
 * - IPC: sql:analyze  → POST /analyze
 * - IPC: sql:build    → POST /build
 * - IPC: sql:templates → GET /templates
 * - 起動失敗時のエラーダイアログ追加
 * - Python プロセスの異常終了を検知してUIに通知
 * - バックエンド通信用のAPIキー（セキュリティ）を追加
 */
const { app, BrowserWindow, ipcMain, dialog, Menu, shell } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const http = require("http");
const crypto = require("crypto");

// ─── 設定 ──────────────────────────────────────────────────────────────────

const PYTHON_PORT = 8765;
const API_BASE       = `http://127.0.0.1:${PYTHON_PORT}`;
const IS_DEV         = process.env.NODE_ENV === "development";

const PYTHON_EXEC    = IS_DEV
  ? "python3"
  : path.join(process.resourcesPath, "backend", "server");

const PYTHON_SCRIPT  = path.join(__dirname, "../backend/server.py");

// 起動のたびに32バイトの強力なランダムキーを生成
const API_KEY = crypto.randomBytes(32).toString("hex");

// ─── Python プロセス管理 ────────────────────────────────────────────────────

let pythonProcess = null;
let mainWindow    = null;

function startPythonServer() {
  return new Promise((resolve, reject) => {
    // 1. 実行環境がWindowsなら "python"、それ以外なら "python3" を使う
    const pythonCmd = process.platform === "win32" ? "python" : "python3";
    
    // 2. Pythonスクリプトを実行する時の「カレントディレクトリ」を backend フォルダーに指定する
    const backendDir = path.join(__dirname, "../backend");
    const args = IS_DEV ? ["server.py"] : [];

    // ★ここで API_KEY を環境変数として Python に渡しています
    pythonProcess = spawn(IS_DEV ? pythonCmd : PYTHON_EXEC, args, {
      cwd: IS_DEV ? backendDir : undefined, // ← これを追加！(backendフォルダ内で実行させる)
      stdio: ["ignore", "pipe", "pipe"],
      env: { 
        ...process.env, 
        PYTHONUNBUFFERED: "1",
        SQL_BUILDER_API_KEY: API_KEY 
      },
    });

    pythonProcess.stdout.on("data", (d) =>
      console.log("[Python]", d.toString().trim())
    );
    pythonProcess.stderr.on("data", (d) => {
      const msg = d.toString().trim();
      // uvicornの単なるINFO（情報）は通常のログとして出し、本当のエラー（Traceback等）だけ警告する
      if (msg.includes("INFO:")) {
        console.log("[Python INFO]", msg);
      } else {
        console.error("🚨 [Python 激ヤバエラー!!]", msg);
      }
    });

    // 異常終了を検知してRendererに通知
    pythonProcess.on("exit", (code, signal) => {
      if (code !== 0 && code !== null) {
        console.error(`[Python] exited with code=${code} signal=${signal}`);
        mainWindow?.webContents.send("backend:crashed", { code, signal });
      }
    });

    pythonProcess.on("error", (err) => {
      console.error("Failed to spawn Python:", err);
      reject(err);
    });

    // ヘルスチェック ポーリング (最大 10 秒)
    // ヘルスチェック ポーリング (最大 30 秒に延長)
     // ヘルスチェック ポーリング (最大 30 秒)
    let attempts = 0;
    const timer = setInterval(() => {
      attempts++;
      
      // "/api/auth/list" にアクセスしてみる
      http.get(`${API_BASE}/api/auth/list`, (res) => {
        // 200でも404でも500でも、とにかくPythonから何らかの応答が来れば「起動している」と判断！
        clearInterval(timer);
        console.log(`[Electron] Python ready on :${PYTHON_PORT} (Status: ${res.statusCode})`);
        resolve();
      }).on("error", () => {
        if (attempts >= 60) {
          clearInterval(timer);
          reject(new Error("Python server did not start within 30 s"));
        }
      });
    }, 500);
  });
}
function stopPythonServer() {
  if (pythonProcess) {
    pythonProcess.kill("SIGTERM");
    pythonProcess = null;
  }
}

// ─── HTTP ヘルパー ──────────────────────────────────────────────────────────

/**
 * Node 標準 http モジュールだけで Python API を呼ぶ汎用関数。
 * node-fetch / axios を使わないことでバンドルサイズを削減。
 */
function callAPI(method, apiPath, body = null) {
  return new Promise((resolve, reject) => {
    const bodyStr = body ? JSON.stringify(body) : "";
    
    // ★ここで HTTP ヘッダーに API_KEY を仕込んでいます
    const options = {
      hostname: "127.0.0.1",
      port:     PYTHON_PORT,
      path:     apiPath,
      method,
      headers: {
        "Content-Type":   "application/json",
        "Content-Length": Buffer.byteLength(bodyStr),
        "X-API-Key":      API_KEY
      },
    };

    const req = http.request(options, (res) => {
      let data = "";
      res.on("data",  (chunk) => (data += chunk));
      res.on("end",   () => {
        try   { resolve(JSON.parse(data)); }
        catch { resolve({ error: "JSON parse failed", raw: data }); }
      });
    });

    req.on("error", reject);
    if (bodyStr) req.write(bodyStr);
    req.end();
  });
}

// ─── IPC Handlers ───────────────────────────────────────────────────────────

// ── 自然言語解析 ────────────────────────────────────────────────────────────

ipcMain.handle("sql:analyze", async (_e, { text }) => {
  try {
    return await callAPI("POST", "/api/nlp/analyze", { text });
  } catch (err) {
    return { error: err.message };
  }
});

ipcMain.handle("sql:templates", async () => {
  try {
    return await callAPI("GET", "/api/nlp/templates", null);
  } catch (err) {
    return [];
  }
});

ipcMain.handle("sql:build", async (_e, { type, parts }) => {
  try {
    return await callAPI("POST", "/api/nlp/build", { type, parts });
  } catch (err) {
    return { error: err.message };
  }
});

// ── SQL 実行 ─────────────────────────────────────────────────────────────────

ipcMain.handle("sql:execute", async (_e, { sql, db_path, params = [] }) => {
  try {
    // ※ ルーティングの prefix "/api/sql" に合わせてパスを修正
    return await callAPI("POST", "/api/sql/run", { sql, db_path, params });
  } catch (err) {
    return {
      success: false, error: err.message,
      columns: [], rows: [], row_count: 0,
      affected_rows: 0, execution_time_ms: 0, query_id: null,
    };
  }
});

ipcMain.handle("sql:get-tables", async (_e, { db_path }) => {
  try {
    return await callAPI("GET", `/api/sql/tables?db_path=${encodeURIComponent(db_path)}`, null);
  } catch (err) {
    return { error: err.message };
  }
});

ipcMain.handle("sql:history", async (_e, { limit = 50 } = {}) => {
  try {
    return await callAPI("GET", `/api/history/?limit=${limit}`, null);
  } catch (err) {
    return [];
  }
});

ipcMain.handle("sql:export-json", async (_e, { db_path }) => {
  try {
    return await callAPI("GET", `/api/sql/export/json?db_path=${encodeURIComponent(db_path)}`, null);
  } catch (err) {
    return { success: false, error: err.message };
  }
});

// ── ダイアログ ───────────────────────────────────────────────────────────────

ipcMain.handle("dialog:open-db", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title:      "SQLiteファイルを開く",
    filters:    [{ name: "SQLite DB", extensions: ["sqlite", "db", "sqlite3"] }],
    properties: ["openFile"],
  });
  return result.canceled ? null : result.filePaths[0];
});

// ─── Window ──────────────────────────────────────────────────────────────────

async function createWindow() {
  mainWindow = new BrowserWindow({
    width:           1440,
    height:          900,
    autoHideMenuBar: true,//メニューバーを隠すかどうか
    minWidth:        1024,
    minHeight:       700,
    titleBarStyle:   "hiddenInset",
    backgroundColor: "#0f1117",
    webPreferences: {
      preload:          path.join(__dirname, "preload.js"),
      nodeIntegration:  false,  
      contextIsolation: true,   
      sandbox:          true,   
    },
  });

  if (IS_DEV) {
    await mainWindow.loadURL("http://localhost:3000");
    mainWindow.webContents.openDevTools();
  } else {
    await mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }
}

// ─── App Lifecycle ───────────────────────────────────────────────────────────

app.whenReady().then(async () => {
  console.log("[Electron] Starting Python backend...");
  try {
    await startPythonServer();
  } catch (err) {
    console.error("[Electron] Python startup failed:", err.message);
    dialog.showErrorBox(
      "バックエンド起動エラー",
      `Pythonサーバーの起動に失敗しました。\n${err.message}\n\n` +
      "SQL実行機能は使えませんが、アプリは起動します。"
    );
  }
  setAppMenu();
  await createWindow();
});

app.on("window-all-closed", () => {
  stopPythonServer();
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", stopPythonServer);

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

function setAppMenu() {
  const template = [
    {
      label: "ファイル",
      submenu: [
        {
          label: "データベースを開く",
          accelerator: "CmdOrCtrl+O",
          click: async () => {
            // ここで既存のIPCハンドラーと同じ処理を呼び出せます
            const result = await dialog.showOpenDialog(mainWindow, {
              properties: ["openFile"],
              filters: [{ name: "SQLite DB", extensions: ["db", "sqlite", "sqlite3"] }]
            });
            if (!result.canceled) {
              // React側に「ファイルが選ばれたよ」と通知する
              mainWindow.webContents.send("menu:open-db", result.filePaths[0]);
            }
          }
        },
        { type: "separator" },
        { label: "終了", role: "quit" }
      ]
    },
    {
      label: "編集",
      submenu: [
        { label: "元に戻す", role: "undo" },
        { label: "やり直し", role: "redo" },
        { type: "separator" },
        { label: "切り取り", role: "cut" },
        { label: "コピー", role: "copy" },
        { label: "貼り付け", role: "paste" },
        { label: "すべて選択", role: "selectAll" }
      ]
    },
    {
      label: "表示",
      submenu: [
        { label: "再読み込み", role: "reload" },
        { label: "開発者ツール", role: "toggleDevTools" },
        { type: "separator" },
        { label: "拡大", role: "zoomIn" },
        { label: "縮小", role: "zoomOut" },
        { label: "リセット", role: "resetZoom" }
      ]
    },
    {
      label: "ヘルプ",
      submenu: [
        {
          label: "GitHubリポジトリ",
          click: async () => {
            await shell.openExternal("https://github.com/your-repo"); // 自分のGitHubなど
          }
        }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}