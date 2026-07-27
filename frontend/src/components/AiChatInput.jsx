// To-main/frontend/src/components/AiChatInput.jsx
import React, { useState } from 'react';

export default function AiChatInput({ onSend, isLoading }) {
  const [inputMessage, setInputMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;
    onSend(inputMessage);
    setInputMessage('');
  };

  return (
    <div className="p-3 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
      <form onSubmit={handleSubmit} className="flex flex-col space-y-2">
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
            {/* <button type="button" className="p-1.5 text-slate-400 hover:text-indigo-600" title="画像添付">🖼️</button> */}
            <button type="submit" disabled={isLoading || !inputMessage.trim()} className="p-1.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white rounded-lg">
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