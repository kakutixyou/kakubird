import Editor from "@monaco-editor/react";
import React, { useState, useEffect } from 'react';
interface Props {
  isOpen: boolean;
  initialHtml: string;
  initialCss: string;
  componentName: string;
  onClose: () => void;
  onSave: (html: string, css: string, name: string) => void;
}

export default function HtmlManualEditModal({ isOpen, initialHtml, initialCss, componentName, onClose, onSave }: Props) {
  const [html, setHtml] = useState(initialHtml);
  const [css, setCss] = useState(initialCss);
  const [name, setName] = useState(componentName);

  if (!isOpen) return null;

  // iframeに流し込むための結合プレビュー用コード
  const previewSrcDoc = `
    <!DOCTYPE html>
    <html>
      <head>
        <style>${css}</style>
      </head>
      <body>${html}</body>
    </html>
  `;

  return (
    // 🌟 画面全体を覆うフルスクリーン設定（fixed inset-0 z-50）
    <div className="fixed inset-0 z-50 bg-gray-900 text-white flex flex-col font-sans">
      
      {/* 🌟 上部ヘッダー（操作バー） */}
      <div className="flex justify-between items-center bg-gray-800 px-6 py-3 border-b border-gray-700">
        <div className="flex items-center gap-4">
          <button onClick={onClose} className="text-gray-400 hover:text-white transition">
            ✕ 閉じる
          </button>
          <input 
            type="text" 
            value={name} 
            onChange={(e) => setName(e.target.value)}
            className="bg-gray-700 text-white px-3 py-1 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="コンポーネント名"
          />
        </div>
        <button 
          onClick={() => onSave(html, css, name)}
          className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded-md font-bold shadow-lg transition-transform hover:scale-105"
        >
          💾 保存してキャンバスへ追加
        </button>
      </div>

      {/* 🌟 メインコンテンツ（左右2カラム分割） */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* 左側：コード編集エリア (50%) */}
        <div className="w-1/2 flex flex-col border-r border-gray-700 bg-[#1e1e1e]">
          
          {/* HTML入力 */}
          <div className="flex-1 flex flex-col border-b border-gray-700">
            <div className="bg-gray-800 text-xs font-bold px-4 py-2 text-gray-400">HTML</div>
          <Editor
            height="100%"
            defaultLanguage="html"
            theme="vs-dark"
            value={html}
            onChange={(value) => setHtml(value || '')}
          />
          </div>

          {/* CSS入力 */}
          <div className="flex-1 flex flex-col">
            <div className="bg-gray-800 text-xs font-bold px-4 py-2 text-gray-400">CSS</div>
            <textarea
              value={css}
              onChange={(e) => setCss(e.target.value)}
              className="flex-1 bg-transparent text-gray-100 p-4 font-mono text-sm resize-none focus:outline-none"
              spellCheck={false}
            />
          </div>
        </div>

        {/* 右側：リアルタイムプレビューエリア (50%) */}
        <div className="w-1/2 bg-gray-100 flex flex-col">
          <div className="bg-white text-xs font-bold px-4 py-2 text-gray-500 border-b shadow-sm flex justify-between">
            <span>LIVE PREVIEW</span>
            <span>📱 🖥️</span> {/* ここにスマホ・PCの切り替えボタンを置いても面白いです */}
          </div>
          <iframe
            title="Live Preview"
            srcDoc={previewSrcDoc}
            className="w-full h-full border-none bg-white"
            sandbox="allow-scripts allow-same-origin"
          />
        </div>

      </div>
    </div>
  );
}
interface HtmlManualEditModalProps {
  isOpen: boolean;
  initialHtml: string;
  initialCss: string;
  initialJs?: string; // オプション（未指定時は空文字）
  componentName: string;
  onClose: () => void;
  onSave: (html: string, css: string, componentName: string, js: string) => void;
}

type TabType = 'html' | 'css' | 'js';

// export default function HtmlManualEditModal({
//   isOpen,
//   initialHtml,
//   initialCss,
//   initialJs = '',
//   componentName,
//   onClose,
//   onSave
// }: HtmlManualEditModalProps) {
//   // エディタ内の状態管理
//   const [html, setHtml] = useState(initialHtml);
//   const [css, setCss] = useState(initialCss);
//   const [js, setJs] = useState(initialJs);
//   const [name, setName] = useState(componentName);
  
//   // アクティブな編集タブ管理
//   const [activeTab, setActiveTab] = useState<TabType>('html');

//   // モーダルが開くたびに初期値を同期
//   useEffect(() => {
//     if (isOpen) {
//       setHtml(initialHtml);
//       setCss(initialCss);
//       setJs(initialJs);
//       setName(componentName);
//     }
//   }, [isOpen, initialHtml, initialCss, initialJs, componentName]);

//   if (!isOpen) return null;

//   // 🌟 右側のリアルタイムプレビュー用 iframe に流し込む HTML の組み立て
//   const srcDoc = `
//     <!DOCTYPE html>
//     <html lang="ja">
//       <head>
//         <meta charset="UTF-8">
//         <style>
//           body {
//             margin: 0;
//             padding: 16px;
//             font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
//             background-color: #ffffff;
//           }
//           ${css}
//         </style>
//       </head>
//       <body>
//         ${html}
//         <script>
//           try {
//             ${js}
//           } catch (e) {
//             console.error("Runtime error in modal JS:", e);
//           }
//         </script>
//       </body>
//     </html>
//   `;

