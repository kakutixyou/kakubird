// frontend/src/hooks/useAiChat.js
import { useState } from 'react';
import { buildCommandPayload } from '../hooks/useCommandRouter';
import { correctTypo } from '../utils/typoCorrector';

export function useAiChat({ onImportDB }) {
  // --- 1. State管理 ---
  const [messages, setMessages] = useState([
    {
      id: Date.now(),
      role: 'assistant',
      content: '<summary>優秀なデータベースエンジニアAI＆CSSジェネレーターとしてスタンバイしました！</summary><details>新規DBの作成、既存DBの読み込み、/sql、/cssコマンドまで対応できます。</details>',
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [isRagMode, setIsRagMode] = useState(false);
  const [forceJsonMode, setForceJsonMode] = useState(false);

  // --- 2. 履歴データのフォーマット共通処理 ---
  const formatHistoryForApi = (currentMessages, lastUserText) => {
    const nextHistory = [
      ...currentMessages,
      { role: 'user', content: lastUserText }
    ];
    return nextHistory.map((m) => {
      let safeContent = m.content;
      if (typeof safeContent === 'object' && safeContent !== null) {
        safeContent = safeContent.message || JSON.stringify(safeContent);
      }
      return { role: m.role, content: String(safeContent) };
    });
  };

  // --- 3. アクション関数 ---
  const loadHistory = (historyName) => {
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now(),
        role: 'system',
        content: `【システム】履歴「${historyName}」を読み込みました。`,
      },
    ]);
    if (onImportDB) onImportDB(historyName);
  };

  const addSystemMessage = (text) => {
    setMessages((prev) => [...prev, { id: Date.now(), role: 'system', content: text }]);
  };

  // --- 4. メッセージ送信ロジック（メイン処理） ---
  const sendMessage = async (rawInput) => {
    if (!rawInput.trim() || isLoading) return;

    const userMsg = { id: Date.now(), role: 'user', content: rawInput };
    const { correctedText, wasCorrected, detectedTargets } = correctTypo(rawInput);
    
    // APIへ渡す履歴をあらかじめ生成
    const apiHistory = formatHistoryForApi(messages, correctedText);

    // フロントの画面（State）を更新
    setMessages((prev) => {
      const updated = [...prev, userMsg];
      if (wasCorrected) {
        updated.push({
          id: Date.now() + 1,
          role: 'system',
          content: `💡 「${detectedTargets.join('、')}」として補正して処理します。`,
        });
      }
      return updated;
    });

    // ペイロード組み立て
    const commandPayload = buildCommandPayload(correctedText);
    const apiPayload = {
      ...commandPayload,
      message: correctedText, 
      force_json_ui: forceJsonMode,
      history: apiHistory,
      mode: isRagMode ? "rag_chat" : undefined,
    };

    setIsLoading(true);

    try {
      console.log("🚀 [useAiChat] 1. API送信直前 - ペイロード:", apiPayload);
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(apiPayload),
      });

      console.log("📡 [useAiChat] 2. レスポンス受信 - ステータス:", response.status, response.statusText);
<<<<<<< HEAD
      
      // 👇 ==========================================
      // 👇 エラーハンドリングを親切に強化
      // 👇 ==========================================
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error("404_NOT_FOUND");
        }
        throw new Error(`HTTP ${response.status}`);
      }
=======
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
>>>>>>> 5d792e5e62f131b04c45504a321405bdd0a8bb17

      const contentType = response.headers.get('content-type');
      console.log("ℹ️ [useAiChat] 3. Content-Type:", contentType);

