import React from 'react';
import { HtmlRule } from '../../data/htmlRules';
import { GeneratedComponent } from '../../hooks/useHtmlBuilder';

interface RuleEditorPanelProps {
  htmlRules: HtmlRule[];
  selectedRuleId: string;
  setSelectedRuleId: (id: string) => void;
  ruleInputs: Record<string, string>;
  setRuleInputs: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  generatedComponents: GeneratedComponent[];
  exporting: boolean;
  onGenerate: () => void;
  onDeleteComponent: (id: string) => void;
  onExport: () => void;
}

export default function RuleEditorPanel({
  htmlRules,
  selectedRuleId,
  setSelectedRuleId,
  ruleInputs,
  setRuleInputs,
  generatedComponents,
  exporting,
  onGenerate,
  onDeleteComponent,
  onExport
}: RuleEditorPanelProps) {
  const selectedRule = htmlRules.find(r => r.id === selectedRuleId);

  return (
    <div className="w-96 border-r border-gray-200 bg-white flex-shrink-0 overflow-y-auto shadow-lg flex flex-col h-full">
      <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-pink-50 flex-shrink-0">
        <h2 className="font-bold text-gray-800 mb-1 flex items-center gap-2 text-sm">
          <span>✨</span> HTMLルールエディタ
        </h2>
        <p className="text-[10px] text-gray-500">コンポーネントを選択して生成</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div>
          <label className="block text-[11px] font-bold text-gray-700 mb-2 uppercase">📦 タイプ</label>
          <select
            value={selectedRuleId}
            onChange={(e) => setSelectedRuleId(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-xs focus:ring-2 focus:ring-purple-500 outline-none"
          >
            <option value="">-- 選択してください --</option>
            {htmlRules.map(rule => (
              <option key={rule.id} value={rule.id}>{rule.display}</option>
            ))}
          </select>
        </div>

        {selectedRule?.inputs && (
          <div className="bg-gray-50 rounded-lg p-3 border border-gray-200 space-y-3">
            <label className="block text-[11px] font-bold text-gray-700 uppercase">📝 入力項目</label>
            {selectedRule.inputs.map(input => (
              <div key={input.key}>
                <label className="block text-[10px] font-bold text-gray-600 mb-1">{input.label}</label>
                {input.type === 'textarea' ? (
                  <textarea
                    value={ruleInputs[input.key] || ''}
                    onChange={(e) => setRuleInputs(prev => ({ ...prev, [input.key]: e.target.value }))}
                    placeholder={`${input.label}を入力...`}
                    className="w-full border border-gray-300 rounded px-2 py-1.5 text-xs focus:ring-2 focus:ring-purple-500 outline-none resize-none"
                    rows={3}
                  />
                ) : input.type === 'select' && input.options ? (
                  <select
                    value={ruleInputs[input.key] || ''}
                    onChange={(e) => setRuleInputs(prev => ({ ...prev, [input.key]: e.target.value }))}
                    className="w-full border border-gray-300 rounded px-2 py-1.5 text-xs focus:ring-2 focus:ring-purple-500 outline-none"
                  >
                    <option value="">-- 選択 --</option>
                    {input.options.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    type={input.type === 'number' ? 'number' : 'text'}
                    value={ruleInputs[input.key] || ''}
                    onChange={(e) => setRuleInputs(prev => ({ ...prev, [input.key]: e.target.value }))}
                    placeholder={`${input.label}を入力...`}
                    className="w-full border border-gray-300 rounded px-2 py-1.5 text-xs focus:ring-2 focus:ring-purple-500 outline-none"
                  />
                )}
              </div>
            ))}
          </div>
        )}

        <button
          onClick={onGenerate}
          disabled={!selectedRuleId}
          className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 disabled:from-gray-300 disabled:to-gray-300 text-white font-bold py-2 rounded-lg transition-all shadow-sm text-xs disabled:cursor-not-allowed"
        >
          ✨ コンポーネントを生成
        </button>

        {generatedComponents.length > 0 && (
          <div className="border-t border-gray-200 pt-4 space-y-2">
            <label className="block text-[11px] font-bold text-gray-700 uppercase">
              📌 生成済み ({generatedComponents.length})
            </label>
            <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
              {generatedComponents.map((comp, idx) => {
                const rule = htmlRules.find(r => r.id === comp.ruleId);
                return (
                  <div key={comp.id} className="bg-white border border-gray-200 rounded p-1.5 flex items-center justify-between hover:bg-gray-50">
                    <div className="text-[11px]">
                      <span className="font-bold text-gray-700">{idx + 1}. {rule?.display}</span>
                    </div>
                    <button onClick={() => onDeleteComponent(comp.id)} className="text-red-400 hover:text-red-600 text-xs">
                      ✕
                    </button>
                  </div>
                );
              })}
            </div>
            <button onClick={onExport} disabled={exporting} className="w-full mt-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-300 text-white font-bold py-1.5 rounded-lg transition-all text-xs">
              {exporting ? '⏳ エクスポート中...' : '⬇️ HTMLエクスポート'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}