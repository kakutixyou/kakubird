// frontend/src/components/blocks/RoutingDebugBlock.jsx
import React, { useMemo, useState } from 'react';

const toFiniteNumber = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
};

const clamp = (value, minimum, maximum) => (
  Math.min(maximum, Math.max(minimum, value))
);

const normalizeHandlers = (value) => {
  if (!Array.isArray(value)) return [];

  return value
    .filter((item) => item && typeof item === 'object')
    .map((item, index) => ({
      id: `${String(item.name || 'handler')}-${index}`,
      name: String(item.name || 'UnknownHandler'),
      score: toFiniteNumber(item.score),
    }))
    .sort((left, right) => {
      if (right.score !== left.score) {
        return right.score - left.score;
      }
      return left.name.localeCompare(right.name);
    });
};

const scoreTone = (score) => {
  if (score >= 80) {
    return {
      badge: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
      bar: 'bg-emerald-500',
    };
  }

  if (score >= 40) {
    return {
      badge: 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
      bar: 'bg-amber-500',
    };
  }

  return {
    badge: 'bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
    bar: 'bg-slate-400',
  };
};

/**
 * ChatOrchestratorのルーティング結果を表示するデバッグブロック。
 *
 * 対応するBackend形式:
 * {
 *   type: "RoutingDebugBlock",
 *   props: {
 *     selected: "ChatHandler",
 *     handlers: [
 *       { name: "ChatHandler", score: 60 }
 *     ]
 *   }
 * }
 *
 * AiChatMessageListはblockとblock.propsの両方を渡すため、
 * このコンポーネントも両形式を安全に受け取る。
 */
export default function RoutingDebugBlock({
  block,
  selected,
  handlers,
  defaultOpen = true,
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const blockProps = block?.props && typeof block.props === 'object'
    ? block.props
    : {};
  const selectedHandler = String(
    selected
      ?? blockProps.selected
      ?? 'UnknownHandler',
  );
  const normalizedHandlers = useMemo(
    () => normalizeHandlers(
      Array.isArray(handlers)
        ? handlers
        : blockProps.handlers,
    ),
    [handlers, blockProps.handlers],
  );
  const selectedEntry = normalizedHandlers.find(
    (handler) => handler.name === selectedHandler,
  );
  const highestScore = normalizedHandlers[0]?.score ?? 0;
  const selectedScore = selectedEntry?.score ?? highestScore;
  const denominator = Math.max(
    100,
    ...normalizedHandlers.map((handler) => Math.abs(handler.score)),
  );

  return (
    <section className="overflow-hidden rounded-xl border border-violet-200 bg-white shadow-sm dark:border-violet-900 dark:bg-slate-900">
      <button
        type="button"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((previous) => !previous)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition hover:bg-violet-50 dark:hover:bg-violet-950/30"
      >
        <span className="flex min-w-0 items-center gap-3">
          <span
            aria-hidden="true"
            className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-violet-100 text-lg dark:bg-violet-950"
          >
            🧭
          </span>

          <span className="min-w-0">
            <span className="block text-xs font-semibold uppercase tracking-wider text-violet-600 dark:text-violet-300">
              Routing Debug
            </span>
            <span className="block truncate text-sm font-bold text-slate-800 dark:text-slate-100">
              選択: {selectedHandler}
            </span>
          </span>
        </span>

        <span className="flex shrink-0 items-center gap-2">
          <span className="rounded-full bg-violet-100 px-2 py-1 text-xs font-bold text-violet-700 dark:bg-violet-950 dark:text-violet-300">
            {selectedScore}点
          </span>
          <span
            aria-hidden="true"
            className={`text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          >
            ▼
          </span>
        </span>
      </button>

      {isOpen && (
        <div className="border-t border-slate-100 px-4 py-4 dark:border-slate-800">
          {normalizedHandlers.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-300 p-3 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
              Handlerの採点結果がありません。
            </div>
          ) : (
            <div className="space-y-3">
              {normalizedHandlers.map((handler, index) => {
                const isSelected = handler.name === selectedHandler;
                const tone = scoreTone(handler.score);
                const width = clamp(
                  (Math.max(0, handler.score) / denominator) * 100,
                  0,
                  100,
                );

                return (
                  <div
                    key={handler.id}
                    className={`rounded-lg border p-3 ${
                      isSelected
                        ? 'border-violet-300 bg-violet-50 dark:border-violet-800 dark:bg-violet-950/30'
                        : 'border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950'
                    }`}
                  >
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <div className="flex min-w-0 items-center gap-2">
                        <span className="w-5 shrink-0 text-xs font-semibold text-slate-400">
                          #{index + 1}
                        </span>
                        <span className="truncate text-sm font-semibold text-slate-700 dark:text-slate-200">
                          {handler.name}
                        </span>
                        {isSelected && (
                          <span className="rounded bg-violet-600 px-1.5 py-0.5 text-[10px] font-bold text-white">
                            SELECTED
                          </span>
                        )}
                      </div>

                      <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-bold ${tone.badge}`}>
                        {handler.score}
                      </span>
                    </div>

                    <div className="h-1.5 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${tone.bar}`}
                        style={{ width: `${width}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <p className="mt-3 text-xs leading-5 text-slate-500 dark:text-slate-400">
            この表示は、ChatOrchestratorが各Handlerを採点した結果です。低スコアや競合が起きた場合の確認に使います。
          </p>
        </div>
      )}
    </section>
  );
}

export { RoutingDebugBlock };
