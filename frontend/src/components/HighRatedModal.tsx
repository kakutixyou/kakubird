// frontend/src/components/HighRatedModal.tsx
import React, { useEffect, useRef, useState } from 'react';
import { useHighRated } from '../hooks/useHighRated';
import type { RatingKind, RatingSource } from '../types/highRated';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  initialKind?: RatingKind;
  fixed?: boolean; // MarkdownChatBlock等から呼ぶ時に画面全体に被せるためのオプション
}

const SOURCE_TABS: { value: RatingSource; label: string }[] = [
  { value: 'auto', label: 'To高評価(自動)' },
  { value: 'user_like', label: 'あなたの👍' },
];

const KIND_TABS: { value: RatingKind; label: string }[] = [
  { value: 'pun', label: 'ダジャレ' },
  { value: 'pattern', label: '回答パターン' },
];

const tabClass = (active: boolean, color: string) =>
  `rounded-md px-3 py-1.5 text-sm font-semibold transition ${
    active
      ? `${color} text-white shadow`
      : 'text-slate-600 hover:bg-white dark:text-slate-300 dark:hover:bg-slate-700'
  }`;

export default function HighRatedModal({ isOpen, onClose, initialKind = 'pattern', fixed = false }: Props) {
  // 💡 初期表示を「あなたの👍(user_like)」と指定されたkind（デフォルト'pattern'）に変更
  const [source, setSource] = useState<RatingSource>('user_like');
  const [kind, setKind] = useState<RatingKind>(initialKind);
  const closeRef = useRef<HTMLButtonElement>(null);

  // 💡 removeItem を受け取る
  const { items, isLoading, error, reload, removeItem } = useHighRated({
    enabled: isOpen,
    kind,
    source,
  });

  // 開くたびに種類を初期化
  useEffect(() => {
    if (isOpen) setKind(initialKind);
  }, [isOpen, initialKind]);

  // Escで閉じる + 開いた時に閉じるボタンへフォーカス
  useEffect(() => {
    if (!isOpen) return;
    closeRef.current?.focus();
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const scoreLabel = (score: number) =>
    source === 'auto' ? `${score}点` : `👍 ${score}`;

  return (
    <div
      // 💡 fixed プロパティによってクラスを出し分ける
      className={`${fixed ? 'fixed' : 'absolute'} inset-0 z-50 flex items-center justify-center bg-black/40 p-4`}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose(); // 背景クリックで閉じる
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="hr-title"
        className="flex max-h-full w-full max-w-md flex-col rounded-2xl bg-white shadow-2xl dark:bg-slate-800"
      >
        <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3 dark:border-slate-700">
          <h2 id="hr-title" className="text-base font-bold text-slate-800 dark:text-slate-100">
            ⭐ Toの高評価リスト
          </h2>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="閉じる"
            className="rounded-md px-2 py-1 text-slate-500 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            ✕
          </button>
        </header>

        <div className="space-y-2 px-4 pt-3">
          <div role="tablist" aria-label="評価の種類" className="inline-flex rounded-lg bg-slate-200 p-1 dark:bg-slate-900">
            {SOURCE_TABS.map((t) => (
              <button
                key={t.value}
                type="button"
                role="tab"
                aria-selected={source === t.value}
                onClick={() => setSource(t.value)}
                className={tabClass(source === t.value, 'bg-blue-600')}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div role="tablist" aria-label="対象" className="inline-flex rounded-lg bg-slate-200 p-1 dark:bg-slate-900">
            {KIND_TABS.map((t) => (
              <button
                key={t.value}
                type="button"
                role="tab"
                aria-selected={kind === t.value}
                onClick={() => setKind(t.value)}
                className={tabClass(kind === t.value, 'bg-emerald-600')}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <div className="min-h-[8rem] flex-1 overflow-y-auto px-4 py-3">
          {isLoading && <p className="text-sm text-slate-500">読み込み中…</p>}

          {!isLoading && error && (
            <div className="text-sm text-red-600 dark:text-red-400">
              <p>{error}</p>
              <button type="button" onClick={() => void reload()} className="mt-2 underline">
                再読み込み
              </button>
            </div>
          )}

          {!isLoading && !error && items.length === 0 && (
            <p className="text-sm text-slate-500">まだ高評価はありません</p>
          )}

          {!isLoading && !error && items.length > 0 && (
            <ol className="space-y-2">
              {items.map((item, i) => (
                <li
                  key={item.id}
                  className="flex items-start gap-3 rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-900 group"
                >
                  <span className="w-5 shrink-0 text-sm font-bold text-slate-400">{i + 1}</span>
                  <p className="flex-1 whitespace-pre-wrap break-words text-sm text-slate-800 dark:text-slate-100">
                    {item.text}
                  </p>
                  
                  <div className="flex flex-col items-end gap-1 shrink-0">
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700 dark:bg-amber-950 dark:text-amber-300">
                      {scoreLabel(item.score || 1)}
                    </span>
                    
                    {/* 💡 削除ボタンを追加（ホバー時のみ少し濃くなる） */}
                    <button
                      onClick={() => removeItem(item.id)}
                      className="text-[10px] text-slate-400 hover:text-red-500 opacity-50 group-hover:opacity-100 transition-opacity"
                      title="この高評価を削除"
                    >
                      🗑️ 削除
                    </button>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </div>
  );
}