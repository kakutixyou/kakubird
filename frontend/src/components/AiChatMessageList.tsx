// AIChatMessageList.tsx
// 既存のコード（1. Multi Select, 2. GitHub Search, Image, 3.5 VS Code, 3.6 Malware Defense,
// 3.7 Video Curator, 3.8 Math Result, 4. UI Blocks, 5. Normal Chat）をすべて維持した上で、
// ToAiStudioDashboard (.tsx) の埋め込みと、体験談JSONメモ (3.75)、および自作モデル会話応答を統合した完全版です。

import React, { useEffect, useRef } from "react";

import MultiSelectMessage from "./MultiSelectMessage";
import { RenderBlocks } from "./blocks";
import { ChatBlock } from "./blocks/ChatBlock";
import { ChatBubble, ChatLabel } from "./ui/ChatBubble";
import { WidgetCard } from "./ui/WidgetCard";
import { Collapsible } from "./ui/Collapsible";
import { LoadingIndicator } from "./ui/LoadingIndicator";
import ToAiStudioDashboard from "./widgets/ToAiStudioDashboard";
import MarkdownChatBlock from './blocks/MarkdownChatBlock';
// ==========================================
// 1. 型定義
// ==========================================

export interface ChatMessage {
  id?: string | number;
  type?: string;
  response_type?: string;
  role?: "user" | "ai" | "system";
  content?: unknown;
  text?: string;
  message?: string;
  blocks?: unknown[];
  data?: unknown;
  active_page?: "video" | "memo" | "security" | "code";
  [key: string]: unknown;
}

export interface AiChatMessageListProps {
  messages?: ChatMessage[];
  isLoading?: boolean;
  onOptionSelect?: (data: unknown) => void;
  onOpenManualEdit?: (data: unknown) => void;
  apiBaseUrl?: string;
}

// ==========================================
// 2. ユーティリティ関数
// ==========================================

const ENV_API_BASE_URL: string = String(
  import.meta.env.VITE_API_BASE_URL || ""
).replace(/\/+$/, "");

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function extractDisplayData(message: ChatMessage | undefined): {
  displayMessage: string;
  displayBlocks: unknown[];
} {
  const candidates = [message?.content, message?.text, message];

  let displayMessage = "";
  let displayBlocks: unknown[] = [];

  for (const candidate of candidates) {
    if (!isRecord(candidate)) continue;

    if (!displayMessage && typeof candidate.message === "string") {
      displayMessage = candidate.message;
    }

    if (displayBlocks.length === 0 && Array.isArray(candidate.blocks)) {
      displayBlocks = candidate.blocks;
    }
  }

  if (!displayMessage) {
    if (typeof message?.content === "string") {
      displayMessage = message.content;
    } else if (typeof message?.text === "string") {
      displayMessage = message.text;
    } else if (typeof message?.message === "string") {
      displayMessage = message.message;
    }
  }

  return { displayMessage, displayBlocks };
}

// ==========================================
// 3. コンポーネント
// ==========================================

function RenderSmartContent({ value }: { value: unknown }): React.ReactElement {
  if (typeof value !== "string") {
    if (isRecord(value)) {
      return (
        <div className="whitespace-pre-wrap leading-relaxed">
          {typeof value.message === "string"
            ? value.message
            : JSON.stringify(value, null, 2)}
        </div>
      );
    }
    return (
      <div className="text-sm text-red-400">
        データ形式エラー: {String(value ?? "")}
      </div>
    );
  }

  if (value.includes("<summary>") && value.includes("<details>")) {
    const summaryText =
      value.match(/<summary>([\s\S]*?)<\/summary>/)?.[1] || "結論";
    const detailsText =
      value.match(/<details>([\s\S]*?)<\/details>/)?.[1] || "";

    return <Collapsible summaryText={summaryText} detailsText={detailsText} />;
  }

  // 物理や証明問題のテキストが読みやすいように leading-relaxed を追加
  return <div className="whitespace-pre-wrap leading-relaxed">{value}</div>;
}

