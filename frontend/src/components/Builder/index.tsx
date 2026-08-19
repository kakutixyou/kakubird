// frontend/src/components/Builder/index.tsx
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

// フック群
import { usePageManager } from '../../hooks/usePageManager';
import { useHtmlBuilder } from '../../hooks/useHtmlBuilder';
import { useBuilderStore } from '../../store/builderStore';

// 分割したコンポーネント群

import BuilderToolbar from './BuilderToolbar';
import RuleEditorPanel from './RuleEditorPanel';
import CanvasArea from './CanvasArea';
import AiChatPanel from '../AiChatPanel';
import MemoryDrawer from '../MemoryDrawer';

export default function BuilderContainer() {
  const { pageId } = useParams();
  const navigate = useNavigate();
  const { pages, currentPage, isDirty } = useBuilderStore();

  // 🌟 非同期・バックエンド通信ロジックを丸ごと取得
  const {
    loading,
    saving,
    showPageList,
    setShowPageList,
    newPageTitle,
    setNewPageTitle,
    createPage,
    savePage,
    publishPage,
    deletePage
  } = usePageManager(pageId);

  // 🌟 HTML生成・AI対応・書き出しロジックを丸ごと取得
  const {
    htmlRules,
    selectedRuleId,
    setSelectedRuleId,
    ruleInputs,
    setRuleInputs,
    generatedComponents,
    previewHtml,
    exporting,
    handleGenerateComponent,
    handleAiCommand,
    deleteGeneratedComponent,
    exportAsHtml,
    resetBuilderState
  } = useHtmlBuilder(currentPage?.title);

  // UI用のパネル開閉ステート
  const [showRuleEditor, setShowRuleEditor] = useState(false);
  const [showMemoryDrawer, setShowMemoryDrawer] = useState(false);

  // ページが切り替わったときは、エディタの状態をクリーンアップ
  useEffect(() => {
    if (pageId) {
      setShowRuleEditor(false);
      resetBuilderState();
    }
  }, [pageId, resetBuilderState]);

  // ===
  // ① ダッシュボードへのルーティング分岐
  // ===


  // ===
  // ② 読み込み中の表示
  // ===
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400 animate-pulse w-full">
        ページを読み込み中...
      </div>
    );
  }

  // ===
  // ③ エディタ本体の完全なレイアウト構造
  // ===
  return (
    <div className="flex flex-col h-full bg-gray-100 overflow-hidden relative w-full font-sans">
      
      {/* ツールバー */}
      <BuilderToolbar
        currentPage={currentPage}
        isDirty={isDirty}
        showRuleEditor={showRuleEditor}
        saving={saving}
        onToggleRuleEditor={() => setShowRuleEditor(!showRuleEditor)}
        onToggleMemoryDrawer={() => setShowMemoryDrawer(true)}
        onSave={savePage}
        onPublish={publishPage}
        onBack={() => {
          setShowPageList(true);
          navigate('/builder');
        }}
      />

      {/* メインエリア */}
      <div className="flex flex-1 overflow-hidden relative">
        
        {/* 左：手動生成用のルールエディタ */}
        {showRuleEditor && (
          <RuleEditorPanel
            htmlRules={htmlRules}
            selectedRuleId={selectedRuleId}
            setSelectedRuleId={(id) => {
              setSelectedRuleId(id);
              setRuleInputs({});
            }}
            ruleInputs={ruleInputs}
            setRuleInputs={setRuleInputs}
            generatedComponents={generatedComponents}
            exporting={exporting}
            onGenerate={handleGenerateComponent}
            onDeleteComponent={deleteGeneratedComponent}
            onExport={exportAsHtml}
          />
        )}

        {/* 中央：プレビュー画面 */}
        <CanvasArea
          previewHtml={previewHtml}
          showRuleEditor={showRuleEditor}
        />

        {/* 右：常駐AIアシスタント（コマンドをフックへ流す） */}
        <div className="w-[420px] border-l border-gray-200 bg-white flex-shrink-0 overflow-hidden shadow-xl h-full">
          <div className="h-full p-4">
            <AiChatPanel onAiCommand={handleAiCommand} />
          </div>
        </div>

      </div>

      {/* 画面右側からシュッと出るAIの記憶パネル */}
      <MemoryDrawer
        isOpen={showMemoryDrawer}
        onClose={() => setShowMemoryDrawer(false)}
      />

    </div>
  );
}