// ====================================================================
      // パターンA: JSONレスポンス（一括返却）
      // ====================================================================
      if (contentType && contentType.includes('application/json')) {
        const data = await response.json();
        console.log("📥 バックエンドから届いたデータ:", data);

        // 💡 【最優先：今回の ui_code 構造を確実にキャッチする】
<<<<<<< HEAD
        if (data.response_type === 'ui_code' || data.content?.blocks) {
=======
        // data.response_type が 'ui_code' であるか、または data.content の中に blocks が存在する場合
        if (data.response_type === 'ui_code' || data.content?.blocks) {
          // data.content 内、または data 直下の message と blocks を安全に救出
>>>>>>> 5d792e5e62f131b04c45504a321405bdd0a8bb17
          const blocks = data.content?.blocks || data.blocks || [];
          const textMsg = data.content?.message || data.message || data.response || "フォルダ構造を生成しました。";
          
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now() + 2,
              role: 'assistant',
              source: data.source || 'ui_code',
              type: 'ui_code',
              response_type: 'ui_code',
<<<<<<< HEAD
=======
              // 💡 ChatMessage.jsx が一番読み込みやすいオブジェクト形式に変換して text に格納
>>>>>>> 5d792e5e62f131b04c45504a321405bdd0a8bb17
              text: {
                message: textMsg,
                blocks: blocks
              },
              blocks: blocks
            },
          ]);
<<<<<<< HEAD
          return;
        }

        // ② 統一フォーマット対応のフォールバック
=======
          return; // 処理完了なのでここで終了
        }

        // ② 統一フォーマット対応のフォールバック (SQLHandlerなど、以前正常に動いていた定義)
>>>>>>> 5d792e5e62f131b04c45504a321405bdd0a8bb17
        if (data.response !== undefined && data.source !== undefined) {
          const hasBlocks = data.blocks && data.blocks.length > 0;
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now() + 2,
              role: 'assistant',
              source: data.source,
              type: hasBlocks ? 'ui_code' : 'text',
              response_type: hasBlocks ? 'ui_code' : 'text',
              text: hasBlocks 
                ? { message: data.response, blocks: data.blocks }
                : data.response,
              blocks: data.blocks || null
            },
          ]);
          return;
        }

<<<<<<< HEAD
        // ③ 既存の特殊コンポーネント用フォーマット分岐
=======
        // ③ 既存の特殊コンポーネント用フォーマット分岐 (条件が重ならないもの)
>>>>>>> 5d792e5e62f131b04c45504a321405bdd0a8bb17
        if (data.response_type === 'multi_select' || data.type === 'multi_select') {
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now() + 2,
              role: 'assistant',
              type: 'multi_select',
              question: data.question || data.content?.question,
              options: data.options || data.content?.options,
              plugin: data.plugin || data.content?.plugin,
            },
          ]);
        } 
        else {
          // ④ 完全に通常の文字列テキストレスポンスとして処理
          const finalContent = typeof data.content === 'string' ? data.content : (data.response || data.message || JSON.stringify(data));
          setMessages((prev) => [
            ...prev,
            { 
              id: Date.now() + 2, 
              role: 'assistant', 
              source: data.source || 'default',
              type: 'text',
              response_type: 'text',
              text: finalContent 
            },
          ]);
        }
      }
      // ====================================================================
      // パターンB: ストリーミング（文字をパラパラ表示）
      // ====================================================================
      else {
        console.log("🌊 [useAiChat] 4. ストリーミングルートに突入しました");
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        const assistantMsgId = Date.now() + 2;

<<<<<<< HEAD
=======
        // ストリーミング時は最初はプレーンテキスト(content属性ではなくChatMessageに合わせるため型を共通化)
>>>>>>> 5d792e5e62f131b04c45504a321405bdd0a8bb17
        setMessages((prev) => [...prev, { id: assistantMsgId, role: 'assistant', type: 'text', text: '' }]);

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunkText = decoder.decode(value, { stream: true });
          const lines = chunkText.split('\n');
          let newText = "";

          for (const line of lines) {
            if (line.trim() === '') continue;
            if (line.includes('[Ollama Stream Error')) {
              newText += line;
              continue;
            }
            try {
              const parsed = JSON.parse(line);
              if (parsed.message?.content) newText += parsed.message.content;
            } catch (e) {
              console.log("parse skip:", e);
            }
          }

          if (newText) {
            setMessages((prev) =>
              prev.map((msg) => msg.id === assistantMsgId ? { ...msg, text: (msg.text || '') + newText } : msg)
            );
          }
        }

