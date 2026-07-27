// frontend/src/components/DeploymentBlock.jsx
import React from 'react';

/**
 * DeploymentBlock
 * デプロイメントのフォルダ構成ツリーを表示するコンポーネント
 */
export default function DeploymentBlock({ block, onOptionSelect, onOpenManualEdit }) {
  // 🌟 props から folderStructure とコンポーネント名を取得（どんなデータの入り方でも安全に抽出）
  const folderStructure = block?.props?.folderStructure || block?.folderStructure;
  const componentName = block?.props?.component_name || block?.component_name;

  const root = folderStructure?.root;
  const folders = folderStructure?.folders || [];

  return (
    <div className="w-full max-w-md border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-white dark:bg-slate-950 shadow-md mt-2 transition-all inline-block text-left">
      
      {/* ヘッダー部分：名前の表示と、アクションボタン */}
      <div className="bg-slate-50 dark:bg-slate-900 px-3 py-2 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center gap-2">
        <span className="flex items-center gap-1.5 text-xs font-bold text-slate-700 dark:text-slate-300 truncate">
          <span>🚀</span> {componentName || "Deployment Structure"}
        </span>
        
        {/* ボタン群 */}
        <div className="flex items-center space-x-1 flex-shrink-0">
          <button 
            onClick={() => onOptionSelect?.(["AIに修正を依頼する"])}
            title="AIに修正を頼む"
            className="p-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors text-xs flex items-center gap-1"
          >
            <span>🤖</span> <span className="hidden sm:inline">AI修正</span>
          </button>
          
          <button 
            onClick={() => onOpenManualEdit?.(block)}
            title="自分でデプロイメントを編集"
            className="p-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-xs flex items-center gap-1 font-medium shadow-sm"
          >
            <span>✏️</span> <span className="hidden sm:inline">手動編集</span>
          </button>
        </div>
      </div>
      
      {/* フォルダ構成表示エリア */}
      <div className="p-3 bg-slate-50/50 dark:bg-slate-900/30 max-h-[250px] overflow-y-auto text-sm space-y-2 font-mono">
        {folderStructure ? (
          <>
            {/* ルートフォルダー */}
            <div className="font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
              📁 {root?.name || 'root'}
            </div>
            
            {/* フォルダー & サブフォルダーの一覧 */}
            <div className="pl-4 border-l-2 border-slate-200 dark:border-slate-700 space-y-2">
              {folders.map((folder, fIdx) => (
                <div key={fIdx} className="space-y-1">
                  <div className="text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                    📁 {folder.name}
                  </div>
                  
                  {/* サブフォルダー */}
                  {folder.subfolders && folder.subfolders.length > 0 && (
                    <div className="pl-4 border-l border-slate-200 dark:border-slate-700 space-y-1">
                      {folder.subfolders.map((subfolder, sIdx) => (
                        <div key={sIdx} className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                          📄 {subfolder.name}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="text-xs text-slate-400 p-2 text-center">
            フォルダ構造データがありません
          </div>
        )}
      </div>
      
    </div>
  );
}