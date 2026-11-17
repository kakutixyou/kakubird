// frontend/src/components/MemoryDrawer.tsx
import React, { useState } from 'react';

// ==========================================
// 1. 型定義
// ==========================================
interface Screenshot {
  id: string;
  filename?: string;
  uri?: string | null;
  mime?: string;
  createdAt?: string;
  dataUrl?: string;
  pending?: boolean;
}

type MemoryType = 'project' | 'rule' | 'knowledge' | 'experience' | 'template' | 'vector';

interface MemoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  screenshots?: Screenshot[];
  memories?: Record<MemoryType, any>;
  onUseScreenshot?: (screenshot: Screenshot | null | undefined) => void;
  onDeleteScreenshot?: (screenshotId: string) => void;
  onSaveMemory?: (type: MemoryType, payload: unknown) => Promise<void> | void;
}

// ==========================================
// 2. ギミック用拡張コンポーネント（手相占い等）
// ==========================================
function GimmickRenderer({ payload }: { payload: any }) {
  // バックエンドから viewType: 'palm_reading' が送られてきた場合の専用UI
  if (payload?.viewType === 'palm_reading') {
    return (
      <div className="flex flex-col items-center justify-center p-4 bg-indigo-950/30 border border-indigo-500/30 rounded-xl mt-4">
        <span className="text-4xl mb-2">🔮</span>
        <h4 className="font-bold text-indigo-300">手相スキャン解析</h4>
        <p className="text-xs text-indigo-200/70 mt-2 text-center">
          {payload.readingResult || "解析データを待機中..."}
        </p>
        <div className="mt-4 w-full h-32 bg-indigo-900/50 rounded-lg flex items-center justify-center border border-indigo-700">
          <span className="text-indigo-400 text-sm">ここにCanvasや手相画像をマッピング</span>
        </div>
      </div>
    );
  }

  // 汎用JSON表示フォールバック
  return (
    <pre className="text-[10px] text-slate-400 bg-slate-900 p-2 rounded overflow-x-auto mt-2">
      {JSON.stringify(payload, null, 2)}
    </pre>
  );
}

// ==========================================
// 3. メインのDrawerコンポーネント
// ==========================================
export default function MemoryDrawer({
  isOpen,
  onClose,
  screenshots = [],
  memories,
  onUseScreenshot,
  onDeleteScreenshot,
}: MemoryDrawerProps) {
  const [activeTab, setActiveTab] = useState<'screenshots' | 'memories'>('screenshots');

  if (!isOpen) return null;

  return (
    <>
      {/* 背景オーバーレイ */}
      <div 
        className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* ドロワー本体（右側からスライドイン） */}
      <div 
        className="fixed top-0 right-0 z-50 h-full w-80 max-w-[90vw] bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col transform transition-transform duration-300"
      >
        {/* ヘッダー */}
        <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-800">
          <h2 className="font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2">
            🧠 Active Memory
          </h2>
          <button 
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xl leading-none"
          >
            ×
          </button>
        </div>

        {/* タブ切り替え */}
        <div className="flex border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/50">
          <button
            onClick={() => setActiveTab('screenshots')}
            className={`flex-1 py-2 text-xs font-semibold ${
              activeTab === 'screenshots' 
                ? 'text-blue-600 border-b-2 border-blue-600 dark:text-blue-400 dark:border-blue-400' 
                : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
            }`}
          >
            📸 画像 ({screenshots.length})
          </button>
          <button
            onClick={() => setActiveTab('memories')}
            className={`flex-1 py-2 text-xs font-semibold ${
              activeTab === 'memories' 
                ? 'text-blue-600 border-b-2 border-blue-600 dark:text-blue-400 dark:border-blue-400' 
                : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
            }`}
          >
            🧩 記憶・ギミック
          </button>
        </div>

        {/* コンテンツエリア */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          
          {/* スクリーンショット タブ */}
          {activeTab === 'screenshots' && (
            screenshots.length === 0 ? (
              <div className="text-center text-slate-400 text-sm py-10">
                <span className="text-3xl block mb-2">📭</span>
                保存された画像はありません
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                {screenshots.map((shot) => (
                  <div key={shot.id} className="group relative border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden bg-slate-50 dark:bg-slate-800">
                    <img 
                      src={shot.dataUrl || shot.uri || ''} 
                      alt={shot.filename || 'Screenshot'} 
                      className="w-full h-24 object-cover"
                    />
                    <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-2">
                      <button 
                        onClick={() => onUseScreenshot?.(shot)}
                        className="text-[10px] bg-blue-600 text-white px-2 py-1 rounded"
                      >
                        解析に使う
                      </button>
                      <button 
                        onClick={() => onDeleteScreenshot?.(shot.id)}
                        className="text-[10px] bg-red-600 text-white px-2 py-1 rounded"
                      >
                        削除
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )
          )}

          {/* 記憶・ギミック タブ */}
          {activeTab === 'memories' && memories && (
            <div className="space-y-4">
              {Object.entries(memories).map(([key, memData]) => {
                if (!memData) return null;
                
                const payload = memData.payload || memData;
                const isGimmick = payload?.viewType !== undefined;

                return (
                  <div key={key} className="border border-slate-200 dark:border-slate-700 rounded-lg p-3 bg-white dark:bg-slate-800">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-xs font-bold text-slate-600 dark:text-slate-300 uppercase">
                        {key}
                      </span>
                      {memData.pending && (
                        <span className="text-[9px] bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full">
                          同期中...
                        </span>
                      )}
                    </div>
                    
                    {/* ギミック判定がある場合は専用レンダラーに処理を委譲 */}
                    {isGimmick ? (
                      <GimmickRenderer payload={payload} />
                    ) : (
                      <div className="text-xs text-slate-500 dark:text-slate-400 line-clamp-3">
                        {typeof payload === 'string' ? payload : JSON.stringify(payload)}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

        </div>
      </div>
    </>
  );
}