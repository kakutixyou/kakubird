// frontend/src/hooks/useAiChat.js ウィジェットを追加する場合後でchatResponseMapper.jsも送ること
import { useCallback, useMemo, useRef, useState } from 'react';
import { buildCommandPayload } from '../hooks/useCommandRouter';
import { correctTypo } from '../utils/typoCorrector';
import { buildAssistantMessageFromJson } from './chat/chatResponseMapper';
import {
  CHAT_MODES,
  DEFAULT_CHAT_MODE,
  buildApiError,
  extractBackendStatus,
  extractStreamText,
  formatErrorMessage,
  formatHistoryForApi,
  isObject,
  normalizeChatMode,
  readFileAsDataUrl,
  readStoredChatMode,
  saveStoredChatMode,
  valueToText,
} from './chat/chatUtils';

export { CHAT_MODES, DEFAULT_CHAT_MODE };

export function useAiChat({ onImportDB, initialChatMode = DEFAULT_CHAT_MODE } = {}) {
  const firstMode = normalizeChatMode(
    readStoredChatMode(),
    normalizeChatMode(initialChatMode, DEFAULT_CHAT_MODE),
  );

  const [messages, setMessages] = useState([
    {
      id: Date.now(),
      role: 'assistant',
      type: 'text',
      source: 'system',
      content:
        '<summary>アプリ開発AIとしてスタンバイしました！</summary>'
        + '<details>AIモードを標準にして、チャットボットモードへも切り替えられます。</details>',
    },
  ]);

  const [isLoading, setIsLoading] = useState(false);
  const [isRagMode, setIsRagMode] = useState(false);
  const [forceJsonMode, setForceJsonMode] = useState(false);
  const [latestElevator, setLatestElevator] = useState(null);
  const [chatMode, setChatModeState] = useState(firstMode);
  const [backendStatus, setBackendStatus] = useState({
    requestedMode: firstMode,
    mode: firstMode,
    aiEnabled: firstMode === CHAT_MODES.AI,
    chatbotEnabled: firstMode === CHAT_MODES.CHATBOT,
    source: 'initial',
    llmAvailable: null,
    confirmed: false,
    updatedAt: null,
  });

  const requestInFlightRef = useRef(false);
  const abortControllerRef = useRef(null);
  const nextIdRef = useRef(Date.now() + 1);

  const nextMessageId = useCallback(() => {
    nextIdRef.current += 1;
    return nextIdRef.current;
  }, []);

  const addSystemMessage = useCallback((text) => {
    setMessages((prev) => [
      ...prev,
      { id: nextMessageId(), role: 'system', type: 'text', source: 'system', content: String(text), text: String(text) },
    ]);
  }, [nextMessageId]);

  const setChatMode = useCallback((nextMode) => {
    const normalized = normalizeChatMode(nextMode, DEFAULT_CHAT_MODE);
    setChatModeState(normalized);
    saveStoredChatMode(normalized);
    setBackendStatus((prev) => ({
      ...prev,
      requestedMode: normalized,
      mode: normalized,
      aiEnabled: normalized === CHAT_MODES.AI,
      chatbotEnabled: normalized === CHAT_MODES.CHATBOT,
      confirmed: false,
      updatedAt: new Date().toISOString(),
    }));
  }, []);

  const toggleChatMode = useCallback(() => {
    setChatMode(chatMode === CHAT_MODES.AI ? CHAT_MODES.CHATBOT : CHAT_MODES.AI);
  }, [chatMode, setChatMode]);

  const syncBackendStatus = useCallback((data, requestedMode) => {
    const status = extractBackendStatus(data, requestedMode);
    setBackendStatus(status);
    if (status.confirmed) {
      setChatModeState(status.mode);
      saveStoredChatMode(status.mode);
    }
    return status;
  }, []);

  const loadHistory = useCallback((historyName) => {
    addSystemMessage(`【システム】履歴「${historyName}」を読み込みました。`);
    if (onImportDB) onImportDB(historyName);
  }, [addSystemMessage, onImportDB]);

  const cancelRequest = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  const consumeStreamingResponse = useCallback(async (response, requestedMode) => {
    if (!response.body) throw new Error('STREAM_BODY_NOT_FOUND');

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    const assistantMessageId = nextMessageId();
    let buffer = '';
    let fullText = '';

    setMessages((prev) => [
      ...prev,
      {
        id: assistantMessageId,
        role: 'assistant',
        type: 'text',
        response_type: 'text',
        source: 'stream',
        chat_mode: requestedMode,
        ai_enabled: requestedMode === CHAT_MODES.AI,
        content: '',
        text: '',
      },
    ]);

    const patchMsg = (patch) => setMessages((prev) => (
      prev.map((m) => (m.id === assistantMessageId ? { ...m, ...patch } : m))
    ));

    const consumeLine = (rawLine) => {
      const trimmed = rawLine.trim();
      if (!trimmed || trimmed === '[DONE]') return;
      const candidate = trimmed.startsWith('data:') ? trimmed.slice(5).trim() : trimmed;
      if (!candidate || candidate === '[DONE]') return;

      try {
        const parsed = JSON.parse(candidate);
        const streamStatus = extractBackendStatus(parsed, requestedMode);
        if (streamStatus.confirmed || streamStatus.source !== 'unknown') {
          setBackendStatus(streamStatus);
          if (streamStatus.confirmed) {
            setChatModeState(streamStatus.mode);
            saveStoredChatMode(streamStatus.mode);
          }
        }
        if (isObject(parsed.elevator)) {
          setLatestElevator(parsed.elevator);
          patchMsg({ elevator: parsed.elevator });
        }
        const chunk = extractStreamText(parsed);
        if (chunk) {
          fullText += chunk;
          patchMsg({ content: fullText, text: fullText });
        }
      } catch {
        fullText += candidate;
        patchMsg({ content: fullText, text: fullText });
      }
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() ?? '';
      lines.forEach(consumeLine);
    }
    buffer += decoder.decode();
    if (buffer.trim()) consumeLine(buffer);

    if (!fullText) {
      patchMsg({ content: 'ストリーミング応答は完了しましたが、表示できる本文がありませんでした。' });
    }
  }, [nextMessageId]);

  // sendMessage / sendImage 共通の実行パイプライン
  const executeChatRequest = useCallback(async (apiPayload, requestedMode, requestLabel) => {
    requestInFlightRef.current = true;
    setIsLoading(true);
    setBackendStatus((prev) => ({ ...prev, requestedMode, confirmed: false }));

    try {
      const controller = new AbortController();
      abortControllerRef.current = controller;

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(apiPayload),
        signal: controller.signal,
      });

      if (!response.ok) throw await buildApiError(response);

      const contentType = response.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        const data = await response.json();
        const status = syncBackendStatus(data, requestedMode);
        const { elevator, message } = buildAssistantMessageFromJson(data, status, nextMessageId());
        if (elevator) setLatestElevator(elevator);
        setMessages((prev) => [...prev, message]);
      } else {
        await consumeStreamingResponse(response, requestedMode);
      }
    } catch (error) {
      console.error(`[useAiChat] ${requestLabel}エラー:`, error);
      addSystemMessage(formatErrorMessage(error, requestLabel));
    } finally {
      requestInFlightRef.current = false;
      abortControllerRef.current = null;
      setIsLoading(false);
    }
  }, [addSystemMessage, consumeStreamingResponse, nextMessageId, syncBackendStatus]);

  const sendMessage = useCallback(async (rawInput) => {
    const input = typeof rawInput === 'string' ? rawInput : valueToText(rawInput);
    if (!input.trim() || requestInFlightRef.current) return;

    const requestedMode = chatMode;
    const { correctedText, wasCorrected, detectedTargets = [] } = correctTypo(input);
    const safeCorrectedText = valueToText(correctedText || input);
    const commandPayload = buildCommandPayload(safeCorrectedText);

    setMessages((prev) => {
      const updated = [
        ...prev,
        { id: nextMessageId(), role: 'user', type: 'text', content: input, text: input, chat_mode: requestedMode },
      ];
      if (wasCorrected) {
        updated.push({
          id: nextMessageId(),
          role: 'system',
          type: 'text',
          source: 'typo_corrector',
          content: detectedTargets.length > 0
            ? `💡「${detectedTargets.join('、')}」として補正して処理します。`
            : `💡「${safeCorrectedText}」として補正して処理します。`,
        });
      }
      return updated;
    });

    const apiPayload = {
      ...(isObject(commandPayload) ? commandPayload : {}),
      message: safeCorrectedText,
      force_json_ui: forceJsonMode,
      history: formatHistoryForApi(messages, safeCorrectedText),
      mode: isRagMode ? 'rag_chat' : undefined,
      chat_mode: requestedMode,
      ai_mode: requestedMode === CHAT_MODES.AI,
    };

    await executeChatRequest(apiPayload, requestedMode, 'メッセージ送信');
  }, [chatMode, executeChatRequest, forceJsonMode, isRagMode, messages, nextMessageId]);

  const sendImage = useCallback(async (file) => {
    if (!file || requestInFlightRef.current) return;

    const requestedMode = chatMode;
    setMessages((prev) => [
      ...prev,
      {
        id: nextMessageId(),
        role: 'user',
        type: 'text',
        content: `📸 画像データを送信しました: ${file.name}`,
        text: `📸 画像データを送信しました: ${file.name}`,
        chat_mode: requestedMode,
      },
    ]);

    try {
      const base64Image = await readFileAsDataUrl(file);
      const apiPayload = {
        message: '【画像解析リクエスト】',
        image_base64: base64Image,
        force_json_ui: forceJsonMode,
        history: formatHistoryForApi(messages, '【画像送信】'),
        mode: isRagMode ? 'rag_chat' : undefined,
        chat_mode: requestedMode,
        ai_mode: requestedMode === CHAT_MODES.AI,
      };
      await executeChatRequest(apiPayload, requestedMode, '画像解析');
    } catch (error) {
      addSystemMessage(formatErrorMessage(error, '画像読み込み'));
    }
  }, [addSystemMessage, chatMode, executeChatRequest, forceJsonMode, isRagMode, messages, nextMessageId]);

  const modeLabel = useMemo(() => (chatMode === CHAT_MODES.AI ? 'AI' : 'チャットボット'), [chatMode]);

  return {
    messages,
    isLoading,
    latestElevator,
    setLatestElevator,
    sendMessage,
    sendImage,
    cancelRequest,
    loadHistory,
    addSystemMessage,
    isRagMode,
    setIsRagMode,
    forceJsonMode,
    setForceJsonMode,
    chatMode,
    setChatMode,
    toggleChatMode,
    modeLabel,
    isAiMode: chatMode === CHAT_MODES.AI,
    isChatbotMode: chatMode === CHAT_MODES.CHATBOT,
    backendStatus,
    backendMode: backendStatus.mode,
    backendSource: backendStatus.source,
    isBackendModeConfirmed: backendStatus.confirmed,
  };
}