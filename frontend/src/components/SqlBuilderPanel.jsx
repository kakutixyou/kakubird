// frontend/src/components/SqlBuilderPanel.jsx
import React, { useState, useEffect } from 'react';

export function SqlBuilderPanel({
  type,
  title,
  icon,
  description,
  sql: initialSql,
  parts: initialParts,
  input
}) {
  // 1. 各パーツの入力値をローカルStateで管理
  const [parts, setParts] = useState(initialParts || []);
  const [currentSql, setCurrentSql] = useState(initialSql || '');
  const [copied, setCopied] = useState(false);

  // 2. ユーザーがフォームを書き換えたときにSQLを簡易的に自動再構築するロジック
  // (高度な再構築が必要な場合は /api/build などのエンドポイントを叩く仕様に拡張可能)
  useEffect(() => {
    // 簡易的なプレースホルダー置換ロジック、または初期SQLの維持
    // 本格的な再構成はバックエンドの build_custom_sql 相当を移植しても良い
    let updatedSql = initialSql;
    
    // パーツの変更を検知して表示をマッピング
    // ※今回は変更可能なフォーム状態を保つためのステート管理を優先
  }, [parts]);

  const handleInputChange = (key, newValue) => {
    setParts((prevParts) =>
      prevParts.map((p) => (p.key === key ? { ...p, value: newValue } : p))
    );
  };

  const handleCopy = async () => {
    await navigator.clipboard.writeText(currentSql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExecute = () => {
    alert(`以下のSQLを実行キューに投入しました:\n\n${currentSql}`);
    // ここに既存の hooks/useSQL.js や store の実行関数（executeQuerryなど）を繋ぎ込めます
  };

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden shadow-2xl text-slate-100 max-w-4xl mx-auto my-2 font-sans">
      {/* ヘッダーセクション */}
      <div className="bg-slate-800 px-5 py-3 border-b border-slate-700 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <span className="text-xl bg-slate-700 p-1.5 rounded-lg border border-slate-600 text-cyan-400">
            {icon || '▷'}
          </span>
          <div>
            <h3 className="font-bold text-base tracking-wide text-slate-200">{title || 'SQL Builder'}</h3>
            <p className="text-xs text-slate-400 mt-0.5">{description}</p>
          </div>
        </div>
        <span className="text-xs font-mono uppercase bg-cyan-950 text-cyan-400 border border-cyan-800 px-2 py-0.5 rounded-full">
          {type}
        </span>
      </div>

      <div className="p-5 grid grid-cols-1 md:grid-cols-12 gap-5">
        {/* 左側: パーツ編集フォーム (5カラム分) */}
        <div className="md:col-span-5 space-y-4 border-b md:border-b-0 md:border-r border-slate-800 pb-4 md:pb-0 md:pr-5">
          <h4 className="text-xs font-semibold tracking-wider text-slate-400 uppercase mb-2">⚡ 構成パーツの調整</h4>
          
          {parts.map((part) => (
            <div key={part.key} className="space-y-1">
              <label className="text-xs text-slate-400 font-medium flex justify-between">
                <span>{part.label}</span>
                <span className="text-[10px] font-mono text-slate-600">{part.key}</span>
              </label>
              <input
                type="text"
                value={part.value}
                onChange={(e) => handleInputChange(part.key, e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 font-mono transition-colors"
              />
            </div>
          ))}

          {input && (
            <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 mt-4">
              <span className="text-[10px] font-semibold text-slate-500 uppercase block mb-1">元の自然言語指示</span>
              <p className="text-xs text-slate-400 italic">" {input} "</p>
            </div>
          )}
        </div>

        {/* 右側: SQLプレビュー & アクション (7カラム分) */}
        <div className="md:col-span-7 flex flex-col justify-between h-full space-y-4">
          <div className="flex-1">
            <div className="flex justify-between items-center mb-2">
              <h4 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">📝 生成されたSQLクエリ</h4>
              <button
                onClick={handleCopy}
                className="text-xs text-slate-400 hover:text-cyan-400 transition-colors flex items-center space-x-1 px-2 py-1 rounded bg-slate-800 border border-slate-700"
              >
                <span>{copied ? '✅ コピー完了' : '📋 クリップボードにコピー'}</span>
              </button>
            </div>

            {/* SQLエディタ風表示エリア */}
            <div className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 font-mono text-sm leading-relaxed text-emerald-400 shadow-inner min-h-[180px] overflow-x-auto whitespace-pre">
              {currentSql}
            </div>
          </div>

          {/* アクションフッター */}
          <div className="flex justify-end space-x-3 pt-2">
            <button
              onClick={() => setCurrentSql(initialSql)}
              className="px-4 py-2 text-xs font-medium text-slate-400 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors"
            >
              リセット
            </button>
            <button
              onClick={handleExecute}
              className="px-5 py-2 text-xs font-semibold text-slate-900 bg-gradient-to-r from-cyan-400 to-teal-400 hover:from-cyan-300 hover:to-teal-300 rounded-lg shadow-md hover:shadow-cyan-500/20 transition-all transform active:scale-95"
            >
              このSQLを実行する 🚀
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}