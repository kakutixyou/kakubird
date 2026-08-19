// frontend/src/components/Builder/BuilderToolbar.tsx
import React from 'react';
import { Page } from '../../types';
import { useBuilderStore } from '../../store/builderStore';
import { generateHtmlString, downloadHtmlFile, printAndPdfHtml } from '../../utils/exportHtml';

interface BuilderToolbarProps {
  currentPage: Page | null;
  isDirty: boolean;
  showRuleEditor: boolean;
  saving: boolean;
  onToggleRuleEditor: () => void;
  onToggleMemoryDrawer: () => void;
  onSave: () => void;
  onPublish: () => void;
  onBack: () => void;
}

export default function BuilderToolbar({
  currentPage,
  isDirty,
  showRuleEditor,
  saving,
  onToggleRuleEditor,
  onToggleMemoryDrawer,
  onSave,
  onPublish,
  onBack,
}: BuilderToolbarProps) {
  // Storeからエクスポート/印刷用のコンポーネントを取得
  const components = useBuilderStore((state) => state.components);

  // HTML書き出し処理
  const handleExport = () => {
    if (components.length === 0) {
      alert('書き出すコンポーネントがありません。');
      return;
    }
    const htmlString = generateHtmlString(components);
    const filename = currentPage?.title ? `${currentPage.title}.html` : 'my-page.html';
    downloadHtmlFile(htmlString, filename);
  };

  // 印刷・PDF化処理
  const handlePrint = () => {
    if (components.length === 0) {
      alert('印刷するコンポーネントがありません。');
      return;
    }
    printAndPdfHtml(components);
  };

  return (
    // z-50 をつけて、無限キャンバスの上をスクロールしても隠れないようにする
    <div className="relative z-50 flex items-center justify-between px-4 py-3 bg-gray-900 text-white border-b border-gray-800 shadow-md flex-shrink-0">
      
      {/* 
          左側: 戻るボタン ＆ ページ情報
       */}
      <div className="flex items-center gap-4">
        <button
          onClick={onBack}
          className="text-gray-400 hover:text-white transition-colors text-sm font-medium flex items-center gap-1"
          title="ダッシュボードに戻る"
        >
          <span>←</span> 戻る
        </button>
        <div className="h-5 w-px bg-gray-700"></div>
        <div className="font-semibold text-lg flex items-center gap-2">
          {currentPage ? currentPage.title : '未保存のページ'}
          {isDirty && (
            <span 
              className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" 
              title="未保存の変更があります"
            ></span>
          )}
        </div>
      </div>

      {/* 
          中央: 各種パネルのトグルスイッチ
       */}
      <div className="flex items-center gap-2">
        <button
          onClick={onToggleRuleEditor}
          className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
            showRuleEditor 
              ? 'bg-blue-600 text-white' 
              : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
          }`}
        >
          {showRuleEditor ? 'ルールエディタを閉じる 🛠' : 'ルールエディタを開く 🛠'}
        </button>
        <button
          onClick={onToggleMemoryDrawer}
          className="px-3 py-1.5 rounded text-sm font-medium bg-gray-800 text-gray-300 hover:bg-gray-700 transition-colors"
        >
          AIメモリー 🧠
        </button>
      </div>

      {/* 
          右側: 保存・書き出しアクション
       */}
      <div className="flex items-center gap-3">
        
        {/* 印刷 / PDFボタン */}
        <button
          onClick={handlePrint}
          className="px-4 py-1.5 bg-gray-700 hover:bg-gray-600 text-white rounded text-sm font-medium transition-colors flex items-center gap-1"
          title="印刷またはPDFとして保存"
        >
          印刷 / PDF 🖨
        </button>

        {/* ダウンロードボタン */}
        <button
          onClick={handleExport}
          className="px-4 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded text-sm font-medium transition-colors flex items-center gap-1"
          title="HTMLファイルとしてダウンロード"
        >
          書き出し 💾
        </button>
        
        {/* DB保存ボタン */}
        <button
          onClick={onSave}
          disabled={saving || !isDirty}
          className={`px-4 py-1.5 rounded text-sm font-medium transition-colors flex items-center gap-1 ${
            !isDirty
              ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700 text-white shadow-sm hover:shadow-blue-500/50'
          }`}
        >
          {saving ? '保存中...' : '保存'}
        </button>

        {/* 公開ボタン */}
        <button
          onClick={onPublish}
          className="px-4 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded text-sm font-medium transition-colors flex items-center gap-1"
        >
          公開 🚀
        </button>
      </div>
    </div>
  );
}