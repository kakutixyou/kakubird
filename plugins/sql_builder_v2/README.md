# SQL Builder v2 — アーキテクチャ設計書

## ディレクトリ構成

```
sql-builder/
├── electron/
│   ├── main.js        # Electronメインプロセス (Python起動 + IPC)
│   └── preload.js     # contextBridge (安全なAPI橋渡し)
│
├── backend/
│   └── server.py      # Python FastAPI + SQLite実行エンジン
│
├── src/
│   ├── App.jsx        # Reactルートコンポーネント
│   ├── App.css        # スタイル
│   └── hooks/
│       └── useSQL.js  # SQL実行カスタムフック
│
├── package.json
└── vite.config.js
```

## 通信フロー

```
React (Renderer)
  └─ window.electronAPI.executeSQL(sql, dbPath)
        ↓ contextBridge (preload.js)
  Electron Main Process
  └─ ipcMain.handle("sql:execute")
        ↓ HTTP POST localhost:8765/execute
  Python FastAPI (server.py)
  └─ SQLiteManager.execute(sql)
        ↓ sqlite3
  *.sqlite ファイル
```

## セキュリティ設計

| 設定 | 値 | 理由 |
|------|-----|------|
| nodeIntegration | false | RendererからNode.js APIを使わせない |
| contextIsolation | true | contextBridgeの前提 |
| sandbox | true | 追加プロセス分離 |
| HTTP | 127.0.0.1のみ | 外部ネットワーク通信なし |

## 開発起動

```bash
# 1. Python依存関係
pip install fastapi uvicorn

# 2. JS依存関係
npm install

# 3. 開発モード (Vite + Electron同時起動)
npm run dev
```

## ビルド

```bash
# Python → 実行バイナリ化
pip install pyinstaller
npm run build:python

# 全体ビルド
npm run build
```

## 今後の拡張ポイント

| 優先度 | 機能 | 実装場所 |
|--------|------|---------|
| 2位 | AND/OR, ORDER BY対応 | backend/server.py の analyze関数 |
| 3位 | ER図 | src/components/ERDiagram.jsx (mermaid.js) |
| 5位 | クエリ保存 | /history APIが既に存在、UIのみ追加 |
| 7位 | SQL→コード変換 | backend/server.py に /convert エンドポイント追加 |
| 8位 | エラーチェック | backend/server.py に EXPLAIN QUERY PLAN を追加 |
