// frontend/src/components/chat_blocks/GameSimResultBlock.tsx
import React from 'react';

export interface GameSimResultBlockProps {
  data: any;
  onOptionSelect?: (payload: unknown) => void;
}

export function GameSimResultBlock({
  data,
  onOptionSelect,
}: GameSimResultBlockProps): React.ReactElement {
  const genre = data?.genre || 'ゲームシミュレーション (ローグライク / すごろく / TD)';
  const statusText = data?.summary || data?.message || 'シミュレーションターンを実行しました。';
  const choices: string[] = Array.isArray(data?.choices) ? data.choices : [];

  return (
    <div className="my-2 rounded-xl border border-amber-500/40 bg-slate-950 p-3.5 text-slate-100 space-y-2.5">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <span className="text-xs font-extrabold text-amber-400 flex items-center gap-1.5">
          <span>🎮</span>
          <span>{genre}</span>
        </span>
        <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300">
          GameSimHandler
        </span>
      </div>

      <div className="text-xs text-slate-200 leading-relaxed whitespace-pre-wrap">
        {statusText}
      </div>

      {choices.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {choices.map((ch, idx) => (
            <button
              key={`${ch}_${idx}`}
              type="button"
              onClick={() => onOptionSelect?.({ action: 'send_chat', text: ch })}
              className="px-2.5 py-1 rounded-lg bg-indigo-600/80 hover:bg-indigo-500 text-white text-xs font-semibold transition"
            >
              ▶ {ch}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default GameSimResultBlock;
