// ChatBlock.tsx
import React from 'react';

// ==========================================
// 1. 型定義
// ==========================================

export interface BlockData {
  title?: string;
  data?: unknown;
  content?: unknown;
  [key: string]: unknown;
}

export interface ChatBlockProps {
  block?: BlockData | null;
  className?: string;
}

// ==========================================
// 2. 型ガード & ユーティリティ関数
// ==========================================

/** 値がプレーンなオブジェクト（配列やnullではない）かどうかを判定します */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/** キーのアンダースコアをスペースに変換し、見やすく整形します */
function formatKey(key: string): string {
  return key.replace(/_/g, ' ');
}

// ==========================================
// 3. コンポーネント本体
// ==========================================

export function ChatBlock({ block, className = '' }: ChatBlockProps): React.ReactElement {
  // データの抽出（フォールバック付き）
  const source = block || {};
  const data = source.data ?? source.content ?? {};
  const title = source.title || '詳細情報';

  // データを表示可能かどうかの判定
  const hasData = isRecord(data) && Object.keys(data).length > 0;

  // JSONの各値（文字列、配列、オブジェクト）を再帰的にレンダリング
  const renderValue = (value: unknown, depth = 0): React.ReactNode => {
    // null / undefined
    if (value === null || value === undefined) {
      return <span className="text-slate-400 italic">なし</span>;
    }

    // boolean (バッジ風に表示)
    if (typeof value === 'boolean') {
      return (
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
            value
              ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
              : 'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300'
          }`}
        >
          {value ? 'はい' : 'いいえ'}
        </span>
      );
    }

    // string / number
    if (typeof value === 'string' || typeof value === 'number') {
      return <span className="break-words">{String(value)}</span>;
    }

    // array
    if (Array.isArray(value)) {
      if (value.length === 0) {
        return <span className="text-slate-400 italic">データなし</span>;
      }
      return (
        <ul className="list-disc list-inside space-y-1 mt-1 pl-1">
          {value.map((item, idx) => (
            <li key={idx} className="text-sm">
              {renderValue(item, depth + 1)}
            </li>
          ))}
        </ul>
      );
    }

    // object (ネストされた辞書)
    if (isRecord(value)) {
      const keys = Object.keys(value);
      if (keys.length === 0) {
        return <span className="text-slate-400 italic">空のデータ</span>;
      }

      return (
        <div className="pl-3 mt-1 border-l-2 border-slate-200 dark:border-slate-600 space-y-2">
          {keys.map((k) => (
            <div key={k} className="flex flex-col sm:flex-row sm:gap-2">
              <span className="font-medium text-slate-500 dark:text-slate-400 capitalize min-w-[100px]">
                {formatKey(k)}:
              </span>
              <div className="flex-1">{renderValue(value[k], depth + 1)}</div>
            </div>
          ))}
        </div>
      );
    }

    // その他 (関数など想定外の型へのフォールバック)
    return <span>{String(value)}</span>;
  };

  return (
    <div
      className={`bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 my-4 shadow-sm w-full ${className}`}
    >
      {/* ヘッダー部分 */}
      <h4 className="text-base font-bold text-slate-800 dark:text-slate-100 mb-4 pb-3 border-b border-slate-100 dark:border-slate-700 flex items-center gap-2">
        📄 {title}
      </h4>

      {/* コンテンツ部分 */}
      <div className="text-sm text-slate-700 dark:text-slate-300">
        {hasData ? (
          <div className="space-y-4">
            {Object.entries(data as Record<string, unknown>).map(([key, val]) => (
              <div
                key={key}
                className="flex flex-col sm:flex-row sm:gap-4 pb-4 border-b border-slate-50 dark:border-slate-700/50 last:border-0 last:pb-0"
              >
                {/* キー部分 (左側) */}
                <span className="font-semibold capitalize sm:w-1/3 shrink-0 text-slate-800 dark:text-slate-200">
                  {formatKey(key)}
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

export default ChatBlock;