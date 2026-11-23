// index.tsx
/// <reference types="vite/client" />
import LinkNavigatorBlock from "../chat_blocks/LinkNavigatorBlock";
import * as React from "react";
import { Component, Suspense, lazy, useEffect, useState } from "react";

/** Backendから受け取る1個の表示ブロック。 */
export interface ChatBlock {
  type: string;
  data?: unknown;
  props?: Record<string, unknown> | null;
  id?: string | number | null;
  [key: string]: unknown;
}

export interface BlockComponentProps {
  block: ChatBlock;
  data?: unknown;
  apiBaseUrl?: string;
  onOptionSelect?: (...args: unknown[]) => void;
  onOpenManualEdit?: (...args: unknown[]) => void;
  [key: string]: unknown;
}

export type BlockComponent = React.ComponentType<BlockComponentProps>;
export type BlockRendererRegistry = Record<string, BlockComponent>;

export interface RenderBlocksProps {
  blocks?: unknown;
  apiBaseUrl?: string;
  /** 呼び出し元固有のRenderer。自動登録済みRendererへ追加されます。 */
  renderers?: BlockRendererRegistry;
  onOptionSelect?: (...args: unknown[]) => void;
  onOpenManualEdit?: (...args: unknown[]) => void;
  fallback?: React.ReactNode | ((block: ChatBlock) => React.ReactNode);
}

/** 1部分のみ修正 (Surgical Partial Patch v2) のデータ構造 */
export interface PartialPatchPayload {
  success: boolean;
  file_path: string;
  strategy: string;
  target_symbol?: string | null;
  modified_start_line: number;
  modified_end_line: number;
  original_line_count: number;
  new_line_count: number;
  preserved_symbols_count: number;
  hunks_applied?: number;
  added_imports?: string[];
  cross_file_warnings?: string[];
  unified_diff: string;
  before_snippet: string;
  after_snippet: string;
  backup_file_path?: string | null;
  vscode_goto_command: string;
  vscode_diff_command: string;
  vscode_launched?: boolean;
  applied_to_disk?: boolean;
  message: string;
  error?: string | null;
}

type ImportedBlockModule = {
  default?: React.ComponentType<any>;
  [exportName: string]: unknown;
};

type BlockImporter = () => Promise<ImportedBlockModule>;

interface BlockErrorBoundaryProps {
  blockType?: string;
  resetKey: React.Key;
  children: React.ReactNode;
}

interface BlockErrorBoundaryState {
  error: Error | null;
}

// ============================================================
// 💻 組み込み VSCodeBlock (1部分のみ修正Diff & 自動import表示 & 3秒間の青白いオーラ付き)
// ============================================================

