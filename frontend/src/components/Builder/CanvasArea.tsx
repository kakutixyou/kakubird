// frontend/src/components/Builder/CanvasArea.tsx
import React, { useState } from 'react';
import { Droppable, Draggable } from '@hello-pangea/dnd';
import { useBuilderStore } from '../../store/builderStore';

interface CanvasAreaProps {
  previewHtml?: string;
  showRuleEditor?: boolean;
}

export default function CanvasArea({ previewHtml, showRuleEditor }: CanvasAreaProps) {
  const { components, removeComponent, selectComponent, selectedComponentId } = useBuilderStore();
  
  // 🌟 キャンバスの横幅を管理するステート（初期値はPC用の100%）
  const [canvasWidth, setCanvasWidth] = useState('100%');

  return (
    <div className={`flex-1 bg-gray-200 overflow-y-auto relative flex flex-col items-center transition-all ${showRuleEditor ? '' : ''}`}>
      
      {/* 🌟 画面幅の切り替えコントローラー (上部固定) */}
      <div className="sticky top-4 z-10 flex gap-2 bg-gray-800 p-1.5 rounded-lg shadow-lg mb-4">
        <button 
          onClick={() => setCanvasWidth('375px')} 
          className={`px-3 py-1 text-xs rounded transition-colors ${canvasWidth === '375px' ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700'}`}
        >
          📱 スマホ
        </button>
        <button 
          onClick={() => setCanvasWidth('768px')} 
          className={`px-3 py-1 text-xs rounded transition-colors ${canvasWidth === '768px' ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700'}`}
        >
          💻 タブレット
        </button>
        <button 
          onClick={() => setCanvasWidth('100%')} 
          className={`px-3 py-1 text-xs rounded transition-colors ${canvasWidth === '100%' ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700'}`}
        >
          🖥 PC (最大)
        </button>
      </div>

      {/* キャンバス本体 (Droppableで囲む) */}
      <div 
        className="bg-white shadow-xl min-h-[800px] border border-gray-300 transition-all duration-300 ease-in-out relative"
        style={{ width: canvasWidth, maxWidth: '1200px' }}
      >
        <Droppable droppableId="canvas">
          {(provided) => (
            <div ref={provided.innerRef} {...provided.droppableProps} className="h-full min-h-[800px] p-4 flex flex-col gap-2">
              
              {components.length === 0 && (
                <div className="text-center text-gray-400 mt-32 pointer-events-none">
                  左のパレットからパーツをドラッグ、またはクリックして追加してください
                </div>
              )}

              {components.map((comp, index) => {
                // 🌟 設定された縦横のサイズを取得（未指定なら横100%, 縦自動）
                const componentWidth = comp.styles?.width || comp.props?.width || '100%';
                const componentHeight = comp.styles?.height || comp.props?.height || 'auto';

                return (
                  <Draggable key={comp.id} draggableId={comp.id} index={index}>
                    {(provided) => (
                      <div
                        ref={provided.innerRef}
                        {...provided.draggableProps}
                        {...provided.dragHandleProps}
                        onClick={() => selectComponent(comp.id)}
                        className={`relative group border-2 transition-all p-4 bg-gray-50 rounded shadow-sm ${
                          selectedComponentId === comp.id ? 'border-blue-500 ring-2 ring-blue-200' : 'border-transparent hover:border-blue-300'
                        }`}
                        // 🌟 ここで取得した縦横サイズをスタイルとして適用する！
                        style={{
                          ...provided.draggableProps.style,
                          width: componentWidth,
                          height: componentHeight,
                        }}
                      >
                        {/* 削除（×）ボタン */}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            removeComponent(comp.id);
                          }}
                          className="absolute -top-3 -right-3 w-7 h-7 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-md hover:bg-red-600 hover:scale-110 z-20"
                          title="このパーツを削除"
                        >
                          ✕
                        </button>

                        <div className="text-gray-700 font-medium overflow-hidden h-full">
                          [{comp.type}] ブロック
                          <p className="text-xs text-gray-500 font-normal mt-1">
                            {comp.props.title || comp.props.content || comp.props.text || 'データなし'}
                          </p>
                        </div>
                      </div>
                    )}
                  </Draggable>
                );
              })}
              {provided.placeholder}
            </div>
          )}
        </Droppable>
      </div>
    </div>
  );
}