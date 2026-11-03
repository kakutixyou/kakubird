// frontend/src/components/blocks/MarkdownChatBlock.tsx
import React, { useState } from 'react';

// ==========================================
// 1. 型定義 (TypeScriptの恩恵)
// 1ヶ月後: ここに新しいprops（例: onAction）を追加すれば、エディタが自動で補完・警告してくれます。
// ==========================================

export interface MarkdownChatBlock {
  /** AIまたはユーザーが発言したテキスト */
  text?: string;
  /** 話者の役割（デザインの出し分けに使用） */
  role?: string; 
  /** 将来、上位コンポーネント（useAiChat等）にアクションを伝えるための関数 */
  onOptionSelect?: (payload: any) => void; 
}

interface DevActionModalProps {
  isOpen: boolean;
  onClose: () => void;
  text: string;
  role: string;
}

// ==========================================
// 2. 分離された開発者ツールモーダル (アプローチA)
// 1ヶ月後: ボタンを増やしたい時は、このコンポーネント内に <button> を追加するだけです。
// メインの表示ロジック（MarkdownChatBlock）を汚さずに済みます。
// ==========================================
function DevActionModal({ isOpen, onClose, text, role }: DevActionModalProps) {
  if (!isOpen) return null;

  return (
    // 背景の半透明黒幕。クリックで閉じる処理(onClose)を配置。
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" 
      onClick={onClose}
    >
      {/* モーダル本体。e.stopPropagation() により、ここをクリックしても背景クリック(閉じる)が発動しないようにする */}
      <div 
        className="bg-slate-900 border border-slate-700 w-80 rounded-xl shadow-2xl p-4 flex flex-col gap-2"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center border-b border-slate-700 pb-2 mb-2">
          <span className="font-bold text-slate-200 text-sm">🛠️ 開発者特権メニュー</span>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-lg leading-none">
            ×
          </button>
        </div>
        
        <div className="text-xs text-slate-400 mb-2">
          対象: {role === 'user' ? 'ユーザーの入力' : 'AIの出力'}
        </div>

        {/* 
          機能拡張のヒント:
          ここで onClick={() => onOptionSelect({ action: 'fuzz', text })} のようにして
          AiChatPanel.jsx までイベントを飛ばせば、ChatHandler.py と連携できます。
        */}
        <button className="text-left text-xs bg-slate-800 hover:bg-indigo-900/50 text-slate-300 p-2 rounded transition-colors border border-slate-700 hover:border-indigo-500">
          🐛 Fuzzingテストを実行 (WIP)
        </button>
        <button className="text-left text-xs bg-slate-800 hover:bg-emerald-900/50 text-slate-300 p-2 rounded transition-colors border border-slate-700 hover:border-emerald-500">
          🧠 他のAI連携用プロンプトを生成 (WIP)
        </button>
        <button className="text-left text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 p-2 rounded transition-colors border border-slate-700">
          💾 テストケースとしてエクスポート (WIP)
        </button>
        <button className="text-left text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 p-2 rounded transition-colors border border-slate-700">
          🔍 Raw JSONをインスペクト (WIP)
        </button>
      </div>
    </div>
  );
}

