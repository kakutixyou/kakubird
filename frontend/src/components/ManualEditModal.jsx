import React, { useEffect, useRef, useState } from 'react';

/*
 ManualEditModal.jsx

 Props:
  - isOpen: boolean
  - blockData: object (期待例: { html: '<div>...</div>', css: '.c{...}' , title: '...' })
  - onClose: () => void
  - onSave: (updatedHtml: string, updatedCss: string) => void
*/

export default function ManualEditModal({ isOpen, blockData, onClose, onSave }) {
  const initialHtml = (blockData && (blockData.html || blockData.content?.html || blockData.content?.message || '')) || '';
  const initialCss = (blockData && (blockData.css || blockData.content?.css || '')) || '';
  const [html, setHtml] = useState(String(initialHtml));
  const [css, setCss] = useState(String(initialCss));
  const [activeTab, setActiveTab] = useState('preview'); // 'preview' | 'html' | 'css'
  const [isDirty, setIsDirty] = useState(false);
  const iframeRef = useRef(null);
  const modalRef = useRef(null);

  // Sync incoming blockData -> editor fields when modal opens or blockData changes
  useEffect(() => {
    if (isOpen) {
      setHtml(String(initialHtml));
      setCss(String(initialCss));
      setIsDirty(false);
      setActiveTab('preview');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, blockData]);

  // update dirty flag
  useEffect(() => {
    setIsDirty(html !== String(initialHtml) || css !== String(initialCss));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [html, css]);

  // keyboard shortcuts: Esc closes, Ctrl/Cmd+Enter saves
  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e) => {
      if ((e.key === 'Escape')) {
        e.preventDefault();
        onClose && onClose();
      }
      if ((e.key === 'Enter' && (e.metaKey || e.ctrlKey))) {
        e.preventDefault();
        handleSave();
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, html, css]);

  // build iframe srcdoc for preview
  const buildSrcDoc = () => {
    return `
      <!doctype html>
      <html>
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width,initial-scale=1" />
          <style>
            html,body{margin:0;padding:12px;font-family:Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;}
            ${css}
          </style>
        </head>
        <body>
          ${html}
        </body>
      </html>
    `;
  };

  const handleSave = () => {
    try {
      onSave && onSave(html, css);
      setIsDirty(false);
      onClose && onClose();
    } catch (e) {
      console.error('ManualEditModal: save failed', e);
    }
  };

  const handleCopyHtml = async () => {
    try {
      await navigator.clipboard.writeText(html);
    } catch (e) {
      console.error('copy html failed', e);
    }
  };

  const handleCopyCss = async () => {
    try {
      await navigator.clipboard.writeText(css);
    } catch (e) {
      console.error('copy css failed', e);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([`<style>${css}</style>\n${html}`], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const filename = (blockData && (blockData.filename || blockData.title)) ? `${(blockData.filename || blockData.title)}.html` : `manual-edit-${Date.now()}.html`;
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  // Prevent background scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      const prevOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => { document.body.style.overflow = prevOverflow; };
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      ref={modalRef}
      className="fixed inset-0 z-60 flex items-center justify-center px-4 py-6"
      role="dialog"
      aria-modal="true"
    >
      {/* Backdrop: blur を削除して半透明だけにする */}
      <div
        className="fixed inset-0 bg-black/40"
        onClick={() => onClose && onClose()}
      />

      {/* Modal panel: z を高めにして確実にバックドロップより上に出す */}
      <div className="relative z-[90] w-full max-w-6xl max-h-[90vh] bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border dark:border-slate-800 overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b dark:border-slate-800">
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-semibold">{(blockData && (blockData.title || blockData.filename)) || '手動レイアウト編集'}</h3>
            <span className="text-sm text-slate-500 dark:text-slate-400">リアルタイムプレビュー付き</span>
            {isDirty && <span className="ml-2 inline-block text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">未保存</span>}
          </div>

          <div className="flex items-center gap-2">
            <button
              className="text-sm px-3 py-1 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700"
              onClick={() => { handleCopyHtml(); }}
              title="HTML をクリップボードにコピー"
            >
              Copy HTML
            </button>
            <button
              className="text-sm px-3 py-1 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700"
              onClick={() => { handleCopyCss(); }}
              title="CSS をクリップボードにコピー"
            >
              Copy CSS
            </button>
            <button
              className="text-sm px-3 py-1 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700"
              onClick={handleDownload}
              title="ダウンロード"
            >
              Download
            </button>
            <button
              className="ml-2 text-sm px-3 py-1 rounded bg-red-50 text-red-700 hover:bg-red-100"
              onClick={() => onClose && onClose()}
              title="Close"
            >
              閉じる
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 flex min-h-0 overflow-hidden">
          {/* Left column: editors */}
          <div className="w-1/2 min-w-[320px] border-r dark:border-slate-800 flex flex-col overflow-hidden">
            <div className="flex items-center gap-2 p-2 border-b dark:border-slate-800 bg-slate-50 dark:bg-slate-900/40">
              <button
                className={`px-3 py-1 rounded ${activeTab === 'preview' ? 'bg-white dark:bg-slate-800 shadow' : 'bg-transparent'}`}
                onClick={() => setActiveTab('preview')}
              >
                Preview
              </button>
              <button
                className={`px-3 py-1 rounded ${activeTab === 'html' ? 'bg-white dark:bg-slate-800 shadow' : 'bg-transparent'}`}
                onClick={() => setActiveTab('html')}
              >
                HTML
              </button>
              <button
                className={`px-3 py-1 rounded ${activeTab === 'css' ? 'bg-white dark:bg-slate-800 shadow' : 'bg-transparent'}`}
                onClick={() => setActiveTab('css')}
              >
                CSS
              </button>
            </div>

            <div className="flex-1 overflow-auto p-3">
              {activeTab === 'preview' && (
                <div className="flex flex-col gap-2">
                  <div className="text-sm text-slate-500 dark:text-slate-400 mb-2">編集中のプレビュー（Preview タブ）</div>
                  <div className="h-[480px] border rounded overflow-hidden">
                    <iframe
                      ref={iframeRef}
                      title="manual-edit-preview"
                      srcDoc={buildSrcDoc()}
                      className="w-full h-full"
                      sandbox="allow-scripts allow-same-origin"
                    />
                  </div>
                </div>
              )}

              {activeTab === 'html' && (
                <div className="flex flex-col h-full">
                  <div className="text-xs text-slate-500 dark:text-slate-400 mb-2">HTML を編集してください</div>
                  <textarea
                    value={html}
                    onChange={(e) => setHtml(e.target.value)}
                    className="flex-1 w-full resize-none p-3 bg-white dark:bg-slate-900 border dark:border-slate-800 rounded font-mono text-sm leading-5"
                    spellCheck={false}
                  />
                </div>
              )}

              {activeTab === 'css' && (
                <div className="flex flex-col h-full">
                  <div className="text-xs text-slate-500 dark:text-slate-400 mb-2">CSS を編集してください</div>
                  <textarea
                    value={css}
                    onChange={(e) => setCss(e.target.value)}
                    className="flex-1 w-full resize-none p-3 bg-white dark:bg-slate-900 border dark:border-slate-800 rounded font-mono text-sm leading-5"
                    spellCheck={false}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Right column: live preview + controls */}
          <div className="flex-1 min-w-0 flex flex-col">
            <div className="p-3 border-b dark:border-slate-800 flex items-center justify-between">
              <div className="text-sm text-slate-500 dark:text-slate-400">ライブプレビュー</div>
              <div className="text-xs text-slate-400">Ctrl/Cmd+Enter で保存 • Esc で閉じる</div>
            </div>

            <div className="flex-1 overflow-auto p-3">
              <div className="w-full h-full border rounded overflow-hidden">
                <iframe
                  title="manual-edit-live"
                  srcDoc={buildSrcDoc()}
                  className="w-full h-full"
                  sandbox="allow-scripts allow-same-origin"
                />
              </div>
            </div>

            <div className="px-4 py-3 border-t dark:border-slate-800 flex items-center justify-between">
              <div className="text-sm text-slate-500">
                {blockData && blockData.id && <span className="mr-3">ID: {String(blockData.id)}</span>}
                {blockData && blockData.source && <span className="mr-3">Source: {blockData.source}</span>}
              </div>

              <div className="flex items-center gap-2">
                <button
                  className="px-4 py-2 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-sm"
                  onClick={() => {
                    setActiveTab('preview');
                    setTimeout(() => {
                      if (iframeRef.current) iframeRef.current.srcdoc = buildSrcDoc();
                    }, 50);
                  }}
                >
                  リフレッシュ
                </button>

                <button
                  className="px-4 py-2 rounded bg-white dark:bg-slate-700 border dark:border-slate-600 text-sm hover:shadow"
                  onClick={() => {
                    onClose && onClose();
                  }}
                >
                  キャンセル
                </button>

                <button
                  className="px-4 py-2 rounded bg-blue-600 text-white text-sm hover:bg-blue-700"
                  onClick={handleSave}
                >
                  保存
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}