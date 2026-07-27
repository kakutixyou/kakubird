// To(と)/frontend/src/pages/Builder.tsx
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { DragDropContext, DropResult } from '@hello-pangea/dnd';

// フック群の読み込み
import { usePageManager } from '../hooks/usePageManager';
import { useHtmlBuilder } from '../hooks/useHtmlBuilder';
import { useBuilderStore } from '../store/builderStore';

// コンポーネント群の読み込み
import BuilderDashboard from '../components/Dashboard/index';
import BuilderToolbar from '../components/Builder/BuilderToolbar';
import RuleEditorPanel from '../components/Builder/RuleEditorPanel';
import ComponentPalette from '../components/Builder/ComponentPalette';
import CanvasArea from '../components/Builder/CanvasArea';
import AiChatPanel from '../components/AiChatPanel';
import MemoryDrawer from '../components/MemoryDrawer';
import HtmlManualEditModal from '../components/Builder/HtmlManualEditModal';

// 🌟 開発・デモ用のテンプレートリスト（実際はバックエンドの Dummy_HTML/templates から走査して取得する想定）
const MOCK_TEMPLATES = [
  { id: 'poster_conference', name: '未来創造カンファレンス (イベント)', type: 'html', path: '/templates/poster_conference.html' },
  { id: 'poster_cafe', name: '青空ラムネカフェ (カフェ出店)', type: 'html', path: '/templates/poster_cafe.html' },
  { id: 'regional_revitalization', name: '地域活性化PRポスター', type: 'html', path: '/templates/regional.html' },
];

