// frontend/src/components/ZipUploadModal.jsx
import React, { useEffect, useState } from 'react';

export default function ZipUploadModal({ isOpen, file, onClose, onComplete }) {
  // uploading (通信中) -> scanning (バックエンドでRAG・Ollama処理中) -> done (完了) -> error (失敗)
  const [status, setStatus] = useState('uploading'); 
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (isOpen && file) {
      const uploadZipToAI = async () => {
        setStatus('uploading');
        setErrorMessage('');
        
        // 1. ファイルを送信可能な形式(FormData)に変換
        const formData = new FormData();
        formData.append('file', file); // FastAPI側の引数名 'file' と一致

        try {
          // 2. サーバーにZIPを投げる (URLをあなたの ai_server.py に正しく合わせる)
          // パスを相対パス（/api/...）にすることで、環境によるポートズレを防止します
          const response = await fetch('/api/memory/upload-zip', {
            method: 'POST',
            body: formData,
          });
          
          // 通信は成功した直後、バックエンド側で自作RAG（Chunker/Ollama）が走るので
          // ステータスを 'scanning' にして待機アニメーションを動かす
          setStatus('scanning');

          const data = await response.json();

          if (response.ok && data.status === 'success') {
            console.log("🧠 記憶完了:", data);
            setStatus('done');
            if (onComplete) onComplete(data); // 親コンポーネントに成功データを通知
          } else {
            console.error("サーバーエラー:", data.message);
            setErrorMessage(data.message || 'サーバー側で処理に失敗しました。');
            setStatus('error');
          }
        } catch (error) {
          console.error("通信エラー", error);
          setErrorMessage('通信エラーが発生しました。サーバー（FastAPI）が起動しているか確認してください。');
          setStatus('error');
        }
      };

      uploadZipToAI();
    }
  }, [isOpen, file]);

  // モーダルが閉じている時は何も描画しない
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/40 backdrop-blur-sm">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-96 overflow-hidden border border-slate-200 dark:border-slate-700 transform transition-all m-4">
        <div className="p-6 text-center space-y-4">
          
          <h3 className="text-lg font-bold text-slate-800 dark:text-white">
            {status === 'error' ? '⚠️ インポート失敗' : 'プロジェクトを記憶中...'}
          </h3>
          
          <div className="text-xs text-slate-500 font-mono bg-slate-50 dark:bg-slate-900 p-2 rounded truncate">
            {file?.name}
          </div>

          {/* ステータスバーとアニメーション表示 */}
          <div className="space-y-4 mt-4">
            <div className="h-2 w-full bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
              <div 
                className={`h-full bg-indigo-500 transition-all duration-500 ease-out ${
                  status === 'uploading' ? 'w-1/3' : 
                  status === 'scanning' ? 'w-2/3' : 
                  status === 'error' ? 'w-full bg-red-500' : 'w-full bg-emerald-500'
                }`}
              ></div>
            </div>

            <div className="flex justify-center">
              <div className={`text-4xl ${
                status === 'uploading' ? 'animate-bounce' : 
                status === 'scanning' ? 'animate-spin' : ''
              }`}>
                {status === 'uploading' ? '📦' : 
                 status === 'scanning' ? '⚙️' : 
                 status === 'error' ? '❌' : '✨'}
              </div>
            </div>

            {/* ガイドテキスト */}
            <div className="text-sm font-medium text-slate-600 dark:text-slate-300">
              {status === 'uploading' && 'ZIPファイルをサーバーへ転送中...'}
              {status === 'scanning' && 'Ollamaでコードをベクトル化しています...'}
              {status === 'done' && '記憶のインデックス化が完了しました！✨'}
              {status === 'error' && (
                <span className="text-red-500 block text-xs mt-1 font-sans">{errorMessage}</span>
              )}
            </div>
          </div>
        </div>

        {/* フッターボタンエリア（完了時、またはエラー時に表示） */}
        {(status === 'done' || status === 'error') && (
          <div className="p-4 bg-slate-50 dark:bg-slate-900 border-t border-slate-100 dark:border-slate-700">
            <button 
              onClick={onClose}
              className={`w-full py-2 text-white text-sm font-bold rounded-lg transition-colors ${
                status === 'error' ? 'bg-slate-600 hover:bg-slate-700' : 'bg-indigo-600 hover:bg-indigo-700'
              }`}
            >
              {status === 'error' ? '閉じる' : 'チャットに戻る'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}