//   const handleSaveClick = () => {
//     // 親の Builder.tsx に編集後のデータを引き渡してキャンバスへ反映
//     onSave(html, css, name, js);
//   };

//   return (
//     <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm transition-all animate-fadeIn">
      
//       {/* モーダルウィンドウ本体（大画面を活かす特大サイズ） */}
//       <div className="flex flex-col w-full max-w-6xl h-[85vh] bg-white dark:bg-slate-950 rounded-2xl shadow-2xl overflow-hidden border border-slate-200 dark:border-slate-800">
        
//         {/* 1. ヘッダーエリア（コンポーネント名の変更に対応） */}
//         <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900">
//           <div className="flex items-center space-x-3 flex-1 max-w-md">
//             <span className="text-xl">🛠️</span>
//             <div className="flex-1">
//               <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold">Component Name</label>
//               <input
//                 type="text"
//                 value={name}
//                 onChange={(e) => setName(e.target.value)}
//                 className="w-full bg-transparent border-b border-transparent hover:border-slate-300 focus:border-blue-500 font-semibold text-slate-800 dark:text-slate-100 focus:outline-none transition-colors text-sm py-0.5"
//                 placeholder="コンポーネント名を入力..."
//               />
//             </div>
//           </div>
//           <button
//             onClick={onClose}
//             className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors p-1"
//           >
//             <span className="text-xl">&times;</span>
//           </button>
//         </div>

//         {/* 2. メインエディタ＆プレビュー（左右スプリットレイアウト） */}
//         <div className="flex flex-1 overflow-hidden w-full">
          
//           {/* 💻 左半分：コードエディタ領域 */}
//           <div className="w-1/2 flex flex-col border-r border-slate-200 dark:border-slate-800 h-full">
//             {/* エディタタブ選択バー */}
//             <div className="flex bg-slate-100 dark:bg-slate-900/50 p-1 border-b border-slate-200 dark:border-slate-800 text-xs font-mono">
//               {(['html', 'css', 'js'] as TabType[]).map((tab) => (
//                 <button
//                   key={tab}
//                   onClick={() => setActiveTab(tab)}
//                   className={`px-4 py-2 rounded-lg font-bold transition-all uppercase ${
//                     activeTab === tab
//                       ? 'bg-white dark:bg-slate-800 text-blue-600 dark:text-blue-400 shadow-sm'
//                       : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-300'
//                   }`}
//                 >
//                   {tab === 'html' && '📄 HTML'}
//                   {tab === 'css' && '🎨 CSS'}
//                   {tab === 'js' && '⚡ JavaScript'}
//                 </button>
//               ))}
//             </div>

//             {/* コード入力エリア */}
//             <div className="flex-1 bg-slate-950 p-2 font-mono text-xs relative">
//               {activeTab === 'html' && (
//                 <textarea
//                   value={html}
//                   onChange={(e) => setHtml(e.target.value)}
//                   className="w-full h-full bg-transparent text-emerald-400 focus:outline-none p-2 resize-none leading-relaxed overflow-y-auto"
//                   placeholder=""
//                 />
//               )}
//               {activeTab === 'css' && (
//                 <textarea
//                   value={css}
//                   onChange={(e) => setCss(e.target.value)}
//                   className="w-full h-full bg-transparent text-amber-400 focus:outline-none p-2 resize-none leading-relaxed overflow-y-auto"
//                   placeholder="/* CSSスタイルを記述してください */"
//                 />
//               )}
//               {activeTab === 'js' && (
//                 <textarea
//                   value={js}
//                   onChange={(e) => setJs(e.target.value)}
//                   className="w-full h-full bg-transparent text-sky-400 focus:outline-none p-2 resize-none leading-relaxed overflow-y-auto"
//                   placeholder="// スクリプトやイベントリスナーを記述してください"
//                 />
//               )}
//             </div>
//           </div>

//           {/* 🖥️ 右半分：ライブプレビュー領域（コードの変更が即時反映） */}
//           <div className="w-1/2 h-full bg-slate-100 dark:bg-slate-900/20 p-4 flex flex-col overflow-hidden">
//             <div className="text-[10px] uppercase font-bold tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
//               <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
//               Live Interactive Preview
//             </div>
//             <div className="flex-1 bg-white rounded-xl shadow-inner border border-slate-200 dark:border-slate-800 overflow-hidden relative">
//               <iframe
//                 title="Modal Live Preview"
//                 srcDoc={srcDoc}
//                 className="w-full h-full border-none bg-white"
//                 sandbox="allow-scripts allow-same-origin"
//               />
//             </div>
//           </div>

//         </div>

//         {/* 3. フッターアクションバー */}
//         <div className="flex justify-end space-x-2 px-6 py-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-xs">
//           <button
//             onClick={onClose}
//             className="px-4 py-2.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-700 font-semibold transition-colors"
//           >
//             キャンセル
//           </button>
//           <button
//             onClick={handleSaveClick}
//             className="px-4 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 font-bold shadow-md shadow-blue-500/10 transition-colors"
//           >
//             編集を確定してキャンバスへ反映 🚀
//           </button>
//         </div>

//       </div>
//     </div>
//   );
// }