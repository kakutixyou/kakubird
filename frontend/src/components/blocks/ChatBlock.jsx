import React from 'react';

export default function ChatBlock({ block }) {
  // block.data または block.content に表示したいJSONオブジェクトが入っていると想定
  const data = block.data || block.content || {};
  const title = block.title || '詳細情報';

  // JSONの各値（文字列、配列、オブジェクト）を人間が読みやすい形式に変換する再帰関数
  const renderValue = (value) => {
    // null / undefined の処理
    if (value === null || value === undefined) {
      return <span className="text-slate-400 italic">なし</span>;
    }
    // 真偽値の処理
    if (typeof value === 'boolean') {
      return <span>{value ? 'はい' : 'いいえ'}</span>;
    }
    // 文字列・数値の処理
    if (typeof value === 'string' || typeof value === 'number') {
      return <span className="break-words">{value}</span>;
    }
    
    // 配列の処理 (リスト表示)
    if (Array.isArray(value)) {
      if (value.length === 0) return <span className="text-slate-400">データなし</span>;
      return (
        <ul className="list-disc list-inside space-y-1 mt-1 pl-1">
          {value.map((item, idx) => (
            <li key={idx} className="text-sm">
              {renderValue(item)}
            </li>
          ))}
        </ul>
      );
    }

    // ネストされたオブジェクトの処理
    if (typeof value === 'object') {
      const keys = Object.keys(value);
      if (keys.length === 0) return <span className="text-slate-400">空のデータ</span>;
      
      return (
        <div className="pl-3 mt-1 border-l-2 border-slate-200 dark:border-slate-600 space-y-2">
          {keys.map((k) => (
            <div key={k} className="flex flex-col sm:flex-row sm:gap-2">
              <span className="font-medium text-slate-500 dark:text-slate-400 capitalize min-w-[100px]">
                {/* アンダースコアをスペースに変換して見やすく */}
                {k.replace(/_/g, ' ')}:
              </span>
              <div className="flex-1">{renderValue(value[k])}</div>
            </div>
          ))}
        </div>
      );
    }

    return <span>{String(value)}</span>;
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-md border border-slate-200 dark:border-slate-700 p-4 my-2 shadow-sm w-full">
      {/* ブロックのタイトル */}
      {title && (
        <h4 className="text-md font-bold text-slate-800 dark:text-slate-100 mb-3 pb-2 border-b border-slate-100 dark:border-slate-700 flex items-center gap-2">
          📄 {title}
        </h4>
      )}
      
      {/* JSONデータを人間向けにレンダリング */}
      <div className="text-sm text-slate-700 dark:text-slate-300">
        {typeof data === 'object' && Object.keys(data).length > 0 ? (
          <div className="space-y-3">
            {Object.entries(data).map(([key, val]) => (
              <div 
                key={key} 
                className="flex flex-col sm:flex-row sm:gap-4 pb-3 border-b border-slate-100 dark:border-slate-700 last:border-0 last:pb-0"
              >
                {/* キー部分 (左側) */}
                <span className="font-semibold capitalize sm:w-1/3 shrink-0 text-slate-800 dark:text-slate-200">
                  {key.replace(/_/g, ' ')}
                </span>
                {/* バリュー部分 (右側) */}
                <div className="sm:w-2/3">
                  {renderValue(val)}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-slate-500 italic">表示できるデータがありません。</p>
        )}
      </div>
    </div>
  );
}