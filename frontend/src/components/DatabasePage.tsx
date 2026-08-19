// import console from 'console';
import DatabaseManager from './DatabaseManager';
import React, { useState } from 'react';

// 
// バックエンド (nlp_service.py) の型定義
// 
interface TemplatePart {
  label: string;
  value: string;
  key: string;
}

interface AnalysisResponse {
  type: string;
  title: string;
  icon: string;
  description: string;
  sql: string;
  parts: TemplatePart[];
  input: string;
}

export default function DatabasePage() {
  // NLP処理用のステート
  const [inputText, setInputText] = useState('');
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [partsValues, setPartsValues] = useState<Record<string, string>>({});
  const [finalSql, setFinalSql] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // 1. テキストを送信してテンプレートを解析
  const handleAnalyze = async () => {
    if (!inputText.trim()) return;
    setIsLoading(true);
    setAnalysis(null);
    setFinalSql('');
    
    try {
      // ※実際のエンドポイントURLに合わせて修正してください
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: inputText })
      });
      const data: AnalysisResponse = await res.json();
      setAnalysis(data);

      // 編集用フォームの初期値をセット
      const initialValues: Record<string, string> = {};
      data.parts.forEach(p => {
        initialValues[p.key] = p.value;
      });
      setPartsValues(initialValues);
    } catch (error) {
      console.error('解析エラー:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // 2. 編集したパーツを送信してSQLを再構築
  const handleBuild = async () => {
    if (!analysis) return;
    try {
      // ※実際のエンドポイントURLに合わせて修正してください
      const res = await fetch('/api/build', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: analysis.type, parts: partsValues })
      });
      const data = await res.json();
      setFinalSql(data.sql);
    } catch (error) {
      console.error('構築エラー:', error);
    }
  };

  // パーツの入力値変更ハンドラ
  const handlePartChange = (key: string, value: string) => {
    setPartsValues(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="p-8 bg-gray-50 h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">🗄️ データベース管理</h1>
          <p className="text-gray-500 text-sm">
            AIアシスタントによるSQL生成と、SQLiteデータベースファイルの管理を行います。
          </p>
        </header>

        <div className="grid grid-cols-1 gap-8">
          {/* 
              AI SQL ビルダー (nlp_service連携UI)
           */}
          <section className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
              <span>✨</span> AI SQL ビルダー
            </h2>
            
            <div className="flex gap-2 mb-6">
              <input
                type="text"
                className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="例: 1000円より高い商品をテーブルAの中から取得して"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
              />
              <button
                onClick={handleAnalyze}
                disabled={isLoading}
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                {isLoading ? '解析中...' : 'SQL生成'}
              </button>
            </div>

            {/* 解析結果の動的UI表示 */}
            {analysis && (
              <div className="bg-blue-50/50 border border-blue-100 rounded-xl p-5 mb-4">
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-2xl">{analysis.icon}</span>
                  <h3 className="font-bold text-lg text-blue-900">{analysis.title}</h3>
                </div>
                <p className="text-sm text-blue-700 mb-4">{analysis.description}</p>

                {/* 動的パーツ入力フォーム */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  {analysis.parts.map((part) => (
                    <div key={part.key} className="flex flex-col gap-1">
                      <label className="text-xs font-bold text-gray-600">{part.label}</label>
                      <input
                        type="text"
                        value={partsValues[part.key] || ''}
                        onChange={(e) => handlePartChange(part.key, e.target.value)}
                        className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                      />
                    </div>
                  ))}
                </div>

                <div className="flex justify-end">
                  <button
                    onClick={handleBuild}
                    className="bg-blue-100 hover:bg-blue-200 text-blue-800 px-4 py-2 rounded font-medium text-sm transition-colors"
                  >
                    この内容でSQLを構築
                  </button>
                </div>
              </div>
            )}

            {/* 最終構築されたSQLの表示 */}
            {finalSql && (
              <div className="bg-gray-900 rounded-xl p-4 relative">
                <span className="absolute top-2 right-3 text-xs text-gray-400 font-mono">SQL</span>
                <pre className="text-green-400 font-mono text-sm whitespace-pre-wrap overflow-x-auto pt-4">
                  {finalSql}
                </pre>
              </div>
            )}
          </section>

          {/* メインの管理パネル */}
          <section>
            <DatabaseManager />
          </section>

          {/* 補足情報：使い方のヒント */}
          <div className="bg-gray-50 border border-gray-200 rounded-2xl p-6">
            <h3 className="font-bold text-gray-700 mb-2 flex items-center gap-2">
              <span>💡</span> Tips: 生成したDBの使い方
            </h3>
            <ul className="text-sm text-gray-600 space-y-2 list-disc list-inside">
              <li>ダウンロードした <b>.db</b> ファイルは、DB Browser for SQLite などのツールで中身を閲覧できます。</li>
              <li>上の「AI SQL ビルダー」で構築したSQLを使って、DBを直接操作することも可能です。</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

function fetch(arg0: string, arg1: { method: string; headers: { 'Content-Type': string; }; body: string; }) {
  throw new Error('Function not implemented.');
}
