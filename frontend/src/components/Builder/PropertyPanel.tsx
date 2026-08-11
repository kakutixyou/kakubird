// frontend/src/components/Builder/PropertyPanel.tsx
import React from 'react';
import { useBuilderStore } from '../../store/builderStore';

export default function PropertyPanel() {
  const { components, selectedComponentId, updateComponent } = useBuilderStore();

  // 現在選択されているコンポーネントを探す
  const selectedComponent = components.find((c) => c.id === selectedComponentId);

  // 🌟 何も選択されていない時の表示（親切なガイド）
  if (!selectedComponent) {
    return (
      <div className="mt-6 p-4 border-2 border-dashed border-gray-200 rounded-lg bg-gray-50 text-center text-xs text-gray-400">
        キャンバス上のパーツをクリックすると、<br/>ここに縦横サイズや詳細設定が表示されます。
      </div>
    );
  }

  const handleStyleChange = (key: string, value: string) => {
    updateComponent(selectedComponent.id, {}, { [key]: value });
  };

  const handlePropChange = (key: string, value: string) => {
    updateComponent(selectedComponent.id, { [key]: value });
  };

  return (
    <div className="mt-6 border border-blue-200 bg-blue-50/50 rounded-lg shadow-sm flex flex-col overflow-hidden">
      <div className="bg-blue-100/50 px-3 py-2 border-b border-blue-200 flex justify-between items-center">
        <h3 className="font-bold text-xs text-blue-800">
          ⚙️ 選択中のパーツ: {selectedComponent.type.toUpperCase()}
        </h3>
      </div>

      <div className="p-3 space-y-4">
        {/* =======================================
            🌟 縦横サイズ指定エリア
        ======================================= */}
        <div>
          <h4 className="text-[10px] font-bold text-gray-500 mb-2 uppercase tracking-wider">サイズ指定 (px, % など)</h4>
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="text-[10px] font-semibold text-gray-600 block mb-1">横幅 (W)</label>
              <input
                type="text"
                value={selectedComponent.styles?.width || selectedComponent.props?.width || ''}
                onChange={(e) => handleStyleChange('width', e.target.value)}
                placeholder="例: 300px"
                className="w-full border border-gray-300 rounded px-2 py-1 text-xs focus:border-blue-500 outline-none"
              />
            </div>
            <div className="flex-1">
              <label className="text-[10px] font-semibold text-gray-600 block mb-1">縦幅 (H)</label>
              <input
                type="text"
                value={selectedComponent.styles?.height || selectedComponent.props?.height || ''}
                onChange={(e) => handleStyleChange('height', e.target.value)}
                placeholder="例: auto"
                className="w-full border border-gray-300 rounded px-2 py-1 text-xs focus:border-blue-500 outline-none"
              />
            </div>
          </div>
        </div>

        {/* =======================================
            🌟 将来のHTML/JS/PHPモデル読み込み用エリア
        ======================================= */}
        <div>
          <h4 className="text-[10px] font-bold text-gray-500 mb-2 uppercase tracking-wider">データ / コード編集</h4>
          
          {selectedComponent.props.title !== undefined && (
            <div className="mb-2">
              <label className="text-[10px] font-semibold text-gray-600 block mb-1">タイトル</label>
              <input
                type="text"
                value={selectedComponent.props.title}
                onChange={(e) => handlePropChange('title', e.target.value)}
                className="w-full border border-gray-300 rounded px-2 py-1 text-xs"
              />
            </div>
          )}

          {/* HTMLやPHP、テキスト用の汎用テキストエリア */}
          <div className="mt-2">
            <label className="text-[10px] font-semibold text-gray-600 block mb-1">
              内容 (HTML/JSの埋め込みもここへ)
            </label>
            <textarea
              rows={5}
              value={selectedComponent.props.content || selectedComponent.props.text || selectedComponent.props.code || ''}
              onChange={(e) => {
                const key = selectedComponent.props.code !== undefined ? 'code' : 
                            selectedComponent.props.content !== undefined ? 'content' : 'text';
                handlePropChange(key, e.target.value);
              }}
              className="w-full border border-gray-300 rounded px-2 py-1 text-xs font-mono resize-none focus:border-blue-500 outline-none"
              placeholder="<div>カスタムHTMLを記述</div>"
            />
          </div>
        </div>
      </div>
    </div>
  );
}