// ==========================================
// 3. メインコンポーネント (テキスト描画とツールバー)
// ==========================================
export default function MarkdownChatBlock({ text, role = 'ai', onOptionSelect }: MarkdownChatBlock) {
  const [copied, setCopied] = useState(false);
  const [showProgress, setShowProgress] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // textが存在しない場合のフォールバック
  if (!text) return null;

  // role判定（'user' の場合は背景が青いため、文字や線の色を反転させる）
  const isUser = role === 'user';

  // クリップボードへのコピー処理
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      // 2秒後に「コピー完了」の表示を元に戻す
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error('Failed to copy', e);
    }
  };

  return (
    <div className={`w-full leading-relaxed space-y-2 text-sm md:text-base ${isUser ? 'text-white' : 'text-slate-800 dark:text-slate-200'}`}>
      
      {/* --- テキスト本文 --- */}
      <div className="whitespace-pre-wrap break-words">
        {text}
      </div>
      
      {/* --- ツールバー --- */}
      {/* ユーザーとAIで区切り線(border)の色を出し分ける */}
      <div className={`pt-2 flex flex-wrap items-center gap-4 mt-2 border-t ${isUser ? 'border-indigo-400/50' : 'border-slate-100 dark:border-slate-700/50'}`}>
        
        {/* 1. コピーボタン (全ロール共通) */}
        <button
          onClick={handleCopy}
          className={`mt-1 text-xs flex items-center gap-1 transition-colors ${
            isUser 
              ? 'text-indigo-200 hover:text-white' 
              : 'text-slate-500 hover:text-indigo-600 dark:hover:text-indigo-400'
          }`}
        >
          {copied ? '✅ コピー完了' : '📋 コピー'}
        </button>

        {/* 2. 進捗解析ボタン (AIの時のみ表示) */}
        {!isUser && (
          <button
            onClick={() => setShowProgress(!showProgress)}
            className="mt-1 text-xs flex items-center gap-1 text-slate-500 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors"
          >
            📊 進捗解析 (Dev)
          </button>
        )}

        {/* 3. Dev Actions モーダル起動ボタン (全ロール共通) */}
        <button
          onClick={() => setIsModalOpen(true)}
          className={`mt-1 text-xs flex items-center gap-1 transition-colors ${
            isUser 
              ? 'text-emerald-200 hover:text-white' 
              : 'text-slate-500 hover:text-emerald-600 dark:hover:text-emerald-400'
          }`}
        >
          🛠️ Dev Actions
        </button>
      </div>

      {/* --- 進捗解析パネル展開エリア --- */}
      {!isUser && showProgress && (
        <div className="mt-3 p-3 bg-slate-950 text-emerald-400 font-mono text-xs rounded-lg border border-slate-800 shadow-inner">
          <p className="font-bold text-slate-300 mb-2">🚀 to_model Internal Status</p>
          <ul className="space-y-1">
            <li>[✓] 1番の目標: 単純計算モジュール - 77%達成</li>
            <li>[↻] 2番の目標: ローカル KnowledgeRouter 統合 - 45%達成</li>
            <li>[ ] 3番の目標: 自動UI構築と自己修復 - 12%達成</li>
          </ul>
        </div>
      )}

      {/* --- Dev Action モーダル展開エリア --- */}
      {/* setIsModalOpen(true) になると、ここで定義した分離コンポーネントが描画される */}
      <DevActionModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
        text={text} 
        role={role} 
      />
      
    </div>
  );
 }
// プロンプトを後から変更・編集できる機能は非常に強力ですが、実装方法によっては状態の不整合（バグ）や意図せぬ悪用（脆弱性）のリスクが伴います。

// 具体的には、以下の3つのリスクに注意する必要があります。

// 履歴データの不整合（バグ）: 会話の途中で過去のプロンプトを書き換えると、フロントエンドの表示とバックエンド（ConversationState等）が保持している履歴データにズレが生じやすくなります。正しく履歴配列を「その時点まで巻き戻して再構築」しないと、AIが文脈を見失ってバグを引き起こします。

// ガードレールの破壊（悪用）: もし「AIのシステムプロンプト（ペルソナや禁止事項）」をUIから自由に上書きできる仕様にした場合、悪意のあるユーザーがガードレールを消去し、攻撃的な出力や機密情報の漏洩を誘発するプロンプトインジェクション（Jailbreak）が容易になります。

// コンテキストの矛盾: 前半の会話と、書き換え後のプロンプトで前提条件が矛盾した場合、LLMが混乱してハルシネーション（幻覚）を生成する確率が跳ね上がります。

// 安全に実装するための定石としては、過去のメッセージを直接上書きするのではなく「その時点からチャットを別スレッドとして分岐（フォーク）させる」設計にする手法があります。

// 今回実装を検討している「プロンプトを変えるボタン」とは、自分が送信した過去のメッセージを編集する機能でしょうか？それとも、AIのシステムプロンプト（裏側の指示設定）を直接書き換える機能のことですか？