export default function AiChatMessageList({
  messages = [],
  isLoading = false,
  onOptionSelect,
  onOpenManualEdit,
  apiBaseUrl = ENV_API_BASE_URL,
}: AiChatMessageListProps): React.ReactElement {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 space-y-4 overflow-y-auto p-4">
      {
        
      messages.map((msg, messageIndex) => {
        

        const messageKey = msg?.id ?? `message-${messageIndex}`;

        // 1. Multi Select Message
        if (msg?.type === "multi_select") {
          return (
            <div key={messageKey} className="flex flex-col items-start">
              <ChatLabel role="ai" />
              <MultiSelectMessage message={msg} onSubmit={onOptionSelect} />
            </div>
          );
        }

        // 2. GitHub Search UI
        if (msg?.response_type === "github_search") {
          const content = isRecord(msg.content) ? msg.content : {};
          const repositories = Array.isArray(content.repositories)
            ? content.repositories
            : [];

          return (
            <WidgetCard key={messageKey} icon="🔍" title="GitHub Search">
              {content.message && (
                <div className="border-b border-slate-100 pb-3 text-sm text-slate-700 dark:border-slate-700 dark:text-slate-300">
                  <RenderSmartContent value={content.message} />
                </div>
              )}

              <div className="mt-2 space-y-3">
                {repositories.map((repo, repositoryIndex) => {
                  const repoData = isRecord(repo) ? repo : {};
                  return (
                    <div
                      key={String(repoData?.id ?? `repository-${repositoryIndex}`)}
                      className="rounded border border-slate-200 bg-slate-50 p-2 text-sm dark:border-slate-700 dark:bg-slate-800"
                    >
                      {String(repoData?.name || "名称未設定")}
                    </div>
                  );
                })}
              </div>
            </WidgetCard>
          );
        }

        // 3. Image UI
        if (msg?.response_type === "image") {
          const dataRecord = isRecord(msg?.data) ? msg.data : {};
          const contentRecord = isRecord(msg?.content) ? msg.content : {};
          const imageUrl =
            (typeof dataRecord.url === "string" ? dataRecord.url : undefined) ||
            (typeof contentRecord.url === "string" ? contentRecord.url : undefined) ||
            "";
          const altText =
            typeof dataRecord.prompt === "string"
              ? dataRecord.prompt
              : "AI Generated Image";

          if (!imageUrl) {
            return null;
          }

          return (
            <div key={messageKey} className="flex w-full flex-col items-start">
              <ChatLabel role="ai" />
              <div className="my-4 overflow-hidden rounded-xl border border-slate-200 shadow-sm dark:border-slate-700">
                <img
                  src={imageUrl}
                  alt={altText}
                  className="max-w-full object-contain"
                  loading="lazy"
                />
              </div>
            </div>
          );
        }

        // 3.5 VS Code Assistant UI
        if (
          msg?.type === "vscode" ||
          msg?.response_type === "vscode" ||
          msg?.mode === "vscode_assistant"
        ) {
          const payload = isRecord(msg?.data)
            ? msg.data
            : isRecord(msg?.content)
            ? msg.content
            : {};

          return (
            <div key={messageKey} className="flex w-full flex-col items-start">
              <ChatLabel role="ai" />
              <WidgetCard icon="⌨️" title="VS Code Assistant">
                <RenderSmartContent value={payload} />
              </WidgetCard>
            </div>
          );
        }

        // ----------------------------------------------------
        // 3.6 Malware Defense UI (HEX・DoS対策・キーロガー対策 + ToAiStudioDashboard 連携)
        // ----------------------------------------------------
        if (
          msg?.type === "malware_defense" ||
          msg?.response_type === "malware_defense"
        ) {
          const payload = isRecord(msg?.data)
            ? msg.data
            : isRecord(msg?.content)
            ? msg.content
            : {};

          return (
            <div key={messageKey} className="flex w-full flex-col items-start">
              <ChatLabel role="ai" />
              <WidgetCard icon="🛡️" title="マルウェア解析 ＆ 防御コンソール">
                {typeof payload.summary === "string" && (
                  <div className="border-b border-slate-100 pb-3 text-sm text-slate-700 dark:border-slate-700 dark:text-slate-300">
                    <RenderSmartContent value={payload.summary} />
                  </div>
                )}

                <div className="mt-3 space-y-3">
                  {Array.isArray(payload.c2_ips) && payload.c2_ips.length > 0 && (
                    <div className="rounded-lg bg-red-50 p-2.5 text-xs text-red-700 dark:bg-red-950/40 dark:text-red-300 border border-red-200 dark:border-red-900">
                      <span className="font-bold">検知されたC2通信先: </span>
                      <span className="font-mono">{payload.c2_ips.join(", ")}</span>
                    </div>
                  )}

                  {Array.isArray(payload.mitigation_rules) && (
                    <div className="rounded-lg bg-slate-900 p-3 font-mono text-xs text-emerald-400 overflow-x-auto">
                      <div className="text-[10px] text-slate-400 mb-1">適用推奨ルール:</div>
                      <pre>{payload.mitigation_rules.join("\n")}</pre>
                    </div>
                  )}

                  <div className="flex flex-wrap gap-2 pt-1">
                    <button
                      onClick={() =>
                        onOptionSelect?.({ action: "apply_rules", target: payload.c2_ips })
                      }
                      className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500"
                    >
                      ルールを適用して通信を遮断
                    </button>
                  </div>

                  {/* フル機能の .tsx ダッシュボード（セキュリティタブ初期選択）を展開 */}
                  <div className="mt-3 overflow-hidden rounded-xl border border-slate-800">
                    <ToAiStudioDashboard
                      initialPage="security"
                      initialData={payload}
                      onOptionSelect={onOptionSelect}
                    />
                  </div>
                </div>
              </WidgetCard>
            </div>
          );
        }

        // ----------------------------------------------------
        // 3.7 Video Curator Studio UI (動画URL解析・タイムバー・造語曲・字幕プレビュー)
        // ----------------------------------------------------
        if (
          msg?.type === "video_curator" ||
          msg?.response_type === "video_curator" ||
          msg?.type === "to_model_studio" ||
          msg?.response_type === "to_model_studio" ||
          msg?.type === "experience_memo" ||
          msg?.response_type === "experience_memo"
        ) {
          const payload = isRecord(msg?.data)
            ? msg.data
            : isRecord(msg?.content)
            ? msg.content
            : {};
          const targetPage =
            msg?.active_page ||
            (msg?.response_type === "experience_memo" || msg?.type === "experience_memo"
              ? "memo"
              : "video");

          return (
            <div key={messageKey} className="flex w-full flex-col items-start">
              <ChatLabel role="ai" />
              <WidgetCard icon="🎬" title="ToModel 統合解析＆会話スタジオ (.tsx)">
                {typeof msg?.message === "string" && (
                  <div className="mb-3 border-b border-slate-100 pb-3 text-sm text-slate-700 dark:border-slate-700 dark:text-slate-300">
                    <RenderSmartContent value={msg.message} />
                  </div>
                )}
                <div className="w-full overflow-hidden rounded-xl border border-slate-800">
                  <ToAiStudioDashboard
                    initialPage={targetPage}
                    initialData={payload}
                    onOptionSelect={onOptionSelect}
                  />
                </div>
              </WidgetCard>
            </div>
          );
        }

        // ----------------------------------------------------
        // 3.8 Math Result UI (やや青いテーマ ＆ 長文/短文ハイブリッド対応)
        // ----------------------------------------------------
        if (msg?.type === "math" || msg?.response_type === "math") {
          let payload: Record<string, any> | null = null;

          if (isRecord(msg?.data) && ("result" in msg.data || "expression" in msg.data)) {
            payload = msg.data;
          } else if ("result" in msg || "expression" in msg) {
            payload = msg as Record<string, any>;
          } else if (typeof msg?.content === "string" && msg.content.includes('"result"')) {
            try {
              payload = JSON.parse(msg.content);
            } catch (e) {
              console.warn("Math JSON parse error", e);
            }
          } else if (typeof msg?.content === "string" && msg.content.startsWith("計算結果:")) {
            const match = msg.content.match(/計算結果:\s*(.*?)\s*=\s*(.*)/);
            if (match) {
              payload = {
                success: true,
                expression: match[1],
                result: match[2],
              };
            } else if (msg.content.startsWith("計算エラー:")) {
              payload = {
                success: false,
                error_message: msg.content.replace("計算エラー:", "").trim(),
              };
            }
          }

          if (!payload) {
            payload = { expression: "AIからデータを抽出中...", result: "..." };
          }

          if (payload?.success === false) {
            return (
              <div key={messageKey} className="flex w-full flex-col items-start">
                <ChatLabel role="ai" />
                <div className="bg-red-50/80 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 rounded-xl p-4 w-full my-4 shadow-sm backdrop-blur-sm">
                  <div className="flex items-center gap-2 font-bold mb-1">
                    <span>⚠</span>
                    <span>計算エラー</span>
                  </div>
                  <p className="text-sm">
                    {String(payload?.error_message || "不明なエラーが発生しました")}
                  </p>
                </div>
              </div>
            );
          }

          const resultString = String(payload?.result ?? "N/A");
          const isLongText = resultString.length > 40 || resultString.includes("\n");

          return (
            <div key={messageKey} className="flex w-full flex-col items-start">
              <ChatLabel role="ai" />
              <div className="bg-blue-50/40 dark:bg-blue-900/10 rounded-xl border border-blue-100 dark:border-blue-800/40 p-5 my-4 shadow-sm w-full backdrop-blur-sm">
                <div className="flex items-center gap-2 mb-5 pb-3 border-b border-blue-100/60 dark:border-blue-800/40">
                  <span className="text-xl">🧮</span>
                  <h4 className="text-base font-bold text-blue-900 dark:text-blue-100">
                    AI 計算結果
                  </h4>
                </div>

                <div className="space-y-5">
                  <div>
                    <div className="text-xs font-semibold text-blue-400/80 dark:text-blue-500/80 uppercase tracking-wider mb-1.5 ml-1">
                      Expression / Problem
                    </div>
                    <div className="text-sm font-mono text-blue-800 dark:text-blue-200 bg-blue-100/30 dark:bg-blue-900/30 px-4 py-3 rounded-lg border border-blue-100/50 dark:border-blue-800/30 overflow-x-auto whitespace-pre-wrap">
                      {String(payload?.expression || "")}
                    </div>
                  </div>

                  <div>
                    <div className="text-xs font-semibold text-blue-400/80 dark:text-blue-500/80 uppercase tracking-wider mb-1.5 ml-1">
                      Result
                    </div>
                    <div
                      className={
                        isLongText
                          ? "text-base text-slate-700 dark:text-slate-200 whitespace-pre-wrap leading-relaxed bg-white/50 dark:bg-slate-900/30 p-4 rounded-lg border border-blue-50 dark:border-blue-900/30"
                          : "text-4xl font-bold text-blue-600 dark:text-blue-400 tracking-tight ml-1"
                      }
                    >
                      {resultString}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        }

        const { displayMessage, displayBlocks } = extractDisplayData(msg);

        const hasBlocks = displayBlocks.length > 0;
        const isBlockResponse =
          msg?.type === "ui_code" ||
          msg?.response_type === "ui_code" ||
          msg?.type === "project_build" ||
          msg?.response_type === "project_build" ||
          hasBlocks;

        // 4. UI Blocks / Project Build / Artifacts
        if (isBlockResponse) {
          return (
            <WidgetCard key={messageKey} icon="⚡" title="AI Widget">
              {displayMessage && (
                <div className="border-b border-slate-100 pb-3 text-sm text-slate-700 dark:border-slate-700 dark:text-slate-300">
                  <RenderSmartContent value={displayMessage} />
                </div>
              )}

              <div className="mt-3 space-y-4">
                <RenderBlocks
                  blocks={displayBlocks as any[]}
                  apiBaseUrl={apiBaseUrl}
                  onOptionSelect={onOptionSelect}
                  onOpenManualEdit={onOpenManualEdit}
                />
              </div>
            </WidgetCard>
          );
        }/// 5. Normal Chat Messages (自作モデルの generate_chat_response による会話応答もここを通る)
        const role = msg?.role || "assistant";
        const normalContent =
          role === "user" || role === "system"
            ? msg?.content
            : displayMessage || msg?.content;

        return (
          <div
            key={messageKey}
            className={`flex w-full flex-col ${
              role === "user" ? "items-end" : "items-start"
            }`}
          >
            <ChatLabel role={role} />
            <ChatBubble role={role}>
              {role === "assistant" || role === "ai" || role === "user" ? (
                <MarkdownChatBlock 
                  text={String(normalContent || "")} 
                  role={role} 
                  // 💡 追加: これがないとボタンの命令がAiChatPanelに届きません
                  onOptionSelect={onOptionSelect} 
                />
              ) : (
                <RenderSmartContent value={normalContent} />
              )}
            </ChatBubble>
          </div>
        );
      })}

      {isLoading && <LoadingIndicator />}
      <div ref={messagesEndRef} />
    </div>
  );
}