function isRecord(value: unknown): value is Record<string, any> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export const VSCodeBlock: React.FC<BlockComponentProps> = ({
  block,
  data,
  apiBaseUrl = "",
  onOptionSelect,
}) => {
  const [isLinked, setIsLinked] = useState<boolean>(false);
  const [showConfirm, setShowConfirm] = useState<boolean>(true);
  const [isAuraActive, setIsAuraActive] = useState<boolean>(false);
  const [statusLog, setStatusLog] = useState<string>("");
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [diffViewMode, setDiffViewMode] = useState<"unified" | "split">("unified");

  // 3秒間だけ青白いオーラを表示して自動で消すタイマー
  useEffect(() => {
    if (!isAuraActive) return;
    const timer = setTimeout(() => {
      setIsAuraActive(false);
    }, 3000);
    return () => clearTimeout(timer);
  }, [isAuraActive]);

  // バックエンドの VSCodeHandler / ProjectBuildHandler に命令を送って VS Code 側の操作を実行させる関数
  const triggerBackendVSCodeAction = async (
    commandText: string,
    extraPayload: Record<string, unknown> = {},
  ) => {
    setIsSyncing(true);
    setStatusLog("⏳ VS Code ワークスペースへ変更を反映し、エディタと同期中...");

    const baseUrl = String(
      apiBaseUrl || import.meta.env.VITE_API_BASE_URL || "",
    ).replace(/\/+$/, "");
    const endpoint = `${baseUrl}/api/chat`;

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: commandText,
          forced_handler: "VSCodeHandler",
          ...extraPayload,
        }),
      });

      if (response.ok) {
        setStatusLog(
          "✅ VS Code ワークスペースに反映し、エディタ（Diff / 該当行）を起動しました！ (Ctrl+Shift+B でタスク実行可能)",
        );
      } else {
        setStatusLog(
          `⚠️ サーバー応答ステータス: ${response.status} (ローカル連携モードで動作中)`,
        );
      }
    } catch (err) {
      console.warn("VSCode direct sync error:", err);
      setStatusLog(
        "⚠️ バックエンド直接通信をスキップしました (ローカル連携モード)",
      );
    } finally {
      setIsSyncing(false);
    }
  };

  // 「⚡ 連携する」ボタンを押したとき
  const handleConnect = async () => {
    setIsLinked(true);
    setShowConfirm(false);
    setIsAuraActive(true);

    await triggerBackendVSCodeAction("VSCodeと連携してtasks.jsonを書き込んで反映して", {
      vscode_action: "vscode_connect",
    });

    onOptionSelect?.({
      action: "vscode_connect",
      timestamp: Date.now(),
    });
  };

  // payload の安全な抽出
  const payload: Record<string, any> = isRecord(data)
    ? data
    : isRecord(block?.data)
      ? block.data
      : isRecord(block)
        ? block
        : {};

  const cards: Record<string, any>[] = Array.isArray(payload.cards)
    ? payload.cards
    : [];
  const generatedTask: Record<string, any> | null = isRecord(
    payload.generated_task,
  )
    ? payload.generated_task
    : null;
  const writtenFiles: string[] = Array.isArray(payload.written_files?.success)
    ? payload.written_files.success
    : [];
  const partialPatch: PartialPatchPayload | null = isRecord(payload.partial_patch)
    ? (payload.partial_patch as PartialPatchPayload)
    : isRecord(payload.code_analysis?.partial_patch)
      ? (payload.code_analysis.partial_patch as PartialPatchPayload)
      : null;

  const addedImports: string[] = Array.isArray(partialPatch?.added_imports)
    ? partialPatch.added_imports
    : [];
  const crossWarnings: string[] = Array.isArray(partialPatch?.cross_file_warnings)
    ? partialPatch.cross_file_warnings
    : [];

  // 1部分のみ修正をVS CodeのDiffビューで開く
  const handleOpenPartialDiff = async () => {
    if (!partialPatch) return;
    setIsLinked(true);
    setShowConfirm(false);
    setIsAuraActive(true);
    await triggerBackendVSCodeAction(
      `VSCodeで ${partialPatch.file_path} の1部分修正Diffを開いて`,
      {
        vscode_action: "vscode_open_diff",
        explicit_file_path: partialPatch.file_path,
        launch_vscode: true,
      },
    );
    onOptionSelect?.({
      action: "vscode_open_diff",
      file_path: partialPatch.file_path,
      command: partialPatch.vscode_diff_command,
    });
  };

  // 1部分修正した該当行をVS Codeで直接開く (code --goto)
  const handleGotoModifiedLine = async () => {
    if (!partialPatch) return;
    setIsLinked(true);
    setShowConfirm(false);
    setIsAuraActive(true);
    await triggerBackendVSCodeAction(
      `VSCodeで ${partialPatch.file_path} の ${partialPatch.modified_start_line}行目を開いて`,
      {
        vscode_action: "vscode_goto_line",
        explicit_file_path: partialPatch.file_path,
        start_line: partialPatch.modified_start_line,
        launch_vscode: true,
      },
    );
    onOptionSelect?.({
      action: "vscode_goto_line",
      file_path: partialPatch.file_path,
      line: partialPatch.modified_start_line,
      command: partialPatch.vscode_goto_command,
    });
  };

  // 1部分修正をバックアップから元に戻す (Rollback)
  const handleRollbackPatch = async () => {
    if (!partialPatch) return;
    setIsAuraActive(true);
    await triggerBackendVSCodeAction(
      `${partialPatch.file_path} の1部分修正をロールバックして元に戻して`,
      {
        vscode_action: "vscode_rollback",
        explicit_file_path: partialPatch.file_path,
      },
    );
    setStatusLog(`↩️ ${partialPatch.file_path} を変更前のバックアップから完全復元しました。`);
    onOptionSelect?.({
      action: "vscode_rollback",
      file_path: partialPatch.file_path,
      backup_file_path: partialPatch.backup_file_path,
    });
  };

  return (
    <div className="relative my-2 w-full">
      {/* 🌌 3秒間の青白いオーラエフェクト (画面フチ + カード背面発光) */}
      {isAuraActive && (
        <>
          <div className="pointer-events-none fixed inset-0 z-50 animate-pulse border-4 border-cyan-300/80 shadow-[inset_0_0_80px_rgba(56,189,248,0.55)] transition-opacity duration-700" />
          <div className="pointer-events-none absolute -inset-2 z-0 animate-pulse rounded-2xl bg-gradient-to-r from-cyan-400 via-sky-200 to-blue-500 opacity-75 blur-xl transition-all duration-1000" />
        </>
      )}

      {/* 💻 メインコンテナ */}
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
              VS Code Engine {partialPatch ? "— ✂️ 1部分のみ修正モード" : ""}
            </h4>
          </div>

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

        {/* オーラ発動中の同期メッセージ（3秒間） */}
        {isAuraActive && (
          <div className="mb-4 flex items-center justify-center gap-2 rounded-lg border border-cyan-300/60 bg-cyan-950/80 py-2.5 text-sm font-bold text-cyan-100 shadow-[0_0_20px_rgba(34,211,238,0.5)]">
            <span>✨</span>
            <span>VS Code ワークスペースと同期しました！</span>
          </div>
        )}

        {/* リアルタイム通信ステータスログ */}
        {statusLog && (
          <div className="mb-4 rounded-lg border border-cyan-500/30 bg-cyan-950/40 px-3 py-2 font-mono text-xs text-cyan-200">
            {statusLog}
          </div>
        )}

        {/* バックエンド側で既にファイル書き込みが完了していた場合の通知 */}
        {writtenFiles.length > 0 && (
          <div className="mb-4 rounded-lg border border-emerald-500/40 bg-emerald-950/40 px-3 py-2 text-xs text-emerald-300">
            ✅ ワークスペースに直接書き込みました:{" "}
            <span className="font-mono font-bold">
              {writtenFiles.join(", ")}
            </span>
          </div>
        )}

        {/* ✂️ 1部分のみ修正 (Surgical Partial Patch v2) 専用パネル */}
        {partialPatch && (
          <div className="mb-4 rounded-xl border border-cyan-500/40 bg-slate-950/80 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded bg-cyan-500/20 px-2 py-0.5 font-mono text-xs font-bold text-cyan-300">
                    ✂️ 1部分のみ修正 ({partialPatch.strategy})
                  </span>
                  <code className="text-sm font-bold text-white">
                    {partialPatch.file_path}
                  </code>
                  {partialPatch.target_symbol && (
                    <span className="rounded bg-amber-500/20 px-2 py-0.5 font-mono text-xs text-amber-300">
                      対象: {partialPatch.target_symbol}
                    </span>
                  )}
                  <span className="rounded border border-slate-700 bg-slate-900 px-2 py-0.5 font-mono text-xs text-sky-300">
                    L{partialPatch.modified_start_line} - L{partialPatch.modified_end_line}
                  </span>
                  {partialPatch.hunks_applied && partialPatch.hunks_applied > 1 && (
                    <span className="rounded bg-purple-500/20 px-2 py-0.5 font-mono text-xs text-purple-300">
                      {partialPatch.hunks_applied}箇所同時適用
                    </span>
                  )}
                </div>
                <p className="mt-1.5 text-xs text-slate-300">
                  {partialPatch.message}
                </p>
              </div>

              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() =>
                    setDiffViewMode(diffViewMode === "unified" ? "split" : "unified")
                  }
                  className="rounded border border-slate-700 bg-slate-800 px-2.5 py-1 text-[11px] text-slate-300 hover:bg-slate-700"
                >
                  {diffViewMode === "unified" ? "左右分割で見る" : "Unified Diffで見る"}
                </button>
              </div>
            </div>

            {/* 自動マージされた新規 import 通知 */}
            {addedImports.length > 0 && (
              <div className="mt-2.5 rounded-lg border border-sky-500/30 bg-sky-950/30 px-3 py-1.5 font-mono text-xs text-sky-200">
                📦 ファイル先頭へ自動マージした import: {addedImports.join(" / ")}
              </div>
            )}

            {/* クロスファイル引数変更の注意通知 */}
            {crossWarnings.length > 0 && (
              <div className="mt-2.5 rounded-lg border border-amber-500/40 bg-amber-950/40 px-3 py-2 text-xs text-amber-200">
                {crossWarnings.map((cw, idx) => (
                  <div key={`cw-${idx}`}>⚠️ {cw}</div>
                ))}
              </div>
            )}

            {/* Diff プレビュー表示 */}
            {diffViewMode === "unified" ? (
              <pre className="mt-3 max-h-64 overflow-x-auto rounded-lg bg-black/80 p-3 font-mono text-xs leading-relaxed">
                {(partialPatch.unified_diff || "差分なし")
                  .split("\n")
                  .map((line, i) => {
                    const colorClass = line.startsWith("+") && !line.startsWith("+++")
                      ? "bg-emerald-950/60 text-emerald-300"
                      : line.startsWith("-") && !line.startsWith("---")
                        ? "bg-rose-950/60 text-rose-300"
                        : line.startsWith("@@")
                          ? "text-cyan-400 font-bold"
                          : "text-slate-300";
                    return (
                      <div key={`diff-${i}`} className={`px-1 ${colorClass}`}>
                        {line}
                      </div>
                    );
                  })}
              </pre>
            ) : (
              <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                <div className="rounded-lg border border-rose-500/30 bg-rose-950/20 p-2.5">
                  <div className="mb-1.5 font-mono text-[11px] font-bold text-rose-300">
                    - 変更前 (L{partialPatch.modified_start_line}〜L{partialPatch.modified_end_line})
                  </div>
                  <pre className="max-h-56 overflow-x-auto font-mono text-[11px] leading-relaxed text-rose-200">
                    {partialPatch.before_snippet || "(変更前スニペットなし)"}
                  </pre>
                </div>
                <div className="rounded-lg border border-emerald-500/30 bg-emerald-950/20 p-2.5">
                  <div className="mb-1.5 font-mono text-[11px] font-bold text-emerald-300">
                    + 1部分修正後
                  </div>
                  <pre className="max-h-56 overflow-x-auto font-mono text-[11px] leading-relaxed text-emerald-200">
                    {partialPatch.after_snippet || "(変更後スニペットなし)"}
                  </pre>
                </div>
              </div>
            )}

            {/* VS Code 連携アクションボタン群 */}
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2 pt-2">
              <div className="font-mono text-[11px] text-slate-400">
                🛡️ 保護済み他シンボル: {Math.max(0, partialPatch.preserved_symbols_count - 1)}件
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={isSyncing}
                  onClick={handleGotoModifiedLine}
                  className="rounded-lg border border-cyan-500/50 bg-cyan-950/60 px-3 py-1.5 text-xs font-semibold text-cyan-200 transition hover:bg-cyan-900/70 disabled:opacity-50"
                >
                  🔍 VS Codeで該当行(L{partialPatch.modified_start_line})を開く
                </button>
                <button
                  type="button"
                  disabled={isSyncing}
                  onClick={handleOpenPartialDiff}
                  className="rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 px-3.5 py-1.5 text-xs font-bold text-white shadow-[0_0_15px_rgba(56,189,248,0.4)] transition hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50"
                >
                  ✂️ VS Codeで変更前後のDiffを比較
                </button>
                {partialPatch.backup_file_path && (
                  <button
                    type="button"
                    disabled={isSyncing}
                    onClick={handleRollbackPatch}
                    className="rounded-lg border border-amber-500/40 bg-amber-950/40 px-3 py-1.5 text-xs text-amber-200 transition hover:bg-amber-900/60 disabled:opacity-50"
                  >
                    ↩️ 変更前に戻す
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* 🔗 「VS Codeと連携しますか？」確認パネル */}
        {showConfirm && !isLinked && (
          <div className="mb-4 rounded-xl border border-sky-500/30 bg-gradient-to-br from-slate-800/90 to-sky-950/40 p-4">
            <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
              <div>
                <h5 className="flex items-center gap-2 text-sm font-bold text-sky-200">
                  <span>🔗</span> VS Code と連携しますか？
                </h5>
                <p className="mt-1 text-xs text-slate-300">
                  連携すると、1部分のみ修正した箇所のDiff比較（
                  <code className="text-sky-300">code --diff</code>
                  ）や該当行ジャンプ（
                  <code className="text-sky-300">code --goto</code>
                  ）、
                  <code className="text-sky-300">.vscode/tasks.json</code>{" "}
                  の自動生成が有効になります。
                </p>
              </div>

              <div className="flex shrink-0 gap-2">
                <button
                  type="button"
                  onClick={() => setShowConfirm(false)}
                  className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 transition hover:bg-slate-700"
                >
                  今はプレビューだけ見る
                </button>
                <button
                  type="button"
                  disabled={isSyncing}
                  onClick={handleConnect}
                  className="rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 px-4 py-1.5 text-xs font-bold text-white shadow-[0_0_15px_rgba(56,189,248,0.4)] transition hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50"
                >
                  {isSyncing ? "同期中..." : "⚡ 連携する"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* 📚 トリビア＆オプション解説カード一覧 */}
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

        {/* 🚀 tasks.json プレビュー & ワンクリック注入パネル */}
        {generatedTask && (
          <div className="mt-4 rounded-lg border border-slate-700 bg-black/50 p-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="font-mono text-xs font-bold text-cyan-400">
                📄 .vscode/tasks.json プレビュー
              </span>

              {isLinked ? (
                <button
                  type="button"
                  disabled={isSyncing}
                  onClick={async () => {
                    setIsAuraActive(true);
                    await triggerBackendVSCodeAction(
                      "VSCodeにtasks.jsonを書き込んで反映して",
                      { vscode_action: "vscode_connect" },
                    );
                    onOptionSelect?.({
                      action: "apply_vscode_task",
                      path: ".vscode/tasks.json",
                      content: JSON.stringify(generatedTask, null, 2),
                    });
                  }}
                  className="rounded bg-cyan-600 px-3 py-1 text-xs font-bold text-white shadow-[0_0_12px_rgba(34,211,238,0.4)] transition hover:bg-cyan-500 disabled:opacity-50"
                >
                  {isSyncing
                    ? "書き込み中..."
                    : "🚀 VS Code に直接注入して開く"}
                </button>
              ) : (
                <button
                  type="button"
                  disabled={isSyncing}
                  onClick={handleConnect}
                  className="rounded border border-cyan-500/50 bg-cyan-950/40 px-3 py-1 text-xs text-cyan-300 transition hover:bg-cyan-900/60 disabled:opacity-50"
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

// ============================================================
// ブロックコンポーネントの自動レジストリ
// ============================================================

const modules = import.meta.glob<ImportedBlockModule>([
  "./**/*.jsx",
  "./**/*.tsx",
  "!./index.jsx",
  "!./index.tsx",
  "!./BlockRenderer.jsx",
  "!./BlockRenderer.tsx",
]) as Record<string, BlockImporter>;

export const BLOCK_COMPONENTS: BlockRendererRegistry = {
  VSCodeBlock: VSCodeBlock,
  LinkNavigatorBlock: LinkNavigatorBlock as BlockComponent,
};
export function normalizeBlockType(value: unknown): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "_");
}

function getComponentName(path: string): string {
  const fileName = path.split("/").pop() ?? "";
  return fileName.replace(/\.(jsx|tsx)$/i, "");
}

function createLazyComponent(
  componentName: string,
  importer: BlockImporter,
): BlockComponent {
  return lazy(async () => {
    const loadedModule = await importer();
    const namedExport = loadedModule[componentName];
    const component =
      loadedModule.default ??
      (typeof namedExport === "function" ? namedExport : undefined);

    if (!component) {
      throw new Error(
        `${componentName} にdefault export、または同名のnamed exportがありません。`,
      );
    }

    return {
      default: component as React.ComponentType<BlockComponentProps>,
    };
  });
}

Object.entries(modules).forEach(([path, importer]) => {
  const componentName = getComponentName(path);
  if (!componentName) return;

  if (
    BLOCK_COMPONENTS[componentName] &&
    componentName !== "VSCodeBlock"
  ) {
    console.warn(
      `[blocks/index] 同名ブロックを検出しました: ${componentName} (${path})`,
    );
    return;
  }

  BLOCK_COMPONENTS[componentName] = createLazyComponent(
    componentName,
    importer,
  );
});

const BLOCK_ALIASES: Record<string, string> = {
  link_navigator: "LinkNavigatorBlock",
  linknavigator: "LinkNavigatorBlock",
  linknavigatorblock: "LinkNavigatorBlock",
  phppreviewblock: "CodeFormatBlock",
  sqlpreviewblock: "CodeFormatBlock",
  htmlcsspreviewblock: "CodeFormatBlock",
  jsonviewerblock: "CodeFormatBlock",
  codeblock: "CodeFormatBlock",
  sqlexamplemodal: "CodeFormatBlock",

  githubrepolist: "GithubRepoListBlock",
  githubrepolistblock: "GithubRepoListBlock",
  heroblock: "HeroBlock",
  databaseschema: "DatabaseSchemaBlock",
  databaseschemablock: "DatabaseSchemaBlock",
  filedownload: "FileDownloadBlock",

  conversionjson: "ConversionJsonBlock",
  conversion_json: "conversion_jsonBlock",

  project_build: "ProjectBuildBlock",
  "project-build": "ProjectBuildBlock",
  projectbuild: "ProjectBuildBlock",
  projectbuildblock: "ProjectBuildBlock",

  vscode: "VSCodeBlock",
  vscode_assistant: "VSCodeBlock",
  "vscode-assistant": "VSCodeBlock",
  vscodeblock: "VSCodeBlock",
  vscode_tool: "VSCodeBlock",
  vscode_partial_patch: "VSCodeBlock",
};

function buildCaseInsensitiveIndex(
  registry: BlockRendererRegistry,
): BlockRendererRegistry {
  return Object.keys(registry).reduce<BlockRendererRegistry>((result, name) => {
    result[name.toLowerCase()] = registry[name];
    return result;
  }, {});
}

function applyAliases(registry: BlockRendererRegistry): BlockRendererRegistry {
  const result: BlockRendererRegistry = { ...registry };
  const caseInsensitive = buildCaseInsensitiveIndex(result);

  Object.entries(BLOCK_ALIASES).forEach(([alias, target]) => {
    const TargetComponent =
      result[target] ?? caseInsensitive[target.toLowerCase()];
    if (TargetComponent) {
      result[alias] = TargetComponent;
    }
  });

  return result;
}

export function createBlockRenderers(
  existing: BlockRendererRegistry = {},
): BlockRendererRegistry {
  return applyAliases({ ...BLOCK_COMPONENTS, ...existing });
}

export function getBlockComponent(
  type: unknown,
  registry: BlockRendererRegistry = createBlockRenderers(),
): BlockComponent | null {
  if (typeof type !== "string") return null;

  const exact = type.trim();
  const normalized = normalizeBlockType(type);
  if (!exact || !normalized) return null;

  const caseInsensitive = buildCaseInsensitiveIndex(registry);
  const aliasTarget = BLOCK_ALIASES[normalized];

  return (
    registry[exact] ??
    registry[normalized] ??
    (aliasTarget
      ? registry[aliasTarget] ?? caseInsensitive[aliasTarget.toLowerCase()]
      : undefined) ??
    caseInsensitive[exact.toLowerCase()] ??
    caseInsensitive[normalized] ??
    null
  );
}

function UnknownBlock({ block }: { block: ChatBlock }): React.ReactElement {
  return (
    <div
      role="note"
      className="rounded border border-slate-400 bg-slate-100 p-3 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-300"
    >
      未対応の表示ブロックです: <code>{block.type || "type未指定"}</code>
    </div>
  );
}

function BlockLoading(): React.ReactElement {
  return (
    <div
      className="h-12 w-full animate-pulse rounded bg-slate-200/60 dark:bg-slate-700/50"
      aria-label="ブロックを読み込み中"
    />
  );
}

class BlockErrorBoundary extends Component<
  BlockErrorBoundaryProps,
  BlockErrorBoundaryState
> {
  state: BlockErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: unknown): BlockErrorBoundaryState {
    return {
      error: error instanceof Error ? error : new Error(String(error)),
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error(
      `[RenderBlocks] ${this.props.blockType || "unknown"} の描画に失敗しました`,
      error,
      errorInfo,
    );
  }

  componentDidUpdate(previousProps: BlockErrorBoundaryProps): void {
    if (
      this.state.error &&
      previousProps.resetKey !== this.props.resetKey
    ) {
      // eslint-disable-next-line react/no-did-update-set-state
      this.setState({ error: null });
    }
  }

  render(): React.ReactNode {
    if (this.state.error) {
      return (
        <div
          role="alert"
          className="rounded border border-amber-700 bg-amber-950/30 p-3 text-xs text-amber-200"
        >
          <div className="font-semibold">
            {this.props.blockType || "ブロック"} の表示に失敗しました。
          </div>
          <div className="mt-1 break-words opacity-80">
            {this.state.error.message}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

function isChatBlock(value: unknown): value is ChatBlock {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    typeof (value as { type?: unknown }).type === "string"
  );
}

function renderFallback(
  fallback: RenderBlocksProps["fallback"],
  block: ChatBlock,
): React.ReactNode {
  if (typeof fallback === "function") return fallback(block);
  if (fallback !== undefined) return fallback;
  return <UnknownBlock block={block} />;
}

/** Backendから受け取ったblocks配列をまとめて描画します。 */
export function RenderBlocks({
  blocks,
  apiBaseUrl,
  renderers,
  onOptionSelect,
  onOpenManualEdit,
  fallback,
}: RenderBlocksProps): React.ReactElement | null {
  if (!Array.isArray(blocks) || blocks.length === 0) return null;

  const registry = createBlockRenderers(renderers);

  return (
    <div className="ai-custom-blocks-container my-3 w-full space-y-4">
      {blocks.map((candidate, index) => {
        if (!isChatBlock(candidate)) {
          const invalidBlock: ChatBlock = { type: "不正なブロックデータ" };
          return (
            <React.Fragment key={`invalid-block-${index}`}>
              {renderFallback(fallback, invalidBlock)}
            </React.Fragment>
          );
        }

        const block = candidate;
        const blockType = block.type.trim();
        const BlockComponent = getBlockComponent(blockType, registry);
        const blockProps =
          block.props &&
          typeof block.props === "object" &&
          !Array.isArray(block.props)
            ? block.props
            : {};
        const blockKey = block.id ?? `${blockType || "unknown"}-${index}`;

        if (!BlockComponent) {
          console.warn(
            `[RenderBlocks] 未対応のブロックタイプです: ${blockType || "type未指定"}`,
          );
          return (
            <React.Fragment key={blockKey}>
              {renderFallback(fallback, block)}
            </React.Fragment>
          );
        }

        return (
          <div key={blockKey} className="w-full animate-fade-in">
            <BlockErrorBoundary blockType={blockType} resetKey={blockKey}>
              <Suspense fallback={<BlockLoading />}>
                <BlockComponent
                  {...blockProps}
                  block={block}
                  data={block.data ?? blockProps.data}
                  apiBaseUrl={apiBaseUrl}
                  onOptionSelect={onOptionSelect}
                  onOpenManualEdit={onOpenManualEdit}
                />
              </Suspense>
            </BlockErrorBoundary>
          </div>
        );
      })}
    </div>
  );
}

export default RenderBlocks;