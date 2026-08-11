// frontend/src/components/MemoryDrawer.tsx
import React, { useEffect, useState } from 'react';
import { useMemory } from '../hooks/useMemory';
import MemoryContent from './MemoryContent';
import MemoryManager from './MemoryManager'; // 先ほど作成したOCR/スクショ管理UIをインポート

interface MemoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function MemoryDrawer({ isOpen, onClose }: MemoryDrawerProps) {
  const { messages, notes, tasks, files, zipHistories, loading, loadMemory, handleDeleteZip } = useMemory();
  
  // 🌟 タブの切り替えステートを追加 ('core' = 既存の文脈表示, 'ocr' = スクショ管理)
  const [activeTab, setActiveTab] = useState<'core' | 'ocr'>('core');

  // ドロワーが開いたタイミングで同期
  useEffect(() => {
    if (isOpen) {
      loadMemory();
    }
  }, [isOpen, loadMemory]);

  return (
    // 🌟 タブが 'ocr' の時は w-[800px] に広がり、'core' の時は w-96 に戻るアニメーション
    <div className={`fixed inset-y-0 right-0 z-50 bg-white shadow-2xl border-l border-gray-200 flex flex-col transform transition-all duration-300 ease-in-out ${
      isOpen ? 'translate-x-0' : 'translate-x-full'
    } ${
      activeTab === 'ocr' ? 'w-[800px]' : 'w-96'
    }`}>
      
      {/* ヘッダー */}
      <div className="p-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center flex-shrink-0">
        <div>
          <h2 className="text-base font-bold text-gray-800 flex items-center gap-2">🧠 AI Memory Center</h2>
          <p className="text-[10px] text-gray-500 mt-0.5">
            {activeTab === 'core' ? '現在のコンテキスト状態' : 'スクショ・求人情報の視覚記憶'}
          </p>
        </div>
        <button onClick={onClose} className="w-7 h-7 rounded-full bg-gray-200/60 hover:bg-gray-200 flex items-center justify-center text-gray-500 hover:text-gray-700 transition-colors text-xs font-bold">✕</button>
      </div>

      {/* 🌟 タブ切り替えボタン */}
      <div className="flex border-b border-gray-200 bg-white">
        <button
          onClick={() => setActiveTab('core')}
          className={`flex-1 py-2.5 text-xs font-bold transition-colors duration-200 ${
            activeTab === 'core' 
              ? 'border-b-2 border-blue-500 text-blue-600' 
              : 'text-gray-500 hover:bg-gray-50'
          }`}
        >
          📄 開発コンテキスト
        </button>
        <button
          onClick={() => setActiveTab('ocr')}
          className={`flex-1 py-2.5 text-xs font-bold transition-colors duration-200 ${
            activeTab === 'ocr' 
              ? 'border-b-2 border-blue-500 text-blue-600' 
              : 'text-gray-500 hover:bg-gray-50'
          }`}
        >
          📸 スクショ・求人解析
        </button>
      </div>

      {/* コンテンツエリア (相対配置で絶対配置の子要素を重ねる) */}
      <div className="flex-1 overflow-hidden relative bg-gray-50">
        
        {/* 1. 既存のコアメモリ (isCompact) */}
        <div className={`absolute inset-0 overflow-y-auto p-2 transition-opacity duration-300 ${
          activeTab === 'core' ? 'opacity-100 z-10' : 'opacity-0 z-0 pointer-events-none'
        }`}>
          <MemoryContent 
            data={{ messages, notes, tasks, files, zipHistories, loading }} 
            onDeleteZip={handleDeleteZip}
            isCompact={true} 
          />
        </div>

        {/* 2. 新しいスクショ管理UI (MemoryManager) */}
        {/* ※ MemoryManager側の背景色がダークテーマ固定(#0d0f16)なので、親も合わせて暗くするかはUIのお好みで */}
        <div className={`absolute inset-0 overflow-y-auto bg-[#0d0f16] transition-opacity duration-300 ${
          activeTab === 'ocr' ? 'opacity-100 z-10' : 'opacity-0 z-0 pointer-events-none'
        }`}>
          <MemoryManager />
        </div>
        
      </div>

      {/* フッター (コアメモリの時だけ「同期」ボタンを表示) */}
      {activeTab === 'core' && (
        <div className="p-3 border-t border-gray-200 bg-white flex justify-end flex-shrink-0">
          <button onClick={loadMemory} disabled={loading} className="px-3 py-1 bg-white border border-gray-300 hover:bg-gray-100 text-gray-600 rounded-lg text-xs font-medium transition shadow-sm disabled:opacity-50">
            🔄 同期
          </button>
        </div>
      )}
    </div>
  );
}