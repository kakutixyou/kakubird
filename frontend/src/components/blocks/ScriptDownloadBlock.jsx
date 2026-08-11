import React from 'react';

export default function ScriptDownloadBlock({ fileName = 'extracted.js', code }) {
  
  // ダウンロードを実行する関数
  const handleDownload = () => {
    // 1. コードをBlob（ファイルデータ）に変換
    const blob = new Blob([code], { type: 'text/javascript' });
    
    // 2. ダウンロード用の仮のURLを発行
    const url = URL.createObjectURL(blob);
    
    // 3. 見えない <a> タグを作って強制的にクリックさせる
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName; // ここで保存されるファイル名を指定
    document.body.appendChild(a);
    a.click();
    
    // 4. お掃除
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-slate-900 rounded-lg p-4 text-slate-200 border border-slate-700">
      <div className="flex justify-between items-center mb-2">
        <span className="font-mono text-sm text-green-400">📦 抽出されたスクリプト: {fileName}</span>
        <button
          onClick={handleDownload}
          className="bg-blue-600 hover:bg-blue-500 text-white px-3 py-1 rounded text-sm font-semibold transition"
        >
          JSをダウンロード
        </button>
      </div>
      
      {/* コードのプレビュー（長すぎる場合はスクロール） */}
      <pre className="bg-black/50 p-3 rounded text-xs font-mono overflow-x-auto max-h-64 overflow-y-auto">
        <code>{code}</code>
      </pre>
    </div>
  );
}