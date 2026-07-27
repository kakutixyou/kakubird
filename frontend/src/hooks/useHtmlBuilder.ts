import { useState, useCallback } from 'react';
import toast from 'react-hot-toast';
import { DEFAULT_HTML_RULES, generateHtmlFromRule, HtmlRule } from '../data/htmlRules';

export interface GeneratedComponent {
  id: string;
  ruleId: string;
  html: string;
  values: Record<string, string>;
  timestamp: number;
}

export function useHtmlBuilder(pageTitle?: string) {
  const [htmlRules] = useState<HtmlRule[]>(DEFAULT_HTML_RULES);
  const [selectedRuleId, setSelectedRuleId] = useState<string>('');
  const [ruleInputs, setRuleInputs] = useState<Record<string, string>>({});
  const [generatedComponents, setGeneratedComponents] = useState<GeneratedComponent[]>([]);
  const [previewHtml, setPreviewHtml] = useState<string>('');
  const [exporting, setExporting] = useState(false);

  // 手動生成ロジック
  const handleGenerateComponent = useCallback(() => {
    const selectedRule = htmlRules.find(r => r.id === selectedRuleId);
    if (!selectedRule) {
      toast.error('ルールを選択してください');
      return;
    }

    const missingInputs = selectedRule.inputs.filter(
      input => !ruleInputs[input.key]?.trim()
    );

    if (missingInputs.length > 0) {
      toast.error(`必須項目を入力してください: ${missingInputs.map(i => i.label).join(', ')}`);
      return;
    }

    const html = generateHtmlFromRule(selectedRule, ruleInputs);
    const newComponent: GeneratedComponent = {
      id: `comp_${Date.now()}`,
      ruleId: selectedRule.id,
      html,
      values: { ...ruleInputs },
      timestamp: Date.now()
    };

    setGeneratedComponents(prev => [...prev, newComponent]);
    setPreviewHtml(html);
    setRuleInputs({});
    toast.success(`${selectedRule.display} を生成しました`);
  }, [htmlRules, selectedRuleId, ruleInputs]);

  // AIからの追加コマンド処理
  const handleAiCommand = useCallback((cmd: any) => {
    if (cmd?.action === 'ADD_COMPONENT' && cmd.ruleId) {
      const targetRule = htmlRules.find(r => r.id === cmd.ruleId);
      if (!targetRule) {
        toast.error(`不明なルールです: ${cmd.ruleId}`);
        return;
      }

      const values = cmd.values || {};
      const html = generateHtmlFromRule(targetRule, values);
      const newComponent: GeneratedComponent = {
        id: `comp_ai_${Date.now()}`,
        ruleId: targetRule.id,
        html,
        values,
        timestamp: Date.now()
      };

      setGeneratedComponents(prev => [...prev, newComponent]);
      setPreviewHtml(html);
      toast.success(`🤖 AIが「${targetRule.display}」を追加しました！`);
    }
  }, [htmlRules]);

  // 削除ロジック
  const deleteGeneratedComponent = useCallback((id: string) => {
    setGeneratedComponents(prev => {
      const updated = prev.filter(c => c.id !== id);
      setPreviewHtml(updated.length > 0 ? updated[updated.length - 1].html : '');
      return updated;
    });
    toast.success('コンポーネントを削除しました');
  }, []);

  // エクスポートロジック
  const exportAsHtml = useCallback(() => {
    if (generatedComponents.length === 0) {
      toast.error('生成済みのコンポーネントがありません');
      return;
    }

    try {
      setExporting(true);
      const fullHtml = `<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${pageTitle || 'Exported Page'}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.6; color: #333; }
        .hero { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; display: flex; align-items: center; justify-content: center; text-align: center; }
        .card { background: white; border-radius: 0.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding: 1.5rem; }
    </style>
</head>
<body>
${generatedComponents.map(comp => comp.html).join('\n')}
</body>
</html>`;

      const blob = new Blob([fullHtml], { type: 'text/html;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `${pageTitle || 'page'}.html`;
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      toast.success('HTMLをエクスポートしました');
    } catch (err) {
      toast.error('エクスポートに失敗しました');
    } finally {
      setExporting(false);
    }
  }, [generatedComponents, pageTitle]);

  // ページ切り替え時のリセット処理
  const resetBuilderState = useCallback(() => {
    setSelectedRuleId('');
    setRuleInputs({});
    setGeneratedComponents([]);
    setPreviewHtml('');
  }, []);

  return {
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
  };
}