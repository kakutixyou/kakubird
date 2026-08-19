// AIChatMessageList.jsx
import React, { useRef, useEffect } from 'react';
import MultiSelectMessage from './MultiSelectMessage';

// 
// ブロック名簿は blocks.jsx に一元化（重複登録によるバグを防止）
// 
import { BLOCK_COMPONENTS } from './blocks';
// 
// ui フォルダから純粋なデザイン部品をインポート
// 
import { ChatBubble, ChatLabel } from './ui/ChatBubble';
import { WidgetCard } from './ui/WidgetCard';
import { Collapsible } from './ui/Collapsible';
import { LoadingIndicator } from './ui/LoadingIndicator';

export default function AiChatMessageList({ messages, isLoading, onOptionSelect, onOpenManualEdit }) {
  const messagesEndRef = useRef(null);

  // Auto Scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Smart Content Renderer
  const renderSmartContent = (text) => {
    if (typeof text !== 'string') {
      // 💡 もしオブジェクト形式のメッセージが届いてもクラッシュしないようにセーフティガード
      if (text && typeof text === 'object') {
        return <div className="whitespace-pre-wrap">{text.message || JSON.stringify(text)}</div>;
      }
      return <div className="text-red-400 text-sm">データ形式エラー: {String(text)}</div>;
    }

    if (text.includes('<summary>') && text.includes('<details>')) {
      const summaryText = text.match(/<summary>([\s\S]*?)<\/summary>/)?.[1] || '結論';
      const detailsText = text.match(/<details>([\s\S]*?)<\/details>/)?.[1] || '';
      return <Collapsible summaryText={summaryText} detailsText={detailsText} />;
    }

    return <div className="whitespace-pre-wrap">{text}</div>;
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.map((msg) => {
        // 1. Multi Select Message
        if (msg.type === 'multi_select') {
          return (
            <div key={msg.id} className="flex flex-col items-start">
              <ChatLabel role="ai" />
              <MultiSelectMessage message={msg} onSubmit={onOptionSelect} />
            </div>
          );
        }

        // 2. GitHub Search UI
        if (msg.response_type === 'github_search') {
          const { message, repositories } = msg.content || {};
          return (
            <WidgetCard key={msg.id} icon="🔍" title="GitHub Search">
              {message && (
                <div className="text-sm text-slate-700 dark:text-slate-300 pb-3 border-b border-slate-100 dark:border-slate-700">
                  {renderSmartContent(message)}
                </div>
              )}
              <div className="space-y-3 mt-2">
                {repositories?.map(repo => (
                  <div key={repo.id} className="text-sm bg-slate-50 dark:bg-slate-800 p-2 rounded border border-slate-200 dark:border-slate-700">{repo.name}</div>
                ))}
              </div>
            </WidgetCard>
          );
        }

        // 3. UI Blocks (Artifacts)
        if (msg.type === 'ui_code' || msg.response_type === 'ui_code') {
          // 💡 【超頑丈ガード】データが msg.content の中、msg.text の中、あるいは直下のどこにあっても100%救出する
          const displayMessage = msg.content?.message || msg.text?.message || msg.message || "";
          const displayBlocks = msg.content?.blocks || msg.text?.blocks || msg.blocks || [];

          return (
            <WidgetCard key={msg.id} icon="⚡" title="AI Widget">
              {displayMessage && (
                <div className="text-sm text-slate-700 dark:text-slate-300 pb-3 border-b border-slate-100 dark:border-slate-700">
                  {renderSmartContent(displayMessage)}
                </div>
              )}

              <div className="space-y-4 mt-3">
                {displayBlocks?.map((block, bIdx) => {
                  // 💡 ブロック名簿は blocks.jsx の BLOCK_COMPONENTS を単一の情報源として使用
                  const BlockComponent = BLOCK_COMPONENTS[block.type];
                  if (!BlockComponent) {
                    return <div key={bIdx} className="text-red-400 text-xs">未定義のブロック: {block.type}</div>;
                  }

                  // 💡 【超重要リファクタリング】
                  // 既存のコンポーネント用に {...block.props} でバラして渡す挙動を維持しつつ、
                  // 新しい DeploymentBlock 用に「block={block}」オブジェクトそのものも一緒に内包して引き渡す！
                  return (
                    <BlockComponent
                      key={bIdx}
                      block={block}
                      {...block.props}
                      onOptionSelect={onOptionSelect}
                      onOpenManualEdit={onOpenManualEdit}
                    />
                  );
                })}
              </div>
            </WidgetCard>
          );
        }

        // 4. Normal Chat Messages
        return (
          <div key={msg.id} className={`flex flex-col w-full ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
            <ChatLabel role={msg.role} />
            <ChatBubble role={msg.role}>
              {msg.role === 'user' || msg.role === 'system' ? msg.content : renderSmartContent(msg.content)}
            </ChatBubble>
          </div>
        );
      })}

      {isLoading && <LoadingIndicator />}

      <div ref={messagesEndRef} />
    </div>
  );
}