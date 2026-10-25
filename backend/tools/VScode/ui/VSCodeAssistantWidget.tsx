// ui/VSCodeAssistantWidget.tsx
import React, { useState, useEffect } from "react";
import { VSCodeAssistantWidget } from "./ui/VSCodeAssistantWidget";
export interface VSCodeAssistantWidgetProps {
  payload: Record<string, any>;
  onAction?: (data: unknown) => void;
}

export const VSCodeAssistantWidget: React.FC<VSCodeAssistantWidgetProps> = ({
  payload,
  onAction,
}) => {
  // 連携状態と「3秒間の青白いオーラ」の状態管理
  const [isLinked, setIsLinked] = useState<boolean>(false);
  const [showConfirm, setShowConfirm] = useState<boolean>(true);
  const [isAuraActive, setIsAuraActive] = useState<boolean>(false);

  // オーラを3秒間だけ表示して自動で消すタイマー
  useEffect(() => {
    if (!isAuraActive) return;
    const timer = setTimeout(() => {
      setIsAuraActive(false);
    }, 3000);
    return () => clearTimeout(timer);
  }, [isAuraActive]);

  // 「連携する」ボタンを押したときの処理
  const handleConnect = () => {
    setIsLinked(true);
    setShowConfirm(false);
    setIsAuraActive(true); // ⚡ 3秒間の青白いオーラを発動！

    // バックエンド側にも連携開始シグナルを送る場合
    onAction?.({
      action: "vscode_connect",
      timestamp: Date.now(),
    });
  };

  const cards: Record<string, any>[] = Array.isArray(payload?.cards)
    ? payload.cards
    : [];
  const generatedTask: Record<string, any> | null =
    typeof payload?.generated_task === "object" && payload?.generated_task !== null
      ? payload.generated_task
      : null;

  return (
    <div className="relative my-4 w-full">
      {/* =========================================================
          🌌 全画面（またはウィジェット周囲）の青白いオーラエフェクト（3秒間）
         ========================================================= */}
      {isAuraActive && (
        <>
          {/* 画面全体のフチを青白く光らせるオーバーレイ（クリック透過） */}
          <div className="pointer-events-none fixed inset-0 z-50 animate-pulse border-4 border-cyan-300/80 shadow-[inset_0_0_80px_rgba(56,189,248,0.55)] transition-opacity duration-700" />
          {/* カード背面の強烈な青白い後光 */}
          <div className="pointer-events-none absolute -inset-2 z-0 animate-pulse rounded-2xl bg-gradient-to-r from-cyan-400 via-sky-200 to-blue-500 opacity-75 blur-xl transition-all duration-1000" />
        </>
      )}

      {/* =========================================================
          💻 メインコンテナ
         ========================================================= */}
      <div
        className={`relative z-10 overflow-hidden rounded-xl border bg-slate-900/95 p-5 text-slate-100 transition-all duration-700 ${
          isAuraActive
            ? "scale-[1.01] border-cyan-200 shadow-[0_0_45px_rgba(125,211,252,0.85),inset_0_0_25px_rgba(186,230,253,0.4)]"
            : isLinked
            ? "border-sky-500/50 shadow-lg"
            : "border-slate-700 shadow-md"
        }`}
      >
        {/* ヘッダー */}
        <div className="mb-4 flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2.5">
            <span className="text-xl">💻</span>
            <h4 className="text-base font-bold tracking-wide text-white">
              VS Code Engine
            </h4>
          </div>

          {/* ステータスバッジ */}
          {isLinked ? (
            <span className="flex items-center gap-1.5 rounded-full border border-cyan-400/40 bg-cyan-950/60 px-3 py-1 text-xs font-semibold text-cyan-300">
              <span className="h-2 w-2 animate-ping rounded-full bg-cyan-400" />
              VS Code 連携中
            </span>
          ) : (
            <span className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-400">
              未接続 (ローカル辞書モード)
            </span>
          )}
        </div>

        {/* オーラ発動中の特別メッセージ（3秒間だけ表示） */}
        {isAuraActive && (
          <div className="mb-4 flex items-center justify-center gap-2 rounded-lg border border-cyan-300/60 bg-cyan-950/80 py-2.5 text-sm font-bold text-cyan-100 shadow-[0_0_20px_rgba(34,211,238,0.5)]">
            <span>✨</span>
            <span>VS Code ワークスペースと同期しました！</span>
          </div>
        )}

        {/* =========================================================
            🔗 「VS Codeと連携しますか？」確認パネル
           ========================================================= */}
        {showConfirm && !isLinked && (
          <div className="mb-4 rounded-xl border border-sky-500/30 bg-gradient-to-br from-slate-800/90 to-sky-950/40 p-4">
            <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
              <div>
                <h5 className="flex items-center gap-2 text-sm font-bold text-sky-200">
                  <span>🔗</span> VS Code と連携しますか？
                </h5>
                <p className="mt-1 text-xs text-slate-300">
                  連携すると、<code className="text-sky-300">.vscode/tasks.json</code>{" "}
                  や設定の直接書き込み・CLIコマンドの自動実行が有効になります。
                </p>
              </div>

              <div className="flex shrink-0 gap-2">
                <button
                  type="button"
                  onClick={() => setShowConfirm(false)}
                  className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 transition hover:bg-slate-700"
                >
                  今はトリビアだけ見る
                </button>
                <button
                  type="button"
                  onClick={handleConnect}
                  className="rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 px-4 py-1.5 text-xs font-bold text-white shadow-[0_0_15px_rgba(56,189,248,0.4)] transition hover:from-cyan-400 hover:to-blue-500"
                >
                  ⚡ 連携する
                </button>
              </div>
            </div>
          </div>
        )}

        {/* =========================================================
            📚 トリビア＆オプション解説カード一覧
           ========================================================= */}
        <div className="space-y-3">
          {cards.map((card, idx) => (
            <div
              key={String(card.id ?? `vscode-card-${idx}`)}
              className="rounded-lg border border-slate-700/80 border-l-4 border-l-cyan-400 bg-slate-800/70 p-3.5"
            >
              <div className="mb-1 flex items-center justify-between">
                <span className="rounded bg-cyan-500/20 px-2 py-0.5 text-[11px] font-semibold text-cyan-300">
                  {String(card.category || "VS Code Trivia")}
                </span>
                {card.shortcut_win && (
                  <kbd className="rounded border border-slate-600 bg-slate-900 px-2 py-0.5 font-mono text-xs text-amber-300">
                    {String(card.shortcut_win)}
                  </kbd>
                )}
              </div>

              <h5 className="text-sm font-bold text-white">
                {String(card.title || "")}
              </h5>

              {card.description && (
                <p className="mt-1 text-xs leading-relaxed text-slate-300">
                  {String(card.description)}
                </p>
              )}

              {card.trivia && (
                <div className="mt-2 rounded bg-slate-900/90 p-2 text-xs text-emerald-300">
                  💡 {String(card.trivia)}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* =========================================================
            🚀 連携完了時に解放される「tasks.json 直接書き込みパネル」
           ========================================================= */}
        {generatedTask && (
          <div className="mt-4 rounded-lg border border-slate-700 bg-black/50 p-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="font-mono text-xs font-bold text-cyan-400">
                📄 .vscode/tasks.json プレビュー
              </span>

              {isLinked ? (
                <button
                  type="button"
                  onClick={() => {
                    setIsAuraActive(true); // 書き込み時にも3秒オーラを再発動！
                    onAction?.({
                      action: "apply_vscode_task",
                      path: ".vscode/tasks.json",
                      content: JSON.stringify(generatedTask, null, 2),
                    });
                  }}
                  className="rounded bg-cyan-600 px-3 py-1 text-xs font-bold text-white shadow-[0_0_12px_rgba(34,211,238,0.4)] transition hover:bg-cyan-500"
                >
                  🚀 VS Code に直接注入する
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleConnect}
                  className="rounded border border-cyan-500/50 bg-cyan-950/40 px-3 py-1 text-xs text-cyan-300 transition hover:bg-cyan-900/60"
                >
                  🔒 連携して注入ボタンを解放
                </button>
              )}
            </div>

            <pre className="max-h-56 overflow-x-auto rounded bg-slate-950 p-2.5 font-mono text-[11px] leading-relaxed text-cyan-200">
              {JSON.stringify(generatedTask, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};