<<<<<<< HEAD
=======
        // ストリーム終了後のエラーチェック
>>>>>>> 5d792e5e62f131b04c45504a321405bdd0a8bb17
        setMessages((prev) => {
          const assistantMessage = prev.find((msg) => msg.id === assistantMsgId);
          if (assistantMessage && String(assistantMessage.text).includes('[Ollama Stream Error')) {
            return prev.map((msg) =>
              msg.id === assistantMsgId
                ? {
                    ...msg,
                    text: '<summary>⚠️ Ollama 接続エラー</summary><details>ローカルのOllamaサーバーが起動しているか、接続設定を確認してください。</details>',
                  }
                : msg
            );
          }
          return prev;
        });
      }
    } catch (error) {
      console.error('通信エラー:', error);
<<<<<<< HEAD
      // 👇 ==========================================
      // 👇 エラーメッセージを親切なものに変更
      // 👇 ==========================================
      if (error.message === "404_NOT_FOUND") {
        addSystemMessage('⚠️ AIサーバー(バックエンド)が見つかりません。Python側の起動ログにエラーが出ていないか確認してください。');
      } else {
        addSystemMessage('⚠️ サーバー通信エラーが発生しました。バックエンドの状態を確認してください。');
      }
=======
      addSystemMessage('⚠️ サーバー通信エラーが発生しました。バックエンドの状態を確認してください。');
>>>>>>> 5d792e5e62f131b04c45504a321405bdd0a8bb17
    } finally {
      setIsLoading(false);
    }
  };

  // --- 5. 画像送信（OCR解析）ロジック ---
  const sendImage = async (file) => {
    if (!file || isLoading) return;

    setIsLoading(true);
    setMessages((prev) => [
      ...prev,
      { id: Date.now(), role: 'user', text: `📸 画像データを送信しました: ${file.name}` },
    ]);

    try {
      const base64Image = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });

      const apiPayload = {
        message: "【画像解析リクエスト】", 
        image_base64: base64Image,
        force_json_ui: forceJsonMode,
        history: formatHistoryForApi(messages, "【画像送信】"),
      };

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(apiPayload),
      });

<<<<<<< HEAD
      // 👇 画像側も同じく404対策
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error("404_NOT_FOUND");
        }
        throw new Error(`HTTP ${response.status}`);
      }

=======
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
>>>>>>> 5d792e5e62f131b04c45504a321405bdd0a8bb17
      const data = await response.json();

      if (data.response !== undefined || data.content !== undefined) {
        const hasBlocks = data.blocks && data.blocks.length > 0;
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now() + 2,
            role: 'assistant',
            type: hasBlocks ? 'ui_code' : (data.response_type || 'text'),
            text: hasBlocks 
              ? { message: data.response || data.message || data.content?.message, blocks: data.blocks }
              : (data.content || data.response),
            blocks: data.blocks || null
          },
        ]);
      }
    } catch (error) {
      console.error('画像送信・OCR通信エラー:', error);
<<<<<<< HEAD
      if (error.message === "404_NOT_FOUND") {
        addSystemMessage('⚠️ AIサーバーが見つかりません。画像解析の受付窓口が存在しません。');
      } else {
        addSystemMessage('⚠️ 画像解析エラー。バックエンドのOCRモジュールまたはAPIの状態を確認してください。');
      }
=======
      addSystemMessage('⚠️ 画像解析エラー。バックエンドのOCRモジュールまたはAPIの状態を確認してください。');
>>>>>>> 5d792e5e62f131b04c45504a321405bdd0a8bb17
    } finally {
      setIsLoading(false);
    }
  };

  return {
    messages,
    isLoading,
    sendMessage,
    sendImage,
    loadHistory,
    addSystemMessage,
    isRagMode,
    setIsRagMode,
    forceJsonMode,
    setForceJsonMode
  };
}