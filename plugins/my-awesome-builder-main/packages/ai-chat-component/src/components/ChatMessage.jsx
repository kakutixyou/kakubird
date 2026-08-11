/**
 * ChatMessage.jsx
 * ===============
 * Renders a single chat message bubble.
 * Supports user, AI, and error message roles, as well as Custom UI blocks (ui_code).
 */
import React from 'react';
// 💡 先ほど有効化した RenderBlocks コンポーネントをインポートします
// ※配置場所（階層）に合わせてインポートパスが異なる場合は調整してください
import { RenderBlocks } from './blocks'; 

/**
 * Small badge showing which API/source answered the message.
 */
function SourceBadge({ source }) {
  if (!source) return null;
  const labels = {
    sql: 'SQL API',
    css: 'CSS API',
    ui_code: 'Deployment API', // 💡 デプロイメント用のラベル定義を追加
    default: 'AI',
  };
  const label = labels[source] ?? source;
  return (
    <span className="ai-chat__source-badge" aria-label={`Answered by ${label}`}>
      {label}
    </span>
  );
}

/**
 * @param {object}  props
 * @param {'user'|'ai'} props.role
 * @param {string|object} props.text  - 文字列、またはui_code時に届くObject形式のcontent
 * @param {string}  [props.source]    - API source badge (e.g. "sql", "css", "ui_code")
 * @param {boolean} [props.isError]
 * @param {string}  [props.response_type] - バックエンドからのレスポンス種別 ("text" | "ui_code")
 * @param {array}   [props.blocks]    - ui_codeの際にレンダリングするカスタムUIブロックの配列
 * @param {function} [props.onOptionSelect]  - ブロック内ボタンのアクション用ハンドラ
 * @param {function} [props.onOpenManualEdit] - ブロック内ボタンの手動編集用ハンドラ
 */
function ChatMessage({ 
  role, 
  text, 
  source, 
  isError, 
  response_type, 
  blocks,
  onOptionSelect,
  onOpenManualEdit
}) {
  const isUser = role === 'user';

  // 💡 【超重要】バックエンドから "ui_code" が届いた場合、または引数がオブジェクトの場合のデータ救出
  // バックエンドの仕様変更や親の渡し方に左右されないように多重でガードをかけます
  const isUiCode = response_type === 'ui_code' || text?.response_type === 'ui_code' || source === 'ui_code';

  // 1. 表示するメインテキストの判定
  let displayRawText = '';
  if (typeof text === 'string') {
    displayRawText = text;
  } else if (text && typeof text === 'object') {
    // textプロパティ自体にオブジェクトが丸ごと入ってきた場合
    displayRawText = text.message || text.content?.message || '';
  }

  // 2. 表示するカスタムブロック(blocks)の抽出
  let uiBlocks = blocks;
  if (!uiBlocks && text && typeof text === 'object') {
    uiBlocks = text.blocks || text.content?.blocks;
  }

  // 3. バッジソースの自動補正
  const finalSource = isUiCode ? 'ui_code' : source;

  const bubbleClass = [
    'ai-chat__bubble',
    isUser ? 'ai-chat__bubble--user' : 'ai-chat__bubble--ai',
    isError ? 'ai-chat__bubble--error' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={`ai-chat__message ${isUser ? 'ai-chat__message--user' : 'ai-chat__message--ai'}`}>
      {!isUser && (
        <div className="ai-chat__avatar" aria-hidden="true">
          {isError ? '⚠️' : '🤖'}
        </div>
      )}
      
      <div className={bubbleClass}>
        {/* ① AIからのテキストメッセージ（説明文やset.pyのソースコードなど）の描画 */}
        {displayRawText ? (
          displayRawText.split('\n').map((line, i, lines) => (
            <React.Fragment key={i}>
              {line}
              {i < lines.length - 1 && <br />}
            </React.Fragment>
          ))
        ) : (
          // 万が一テキストが空でブロックだけがある場合、ローディング対策等でフォールバック
          !isUser && !isError && !uiBlocks && <span className="text-slate-400">応答を解析中...</span>
        )}

        {/* ② 💡 [新機能] response_typeが ui_code の場合、テキストの下にフォルダツリーUIを展開する */}
        {isUiCode && uiBlocks && (
          <div className="ai-chat__custom-blocks-wrapper mt-3">
            <RenderBlocks 
              blocks={uiBlocks} 
              onOptionSelect={onOptionSelect}
              onOpenManualEdit={onOpenManualEdit}
            />
          </div>
        )}

        {!isUser && !isError && <SourceBadge source={finalSource} />}
      </div>
      
      {isUser && (
        <div className="ai-chat__avatar ai-chat__avatar--user" aria-hidden="true">
          👤
        </div>
      )}
    </div>
  );
}

export default ChatMessage;