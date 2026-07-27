// frontend/src/components/Builder/ComponentPalette.tsx
import React from 'react';
import { Droppable, Draggable } from '@hello-pangea/dnd';
import { useBuilderStore } from '../../store/builderStore'; // 🌟 追加

const COMPONENTS = [
  { type: 'hero', label: '見出し(Hero)', icon: '🖼', category: 'content' },
  { type: 'header', label: '見出し', icon: 'H', category: 'content' },
  { type: 'text', label: 'テキスト', icon: '¶', category: 'content' },
  { type: 'image', label: '画像', icon: '🖼', category: 'media' },
  { type: 'button', label: 'ボタン', icon: '⬜', category: 'interactive' },
  { type: 'form', label: 'フォーム', icon: '📝', category: 'interactive' },
];
// const COMPONENTS: ComponentDefinition[] = [
//   // --- レイアウト・基本コンテンツ ---
//   { type: 'header', label: '見出し', icon: 'H', defaultProps: {}, category: 'content' },
//   { type: 'text', label: 'テキスト', icon: '¶', defaultProps: {}, category: 'content' },
//   { type: 'image', label: '画像', icon: '🖼', defaultProps: {}, category: 'media' },
//   { type: 'columns', label: 'カラム (左右分割)', icon: '⊞', defaultProps: {}, category: 'layout' },
//   { type: 'divider', label: '区切り線', icon: '—', defaultProps: {}, category: 'layout' },
//   { type: 'spacer', label: '余白 (スペーサー)', icon: '↕', defaultProps: {}, category: 'layout' },

//   // --- フォーム・インタラクティブ ---
//   { type: 'button', label: 'ボタン', icon: '⬜', defaultProps: {}, category: 'interactive' },
//   { type: 'form', label: 'お問い合わせフォーム', icon: '📝', defaultProps: {}, category: 'interactive' },

//   // --- 外部連携 (新しく追加！) ---
//   { type: 'rss', label: 'RSSフィード', icon: '📰', defaultProps: { url: '' }, category: 'integrations' },
//   { type: 'facebook-like', label: 'Facebook いいね!', icon: '👍', defaultProps: { url: '' }, category: 'social' },
//   { type: 'youtube', label: 'YouTube動画', icon: '▶', defaultProps: { videoId: '' }, category: 'media' },
// ];

export default function ComponentPalette() {
  const { addComponent } = useBuilderStore(); // 🌟 Storeから追加アクションを取得

  return (
    <div className="w-full bg-gray-50 overflow-y-auto h-full flex-shrink-0">
      <Droppable droppableId="palette" isDropDisabled={true}>
        {(provided) => (
          <div ref={provided.innerRef} {...provided.droppableProps} className="p-3">
            <p className="text-xs text-gray-500 mb-3">クリックまたはドラッグで追加</p>
            <div className="grid grid-cols-2 gap-2">
              {COMPONENTS.map((comp, index) => (
                <Draggable key={comp.type} draggableId={comp.type} index={index}>
                  {(provided, snapshot) => (
                    <>
                      <div
                        ref={provided.innerRef}
                        {...provided.draggableProps}
                        {...provided.dragHandleProps}
                        onClick={() => addComponent(comp.type as any)} // 🌟 クリックでも追加される魔法！
                        className={`flex flex-col items-center justify-center p-3 rounded-lg border cursor-grab transition-all ${
                          snapshot.isDragging 
                            ? 'bg-blue-500 text-white border-blue-500 shadow-lg scale-105 z-50' 
                            : 'bg-white border-gray-200 hover:border-blue-400 hover:text-blue-600 hover:shadow-sm'
                        }`}
                      >
                        <span className="text-2xl mb-1">{comp.icon}</span>
                        <span className="text-[10px] font-medium">{comp.label}</span>
                      </div>

                      {/* ドラッグ中のプレースホルダー（残像） */}
                      {snapshot.isDragging && (
                        <div className="flex flex-col items-center justify-center p-3 rounded-lg border border-dashed border-gray-300 bg-gray-100 opacity-50">
                          <span className="text-2xl mb-1">{comp.icon}</span>
                          <span className="text-[10px] font-medium">{comp.label}</span>
                        </div>
                      )}
                    </>
                  )}
                </Draggable>
              ))}
              {provided.placeholder}
            </div>
          </div>
        )}
      </Droppable>
    </div>
  );
}