export default function Builder() {
  const { pageId } = useParams();
  const navigate = useNavigate();
  
  const { 
    pages, 
    currentPage, 
    isDirty, 
    components, 
    addComponent, 
    reorderComponents 
  } = useBuilderStore();

  const {
    loading, saving, showPageList, setShowPageList, newPageTitle, setNewPageTitle,
    createPage, savePage, publishPage, deletePage
  } = usePageManager(pageId);

  const {
    htmlRules, selectedRuleId, setSelectedRuleId, ruleInputs, setRuleInputs,
    generatedComponents, previewHtml, exporting, handleGenerateComponent,
    handleAiCommand, deleteGeneratedComponent, exportAsHtml, resetBuilderState
  } = useHtmlBuilder(currentPage?.title);

  // 🌟 モード・タブ管理用のステート
  const [editorMode, setEditorMode] = useState<'json' | 'html_template'>('json'); // JSONビルダー vs iframeテンプレート
  const [showLeftPanel, setShowLeftPanel] = useState(true);
  const [leftPanelTab, setLeftPanelTab] = useState<'palette' | 'rules' | 'templates'>('palette'); // 🌟 templatesを追加
  const [showMemoryDrawer, setShowMemoryDrawer] = useState(false);
  const [activeTemplateHtml, setActiveTemplateHtml] = useState<string>(''); // iframeに流し込むHTML

  const [editingBlock, setEditingBlock] = useState<any | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  useEffect(() => {
    if (!pageId) return;
    if (currentPage?.id !== pageId) {
      resetBuilderState();
    }
  }, [pageId, currentPage?.id, resetBuilderState]);

  const handleOpenManualEdit = (block: any) => {
    setEditingBlock(block);
    setIsEditModalOpen(true);
  };

  const handleSaveManualEdit = (updatedHtml: string, updatedCss: string, componentName: string) => {
    addComponent(
      'custom_html' as any, 
      { html: updatedHtml, css: updatedCss, component_name: componentName },
      components.length
    );
    setIsEditModalOpen(false);
    setEditingBlock(null);
  };

  const handleDragEnd = (result: DropResult) => {
    const { source, destination, draggableId } = result;
    if (!destination) return;
    if (source.droppableId === 'palette' && destination.droppableId === 'canvas') {
      addComponent(draggableId as any, {}, destination.index);
      return;
    }
    if (source.droppableId === 'canvas' && destination.droppableId === 'canvas') {
      reorderComponents(source.index, destination.index);
    }
  };

  // 🌟 テンプレートを選択してHTMLモードに切り替える処理（実際はfetchなどでHTML文字列を取得する）
  const loadTemplate = async (templateId: string) => {
    setEditorMode('html_template');
    
    // ※今回はデモとしてダミーのHTML文字列をセットします。
    // 実稼働時は await fetch(`/api/templates/${templateId}`) などで Dummy_HTML フォルダから読み込む
    const dummyHtmlResponse = `
      <!DOCTYPE html><html><head><style>
        body { display: flex; justify-content: center; align-items: center; height: 100vh; background: #f0f0f0; font-family: sans-serif; }
        .box { padding: 40px; background: white; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); text-align: center; }
      </style></head><body>
        <div class="box">
          <h1>${templateId} のテンプレート</h1>
          <p>AIが生成したHTMLファイルがここにiframeで表示されます。</p>
          <button style="padding: 10px 20px; background: blue; color: white; border: none; border-radius: 5px;">綺麗なボタン</button>
        </div>
      </body></html>
    `;
    setActiveTemplateHtml(dummyHtmlResponse);
  };

  if ((showPageList || !pageId) && components.length === 0) {
    return <BuilderDashboard pages={pages} newPageTitle={newPageTitle} setNewPageTitle={setNewPageTitle} onCreatePage={createPage} onDeletePage={deletePage} />;
  }

  if (loading && pageId) {
    return <div className="flex items-center justify-center h-full text-gray-400 animate-pulse w-full bg-gray-900">ページデータ展開中...</div>;
  }

  return (
    <div className="flex flex-col h-full bg-gray-100 overflow-hidden relative w-full font-sans select-none">
      
      <BuilderToolbar
        currentPage={currentPage}
        isDirty={isDirty}
        showRuleEditor={showLeftPanel}
        saving={saving}
        onToggleRuleEditor={() => setShowLeftPanel(!showLeftPanel)}
        onToggleMemoryDrawer={() => setShowMemoryDrawer(true)}
        onSave={savePage}
        onPublish={publishPage}
        onBack={() => { setShowPageList(true); navigate('/builder'); }}
      />

      <DragDropContext onDragEnd={handleDragEnd}>
        <div className="flex flex-1 overflow-hidden relative w-full">
          
          {/* 左側サイドパネル */}
          {showLeftPanel && (
            <div className="w-80 border-r border-gray-200 bg-white flex flex-col flex-shrink-0 z-20 shadow-lg overflow-hidden">
              <div className="flex border-b border-gray-200 bg-gray-50 text-xs flex-shrink-0">
                <button 
                  onClick={() => { setLeftPanelTab('palette'); setEditorMode('json'); }}
                  className={`flex-1 py-3 font-bold border-b-2 transition-colors ${leftPanelTab === 'palette' ? 'border-blue-600 text-blue-600 bg-white' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
                >
                  🏗️ パーツ
                </button>
                <button 
                  onClick={() => { setLeftPanelTab('rules'); setEditorMode('json'); }}
                  className={`flex-1 py-3 font-bold border-b-2 transition-colors ${leftPanelTab === 'rules' ? 'border-blue-600 text-blue-600 bg-white' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
                >
                  🛠️ AI生成
                </button>
                {/* 🌟 新設：テンプレートタブ */}
                <button 
                  onClick={() => setLeftPanelTab('templates')}
                  className={`flex-1 py-3 font-bold border-b-2 transition-colors ${leftPanelTab === 'templates' ? 'border-purple-600 text-purple-600 bg-white' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
                >
                  📄 テンプレ
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-4 min-h-0 bg-gray-50">
                {leftPanelTab === 'palette' && <ComponentPalette />}
                {leftPanelTab === 'rules' && (
                  <RuleEditorPanel htmlRules={htmlRules} selectedRuleId={selectedRuleId} setSelectedRuleId={(id) => { setSelectedRuleId(id); setRuleInputs({}); }} ruleInputs={ruleInputs} setRuleInputs={setRuleInputs} generatedComponents={generatedComponents} exporting={exporting} onGenerate={handleGenerateComponent} onDeleteComponent={deleteGeneratedComponent} onExport={exportAsHtml} />
                )}
                {/* 🌟 テンプレートリストの表示 */}
                {leftPanelTab === 'templates' && (
                  <div className="flex flex-col gap-3">
                    <p className="text-xs text-gray-500 mb-2">生成済みのHTMLファイル一覧</p>
                    {MOCK_TEMPLATES.map(tmpl => (
                      <div 
                        key={tmpl.id}
                        onClick={() => loadTemplate(tmpl.id)}
                        className="bg-white border border-gray-200 p-3 rounded-lg shadow-sm hover:border-purple-400 hover:shadow-md cursor-pointer transition-all flex items-center group"
                      >
                        <span className="text-2xl mr-3 group-hover:scale-110 transition-transform">🖼️</span>
                        <div className="flex-1">
                          <h4 className="text-sm font-bold text-gray-800">{tmpl.name}</h4>
                          <span className="text-[10px] text-gray-400">{tmpl.path}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 中央メインキャンバスエリア */}
          <div className="flex-1 min-w-0 h-full relative overflow-hidden bg-slate-50 flex flex-col">
            
            {/* 🌟 状態に応じたレンダリング分岐 (JSONビルダー or HTMLプレビュー) */}
            {editorMode === 'json' ? (
              <CanvasArea previewHtml={previewHtml} showRuleEditor={showLeftPanel} />
            ) : (
              <div className="h-full w-full flex flex-col items-center bg-gray-300 overflow-y-auto relative p-6">
                
                {/* モード切り替え・警告バー */}
                <div className="w-full max-w-[1200px] mb-4 bg-purple-100 border border-purple-300 text-purple-800 px-4 py-3 rounded-lg shadow-sm flex justify-between items-center z-10">
                  <div>
                    <span className="font-bold mr-2">⚡ HTML専用プレビューモード</span>
                    <span className="text-sm opacity-80">iframeによる完全なアイソレーション（分離）状態で表示しています。</span>
                  </div>
                  <button 
                    onClick={() => { setEditorMode('json'); setLeftPanelTab('palette'); }}
                    className="bg-white text-purple-700 px-3 py-1 rounded text-sm font-bold shadow hover:bg-purple-50"
                  >
                    JSONビルダーに戻る
                  </button>
                </div>

                {/* ✨ iframeによる安全なHTML表示 */}
                <iframe
                  title="HTML Template Preview"
                  srcDoc={activeTemplateHtml}
                  className="w-full max-w-[1200px] bg-white shadow-2xl border-0 transition-all duration-300"
                  style={{ minHeight: '800px', height: '100%' }}
                  sandbox="allow-scripts allow-same-origin"
                />
              </div>
            )}
          </div>

          {/* 右側サイドパネル (AIチャット) */}
          <div 
            className="border-l border-gray-200 bg-white flex-shrink-0 h-full z-20 min-w-0 flex flex-col overflow-hidden"
            style={{ width: '420px', minWidth: '320px', maxWidth: '700px', resize: 'horizontal', direction: 'rtl' }}
          >
            <div className="h-full w-full flex flex-col overflow-hidden" style={{ direction: 'ltr' }}>
              <AiChatPanel onAiCommand={handleAiCommand} onOpenManualEdit={handleOpenManualEdit} />
            </div>
          </div>

        </div>
      </DragDropContext>

      <MemoryDrawer isOpen={showMemoryDrawer} onClose={() => setShowMemoryDrawer(false)} />

      {isEditModalOpen && editingBlock && (
        <HtmlManualEditModal isOpen={isEditModalOpen} initialHtml={editingBlock.html} initialCss={editingBlock.css} componentName={editingBlock.component_name || "CustomUI"} onClose={() => { setIsEditModalOpen(false); setEditingBlock(null); }} onSave={handleSaveManualEdit} />
      )}

    </div>
  );
}