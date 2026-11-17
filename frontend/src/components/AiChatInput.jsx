import React, { useState } from 'react';

export default function AiChatInput({ onSend, isLoading }) {
  const [inputMessage, setInputMessage] = useState('');
  const [selectedModel, setSelectedModel] = useState('gemini');
  const [copied, setCopied] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;
    
    // 選択されたモデルを親(AiChatPanel/useAiChat)へ渡す
    onSend(inputMessage, selectedModel);
    setInputMessage('');
  };

  const handleCopyPrompt = async () => {
    if (!inputMessage.trim()) return;
    try {
      await navigator.clipboard.writeText(inputMessage);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy', err);
    }
  };

  return (
    <div className="p-3 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
      <form onSubmit={handleSubmit} className="flex flex-col space-y-2">
        
        {/* モデル選択 & コピーボタンのツールバー */}
        <div className="flex justify-between items-center px-1">
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="text-xs bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 rounded-md px-2 py-1 outline-none focus:ring-1 focus:ring-indigo-500 transition-colors"
          >
            <option value="gemini">Gemini</option>
            <option value="ollama">Ollama (Local)</option>
            <option value="to_model">To Model (Custom)</option>
          </select>

          <button
            type="button"
            onClick={handleCopyPrompt}
            disabled={!inputMessage.trim()}
            className="text-xs text-slate-500 hover:text-indigo-600 dark:hover:text-indigo-400 disabled:opacity-30 transition-colors"
            title="プロンプトをコピー"
          >
            {copied ? '✅ コピー完了' : '📋 プロンプトをコピー'}
          </button>
        </div>

        <div className="relative flex items-center">
          <textarea
            rows={2}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            placeholder="SQLの質問や /css コマンドを入力..."
            className="w-full resize-none pl-3 pr-20 py-2 text-sm bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
          />
          <div className="absolute right-2 bottom-2 flex items-center space-x-1">
            <button 
              type="submit" 
              disabled={isLoading || !inputMessage.trim()} 
              className="p-1.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 dark:disabled:bg-slate-700 text-white rounded-lg transition-colors"
            >
              ↑
            </button>
          </div>
        </div>
        <div className="flex justify-between items-center px-1">
          <span className="text-[10px] text-slate-400">💡 /css 月光の第三楽章みたいなCSSを作ってほしい</span>
          <span className="text-[10px] text-slate-400">Shift + Enter で改行</span>
        </div>
      </form>
    </div>
  );
}