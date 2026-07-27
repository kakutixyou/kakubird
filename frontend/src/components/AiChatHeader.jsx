// frontend/src/components/AiChatHeader.jsx
import React, { useState, useRef } from 'react';

export default function AiChatHeader({ 
  panelWidth, 
  setPanelWidth, 
  onCreateDB, 
  onLoadHistory,
  onOpenMemory,     // 👈 メモリードロワーを開くための関数

  onUploadImage,     // 👈 画像読み込み処理の関数
  onUploadZip,      // 👈 ZIPアップロード処理の関数（将来追加予定）
  onInsertPrompt
}) {
  const [showPromptModal, setShowPromptModal] = useState(false);//モーダルを生み出す場合の書き方!
  const [showHistoryDropdown, setShowHistoryDropdown] = useState(false);
  const imageInputRef = useRef(null); // 画像アップロード用の隠しinput参照
  const zipInputRef = useRef(null);
  const handleZipChange = (e) => {
    const file = e.target.files[0];
    if (file && file.name.endsWith('.zip') && onUploadZip) {
      onUploadZip(file);
    }
    e.target.value = null; // リセット
  };
  // DB履歴のモックデータ
  const dbHistories = [
    { id: 'db-1', name: 'ECサイト商品管理DB', date: '2026-05-10' },
    { id: 'db-2', name: 'SaaSマルチテナント基本構成', date: '2026-05-11' },
    { id: 'db-3', name: 'ゲームギルドユーザーテーブル', date: '2026-05-12' },
  ];

  const handleSelect = (name) => {
    setShowHistoryDropdown(false);
    onLoadHistory(name);
  };

  // 画像選択時のハンドラー
  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file && onUploadImage) {
      onUploadImage(file);
    }
    // 同じ画像を連続で選べるように値をリセット
    e.target.value = null;
  };
