// frontend/src/components/blocks/HtmlCssPreviewBlock.jsx
import React from 'react';

/**
 * HtmlCssPreviewBlock (改造版)
 * 横幅をコンパクトにし、ヘッダーにアクションを集約。
 * JavaScript (js) の埋め込み・実行にも対応。
 */
export default function HtmlCssPreviewBlock({ block, onOptionSelect, onOpenManualEdit }) {
  // 🌟 バックエンドから js も受け取るように拡張
  const { html, css, js, component_name } = block;

  // iframeの中に流し込むHTMLに <script> タグも同梱する
  const srcDoc = html && html.includes('<!DOCTYPE html>')
    ? html
    : `
      <!DOCTYPE html>
      <html lang="ja">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <style>
            body {
              margin: 0;
              padding: 12px;
              font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
              background-color: transparent;
            }
            ${css || ''}
          </style>
        </head>
        <body>
          ${html || ''}
          
          <script>
            try {
              ${js || ''}
            } catch (e) {
              console.error("Runtime error in dummy JS:", e);
            }
          </script>
        </body>
      </html>
    `;

  return (
    // 🌟 w-full から max-w-sm や max-w-md などのコンパクトなサイズに変更（インラインブロック等で並べやすく）
    <div className="w-full max-w-md border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-white dark:bg-slate-950 shadow-md mt-2 transition-all inline-block text-left">
      
      {/* ヘッダー部分：名前の表示と、アクションボタンをここに凝縮！ */}
      <div className="bg-slate-50 dark:bg-slate-900 px-3 py-2 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center gap-2">
        <span className="flex items-center gap-1.5 text-xs font-bold text-slate-700 dark:text-slate-300 truncate">
          <span>🎨</span> {component_name || "UI Preview"}
        </span>
        
        {/* 🌟 ちょこちょこ配置したいボタン群をヘッダー右側に集約 */}
        <div className="flex items-center space-x-1 flex-shrink-0">
          <button 
            onClick={() => onOptionSelect?.(["AIに修正を依頼する"])}
            title="AIに修正を頼む"
            className="p-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors text-xs flex items-center gap-1"
          >
            <span>🤖</span> <span className="hidden sm:inline">AI修正</span>
          </button>
          
          <button 
            onClick={() => onOpenManualEdit?.(block)}
            title="自分でレイアウトを編集"
            className="p-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-xs flex items-center gap-1 font-medium shadow-sm"
          >
            <span>✏️</span> <span className="hidden sm:inline">手動編集</span>
          </button>
        </div>
      </div>
      
      {/* プレビュー本体（高さも 350px から 220px などのコンパクトに調整） */}
      <div className="p-1.5 bg-slate-50/30 dark:bg-slate-900/10">
        <iframe
          title={component_name || "UI Preview"}
          srcDoc={srcDoc}
          className="w-full h-[220px] border-none bg-white dark:bg-slate-900 rounded-lg border border-slate-100 dark:border-slate-800 shadow-inner"
          sandbox="allow-scripts allow-same-origin" // allow-scripts があるので埋め込んだ JS が動きます
        />
      </div>
      
    </div>
  );
}