function PromptItem({ title, content }) {

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
  };

  return (
    <div className="border rounded-lg p-3">

      <div className="flex items-center justify-between">
        <span className="font-medium">
          {title}
        </span>

        <button
          onClick={handleCopy}
          className="px-3 py-1 text-xs bg-indigo-600 text-white rounded"
        >
          コピー
        </button>
      </div>

    </div>
  );
}
  return (
    <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
      
      {/* 左側：タイトルとメモリーボタン */}
      <div className="flex items-center space-x-3">
        <span className="text-base font-bold bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent">
          AI Assistant
        </span>
        {onOpenMemory && (
          <button 
            onClick={onOpenMemory}
            className="text-xs px-2 py-1 bg-indigo-50 text-indigo-600 hover:bg-indigo-100 rounded-md transition-colors border border-indigo-100"
            title="AIの記憶を確認"
          >
            🧠 記憶
          </button>
        )}
      </div>

      {/* 右側：各種アクションボタン */}
      <div className="flex items-center space-x-1.5">
        
        {/* 1. 画像アップロード ( ﾟДﾟ)☆彡 */}
        <input 
          type="file" 
          accept="image/*"
          ref={imageInputRef}
          onChange={handleImageChange}
          className="hidden" 
        />
        <input 
          type="file" 
          accept=".zip"
          ref={zipInputRef}
          onChange={handleZipChange}
          className="hidden" 
        />
        <button 
          onClick={() => zipInputRef.current?.click()} 
          className="px-2 py-1 text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-md transition-colors"
          title="ZIPを読み込ませる"
        >
          📦 ZIP読込
        </button>
        <button 
          onClick={() => imageInputRef.current?.click()} 
          className="px-2 py-1 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded-md transition-colors"
          title="画像を読み込む"
        >
         ⭐画像
        </button>

        <button
          onClick={() => setShowPromptModal(true)}
          className="px-2 py-1 text-xs font-semibold text-green-700 bg-green-50 hover:bg-green-100 border border-green-200 rounded-md transition-colors"
        >
          📋 定型文
        </button>

        {/* 3. 新規DB作成 */}
        {onCreateDB && (
          <button 
            onClick={onCreateDB} 
            className="px-2 py-1 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-md transition-colors"
          >
            ＋ 新規DB
          </button>
        )}

        {/* 4. DB履歴ドロップダウン */}
        <div className="relative">
          <button 
            onClick={() => setShowHistoryDropdown(!showHistoryDropdown)} 
            className="px-2 py-1 text-xs font-semibold text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-md transition-colors"
          >
            📂 DB読込 ▾
          </button>

          {showHistoryDropdown && (
            <div className="absolute right-0 mt-1 w-56 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl z-50 py-1">
              <div className="px-3 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100 dark:border-slate-700">
                直近のDB履歴
              </div>
              {dbHistories.map((h) => (
                <button 
                  key={h.id} 
                  onClick={() => handleSelect(h.name)} 
                  className="w-full text-left px-3 py-2 text-xs hover:bg-indigo-50 dark:hover:bg-indigo-900/30 transition-colors"
                >
                  <div className="font-medium truncate">{h.name}</div>
                  <div className="text-[9px] text-slate-400">{h.date}</div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 5. パネル幅切り替え */}
        <button 
          onClick={() => setPanelWidth(panelWidth === 'normal' ? 'wide' : 'normal')} 
          className="p-1 ml-1 text-slate-400 hover:text-slate-600 transition-colors"
        >
          {panelWidth === 'normal' ? '↔️' : '➡️'}
        </button>
        {showPromptModal && (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
    <div className="w-[500px] rounded-xl bg-white shadow-xl">

      <div className="flex items-center justify-between border-b p-4">
        <h2 className="font-bold text-lg">
          定型文ライブラリ
        </h2>

        <button
          onClick={() => setShowPromptModal(false)}
          className="text-gray-500 hover:text-black"
        >
          ✕
        </button>
      </div>

      <div className="p-4 space-y-3">

        <PromptItem
          title="Ctrl+Shift+F検索"
          content={`Ctrl+Shift+Fで検索してください。

関連ファイルも確認してください。`}
        />

        <PromptItem
          title="CSS全文表示"
          content={`CSSを全文表示してください。
省略せずに全文を書いてください。`}
        />

        <PromptItem
          title="コードレビュー"
          content={`現在のコード構成を読んでください。

1. 問題点
2. 改善案
3. 修正コード

を提示してください。`}
        />
                <PromptItem
          title="repomix-output.xmlを使ってAIを強化する。"
          content={`「最新の repomix-output.xml を読み込んで、プロジェクトの構造とコンポーネント、APIの情報を解析してJSONに保存して。今後のコード生成のために知識をアップデートしてほしい。」`}
        />
        <PromptItem
        title="フォルダー構成通りに空箱で構成する"
                  content={`フォルダー構成を読んだあとこれらを空箱で構成するset.pyを作ってほしい
root/
│
├── api/
│   └── .env                          # [実装済み] APIキー等の環境変数
│
├── terminal_workflow.py               # [一部実装済 / 調整中] 統括ワークフローの入り口
│
├── schemas/
│   └── knowledge_package.py          # [設計提示済み] 共通JSONフォーマットの型定義(Pydantic)
│
├── collectors/                       # ─── 【収集層】プラグイン化されたコレクター群
│   ├── __init__.py
│   ├── base_collector.py             # [設計提示済み] コレクターの共通インターフェース(ABC)
│   ├── manager.py                    # [設計提示済み] 全コレクターを動的ロード・統括するマネージャー
│   │
│   ├── github/                       # 各コンポーネントに細分化
│   │   ├── __init__.py               # [設計提示済み] サブコレクターを束ねるマスター
│   │   ├── repository.py             # [設計提示済み] Star, Fork, 言語, ライセンス等の基本情報
│   │   ├── issue.py                  # [これから実装] 直近の課題、議論の収集
│   │   ├── release.py                # [これから実装] バージョン履歴、Changelog
│   │   └── commit.py                 # [これから実装] 直近のコード変更アクティビティ
│   │
│   ├── qiita/
│   │   ├── __init__.py
│   │   └── article.py                # [これから実装] 技術記事、タグ、LGTM数の収集
│   │
│   └── huggingface/ / zenn/ / npm/   # [これから実装] 今後必要に応じて追加するプラグイン
│
├── analyzers/                        # ─── 【解析層】
│   └── terminal_engine.py            # [一部実装済] 収集データを読み込み、Geminiで解析するエンジン
│
├── core/                             # ─── 【思考・検索層】エージェントの「脳」
│   ├── knowledge_searcher.py         # [設計提示済み] SQLite/VectorDB/JSONのハイブリッド横断検索
│   └── ofa_planner.py                # [設計提示済み] 知識を元にHandlerの実行計画(Plan)を立てる司令塔
│
├── data/                             # ─── 【記憶層】データベース
│   └── agent_brain.db                # [自動生成] 結晶化したKnowledgePackageが蓄積されるSQLite
│
├── knowledge/                        # ─── 【静的ルール層】挙動を微調整する固定制約JSON
│   ├── html/                         # (button.json, navbar.json など) [これから実装]
│   ├── css/                          # (flex.json, grid.json など) [これから実装]
│   └── terminal/                     # (git.json, docker.json など) [これから実装]
│
└── ts_layer/                         # ─── 【実行・具現化層】TypeScript ＆ フロントエンド
    ├── handlers/
    │   └── handler.ts                # [設計提示済み] PythonからのPlan(JSON)を解釈・実行するディスパッチャー
    │
    └── frontend/                     # ─── 【UI出力層】
        └── components/               # [これから実装] React / HTML / SVG / Terminalを可視化するUI`}
/>
      </div>
    </div>
  </div>
)}
      </div>
    </div>

  );
}