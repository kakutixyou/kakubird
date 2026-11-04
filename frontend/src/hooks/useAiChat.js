// frontend/src/hooks/useAiChat.js
import { useCallback, useMemo, useRef, useState } from 'react';
import { buildCommandPayload } from '../hooks/useCommandRouter';
import { correctTypo } from '../utils/typoCorrector';

export const CHAT_MODES = Object.freeze({
  AI: 'ai',
  CHATBOT: 'chatbot',
});

export const DEFAULT_CHAT_MODE = CHAT_MODES.AI;

const CHAT_MODE_STORAGE_KEY = 'ai_chat_mode';

const isObject = (value) => (
  value !== null
  && typeof value === 'object'
  && !Array.isArray(value)
);

const normalizeChatMode = (value, fallback = null) => {
  if (value === CHAT_MODES.AI || value === CHAT_MODES.CHATBOT) {
    return value;
  }
  return fallback;
};

const readStoredChatMode = () => {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    return normalizeChatMode(
      window.localStorage.getItem(CHAT_MODE_STORAGE_KEY),
      null,
    );
  } catch (error) {
    console.warn(
      '[useAiChat] モード設定を読み込めませんでした。',
      error,
    );
    return null;
  }
};

const saveStoredChatMode = (mode) => {
  if (typeof window === 'undefined') return;

  try {
    window.localStorage.setItem(CHAT_MODE_STORAGE_KEY, mode);
  } catch (error) {
    console.warn(
      '[useAiChat] モード設定を保存できませんでした。',
      error,
    );
  }
};

const valueToText = (value) => {
  if (value === null || value === undefined) return '';

  if (typeof value === 'string') return value;

  if (
    typeof value === 'number'
    || typeof value === 'boolean'
  ) {
    return String(value);
  }

  if (isObject(value)) {
    const preferred = (
      value.message
      ?? value.text
      ?? value.response
      ?? value.content
    );

    if (
      preferred !== undefined
      && preferred !== value
    ) {
      return valueToText(preferred);
    }
  }

  try {
    return JSON.stringify(value);
  } catch (_error) {
    return String(value);
  }
};

const getMessageContent = (message) => {
  if (!message) return '';

  if (message.content !== undefined) {
    return valueToText(message.content);
  }

  if (message.text !== undefined) {
    return valueToText(message.text);
  }

  if (message.message !== undefined) {
    return valueToText(message.message);
  }

  return '';
};

const formatHistoryForApi = (
  currentMessages,
  lastUserText,
) => {
  const nextHistory = [
    ...currentMessages,
    {
      role: 'user',
      content: lastUserText,
    },
  ];

  return nextHistory
    .filter((message) => message?.role)
    .map((message) => ({
      role: message.role,
      content: getMessageContent(message),
    }));
};

const unwrapJsonResponse = (data) => {
  if (!isObject(data)) {
    return {
      outer: {},
      content: data,
      payload: {},
    };
  }

  const nestedContent = data.content;

  const nestedPayload = isObject(nestedContent)
    ? nestedContent
    : {};

  return {
    outer: data,
    content: nestedContent,
    payload: {
      ...data,
      ...nestedPayload,
    },
  };
};

const extractBackendStatus = (
  data,
  requestedMode,
) => {
  const {
    outer,
    payload,
  } = unwrapJsonResponse(data);

  const confirmedMode = normalizeChatMode(
    payload.chat_mode
      ?? payload.mode
      ?? outer.chat_mode
      ?? outer.mode,
    null,
  );

  const effectiveMode = (
    confirmedMode
    ?? requestedMode
  );

  const explicitAiEnabled = (
    payload.ai_enabled
    ?? outer.ai_enabled
  );

  const explicitChatbotEnabled = (
    payload.chatbot_enabled
    ?? outer.chatbot_enabled
  );

  return {
    requestedMode,
    mode: effectiveMode,

    aiEnabled:
      typeof explicitAiEnabled === 'boolean'
        ? explicitAiEnabled
        : effectiveMode === CHAT_MODES.AI,

    chatbotEnabled:
      typeof explicitChatbotEnabled === 'boolean'
        ? explicitChatbotEnabled
        : effectiveMode === CHAT_MODES.CHATBOT,

    source:
      payload.source
      ?? outer.source
      ?? 'unknown',

    llmAvailable:
      typeof payload.llm_available === 'boolean'
        ? payload.llm_available
        : null,

    confirmed: confirmedMode !== null,
    updatedAt: new Date().toISOString(),
  };
};

const extractStreamText = (parsed) => {
  if (!isObject(parsed)) return '';

  return valueToText(
    parsed.message?.content
      ?? parsed.delta?.content
      ?? parsed.token
      ?? parsed.response
      ?? parsed.text
      ?? (
        typeof parsed.content === 'string'
          ? parsed.content
          : ''
      ),
  );
};

const buildApiError = async (response) => {
  let responseBody = '';

  try {
    responseBody = (
      await response.text()
    ).trim();
  } catch (_error) {
    responseBody = '';
  }

  let details = responseBody;

  if (responseBody) {
    try {
      const parsed = JSON.parse(responseBody);

      details = valueToText(
        parsed.detail
          ?? parsed.message
          ?? parsed.error
          ?? responseBody,
      );
    } catch (_error) {
      // FastAPI以外のプレーンテキスト応答は
      // そのまま表示する。
    }
  }

  const error = new Error(
    response.status === 404
      ? '404_NOT_FOUND'
      : `HTTP_${response.status}`,
  );

  error.status = response.status;
  error.statusText = response.statusText;
  error.details = details;

  return error;
};

export function useAiChat({
  onImportDB,
  initialChatMode = DEFAULT_CHAT_MODE,
} = {}) {
  const firstMode = normalizeChatMode(
    readStoredChatMode(),
    normalizeChatMode(
      initialChatMode,
      DEFAULT_CHAT_MODE,
    ),
  );

  const [messages, setMessages] = useState([
    {
      id: Date.now(),
      role: 'assistant',
      type: 'text',
      source: 'system',
      content:
        '<summary>アプリ開発AIとしてスタンバイしました！</summary>'
        + '<details>AIモードを標準にして、'
        + 'チャットボットモードへも切り替えられます。</details>',
    },
  ]);

  const [isLoading, setIsLoading] = useState(false);
  const [isRagMode, setIsRagMode] = useState(false);
  const [forceJsonMode, setForceJsonMode] = useState(false);

  const [
    chatMode,
    setChatModeState,
  ] = useState(firstMode);

  const [
    backendStatus,
    setBackendStatus,
  ] = useState({
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

  const addSystemMessage = useCallback(
    (text) => {
      setMessages((previous) => [
        ...previous,
        {
          id: nextMessageId(),
          role: 'system',
          type: 'text',
          source: 'system',
          content: String(text),
          text: String(text),
        },
      ]);
    },
    [nextMessageId],
  );

  const setChatMode = useCallback((nextMode) => {
    const normalized = normalizeChatMode(
      nextMode,
      DEFAULT_CHAT_MODE,
    );

    setChatModeState(normalized);
    saveStoredChatMode(normalized);

    setBackendStatus((previous) => ({
      ...previous,
      requestedMode: normalized,
      mode: normalized,
      aiEnabled: normalized === CHAT_MODES.AI,
      chatbotEnabled:
        normalized === CHAT_MODES.CHATBOT,
      confirmed: false,
      updatedAt: new Date().toISOString(),
    }));
  }, []);

  const toggleChatMode = useCallback(() => {
    setChatMode(
      chatMode === CHAT_MODES.AI
        ? CHAT_MODES.CHATBOT
        : CHAT_MODES.AI,
    );
  }, [
    chatMode,
    setChatMode,
  ]);

  const syncBackendStatus = useCallback(
    (data, requestedMode) => {
      const status = extractBackendStatus(
        data,
        requestedMode,
      );

      setBackendStatus(status);

      if (status.confirmed) {
        setChatModeState(status.mode);
        saveStoredChatMode(status.mode);
      }

      return status;
    },
    [],
  );

  const loadHistory = useCallback(
    (historyName) => {
      addSystemMessage(
        `【システム】履歴「${historyName}」を読み込みました。`,
      );

      if (onImportDB) {
        onImportDB(historyName);
      }
    },
    [
      addSystemMessage,
      onImportDB,
    ],
  );

  const cancelRequest = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  const addJsonResponseMessage = useCallback(
    (data, requestedMode) => {
      const {
        outer,
        content,
        payload,
      } = unwrapJsonResponse(data);

      const status = syncBackendStatus(
        data,
        requestedMode,
      );

      const responseType = (
        outer.response_type
        ?? payload.response_type
        ?? outer.type
        ?? payload.type
        ?? 'text'
      );

      const blocks = Array.isArray(payload.blocks)
        ? payload.blocks
        : (
          Array.isArray(outer.blocks)
            ? outer.blocks
            : []
        );

      if (responseType === 'multi_select') {
       setMessages((previous) => [
        ...previous,
        {
          // 1. まず API から来た payload の中身を丸ごと展開（これによって data や metadata が引き継がれます）
          ...payload,
          
          // 2. その上で、UI 制御に必要な基本プロパティを上書き設定
          id: nextMessageId(),
          role: 'assistant',
          
          // type は payload.type があればそれを優先、なければ 'text'
          type: payload.type || 'text', 
          
          response_type: responseType,
          source: status.source,
          chat_mode: status.mode,
          ai_enabled: status.aiEnabled,
          content: textMessage,
          text: textMessage,
        },
      ]);

        return;
      }

      const hasBlocks = blocks.length > 0;

      const hasUiCode = (
        responseType === 'ui_code'
        || hasBlocks
      );

      const textMessage = valueToText(
        payload.message
          ?? outer.message
          ?? outer.response
          ?? payload.response
          ?? (
            typeof content === 'string'
              ? content
              : ''
          ),
      ) || (
        hasUiCode
          ? '生成結果を受信しました。'
          : '応答を受信しました。'
      );

      if (hasUiCode) {
        const uiContent = {
          message: textMessage,
          blocks,
          response_type: responseType,
        };

        setMessages((previous) => [
          ...previous,
          {
            id: nextMessageId(),
            role: 'assistant',

            // 既存UIのブロック描画分岐との
            // 互換性は維持する。
            type: 'ui_code',

            // project_buildなどの
            // 実際の応答種別は失わない。
            response_type: responseType,

            source:
              status.source
              || responseType,

            chat_mode: status.mode,
            ai_enabled: status.aiEnabled,
            content: uiContent,
            text: uiContent,
            blocks,
          },
        ]);

        return;
      }

      setMessages((previous) => [
        ...previous,
        {
          id: nextMessageId(),
          role: 'assistant',
          type: 'text',
          response_type: responseType,
          source: status.source,
          chat_mode: status.mode,
          ai_enabled: status.aiEnabled,
          content: textMessage,
          text: textMessage,
        },
      ]);
    },
    [
      nextMessageId,
      syncBackendStatus,
    ],
  );

  const consumeStreamingResponse = useCallback(
    async (
      response,
      requestedMode,
    ) => {
      if (!response.body) {
        throw new Error('STREAM_BODY_NOT_FOUND');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      const assistantMessageId = nextMessageId();

      let buffer = '';
      let fullText = '';

      setMessages((previous) => [
        ...previous,
        {
          id: assistantMessageId,
          role: 'assistant',
          type: 'text',
          response_type: 'text',
          source: 'stream',
          chat_mode: requestedMode,
          ai_enabled:
            requestedMode === CHAT_MODES.AI,
          content: '',
          text: '',
        },
      ]);

      const appendText = (text) => {
        if (!text) return;

        fullText += text;

        setMessages((previous) => (
          previous.map((message) => (
            message.id === assistantMessageId
              ? {
                ...message,
                content: fullText,
                text: fullText,
              }
              : message
          ))
        ));
      };

      const consumeLine = (rawLine) => {
        const trimmed = rawLine.trim();

        if (
          !trimmed
          || trimmed === '[DONE]'
        ) {
          return;
        }

        const candidate = trimmed.startsWith('data:')
          ? trimmed.slice(5).trim()
          : trimmed;

        if (
          !candidate
          || candidate === '[DONE]'
        ) {
          return;
        }

        try {
          const parsed = JSON.parse(candidate);

          const streamStatus = extractBackendStatus(
            parsed,
            requestedMode,
          );

          if (
            streamStatus.confirmed
            || streamStatus.source !== 'unknown'
          ) {
            setBackendStatus(streamStatus);

            if (streamStatus.confirmed) {
              setChatModeState(streamStatus.mode);
              saveStoredChatMode(streamStatus.mode);
            }
          }

          appendText(
            extractStreamText(parsed),
          );
        } catch (_error) {
          appendText(candidate);
        }
      };

      while (true) {
        const {
          done,
          value,
        } = await reader.read();

        if (done) break;

        buffer += decoder.decode(
          value,
          { stream: true },
        );

        const lines = buffer.split(/\r?\n/);

        buffer = lines.pop() ?? '';

        lines.forEach(consumeLine);
      }

      buffer += decoder.decode();

      if (buffer.trim()) {
        consumeLine(buffer);
      }

      if (!fullText) {
        appendText(
          'ストリーミング応答は完了しましたが、'
          + '表示できる本文がありませんでした。',
        );
      }
    },
    [nextMessageId],
  );

  const postChatRequest = useCallback(
    async (apiPayload) => {
      const controller = new AbortController();

      abortControllerRef.current = controller;

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(apiPayload),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw await buildApiError(response);
      }

      return response;
    },
    [],
  );

  const handleRequestError = useCallback(
    (error, requestLabel) => {
      console.error(
        `[useAiChat] ${requestLabel}エラー:`,
        error,
      );

      if (error?.name === 'AbortError') {
        addSystemMessage(
          `${requestLabel}をキャンセルしました。`,
        );
        return;
      }

      if (error?.message === '404_NOT_FOUND') {
        addSystemMessage(
          'AIサーバー（Backend）が見つかりません。'
          + 'Python側の起動状態と'
          + ' /api/chat を確認してください。',
        );
        return;
      }

      if (
        error instanceof TypeError
        && /failed to fetch|networkerror|load failed/i
          .test(error.message)
      ) {
        addSystemMessage(
          'AIサーバーへ接続できません。'
          + 'Backendが起動しているか、'
          + 'ポート8765を確認してください。',
        );
        return;
      }

      if (Number(error?.status) >= 500) {
        const details = error?.details
          ? `\nBackend詳細: ${error.details}`
          : '';

        addSystemMessage(
          `${requestLabel}中にBackend内部エラー`
          + `（HTTP ${error.status}）が発生しました。`
          + details,
        );

        return;
      }

      if (
        error?.message
        === 'STREAM_BODY_NOT_FOUND'
      ) {
        addSystemMessage(
          'ストリーミング本文を取得できませんでした。',
        );
        return;
      }

      const details = error?.details
        ? `\n詳細: ${error.details}`
        : '';

      addSystemMessage(
        `${requestLabel}で通信エラーが発生しました。`
        + 'Backendの状態を確認してください。'
        + details,
      );
    },
    [addSystemMessage],
  );

  const sendMessage = useCallback(
    async (rawInput) => {
      const input = typeof rawInput === 'string'
        ? rawInput
        : valueToText(rawInput);

      if (
        !input.trim()
        || requestInFlightRef.current
      ) {
        return;
      }

      const requestedMode = chatMode;

      const {
        correctedText,
        wasCorrected,
        detectedTargets = [],
      } = correctTypo(input);

      const safeCorrectedText = valueToText(
        correctedText || input,
      );

      const apiHistory = formatHistoryForApi(
        messages,
        safeCorrectedText,
      );

      const commandPayload = buildCommandPayload(
        safeCorrectedText,
      );

      setMessages((previous) => {
        const updated = [
          ...previous,
          {
            id: nextMessageId(),
            role: 'user',
            type: 'text',
            content: input,
            text: input,
            chat_mode: requestedMode,
          },
        ];

        if (wasCorrected) {
          updated.push({
            id: nextMessageId(),
            role: 'system',
            type: 'text',
            source: 'typo_corrector',

            content:
              detectedTargets.length > 0
                ? `💡「${detectedTargets.join('、')}」として補正して処理します。`
                : `💡「${safeCorrectedText}」として補正して処理します。`,
          });
        }

        return updated;
      });

      const apiPayload = {
        ...(
          isObject(commandPayload)
            ? commandPayload
            : {}
        ),

        message: safeCorrectedText,
        force_json_ui: forceJsonMode,
        history: apiHistory,

        // RAGの処理モード。
        // AI/チャットボットとは別の軸。
        mode: isRagMode
          ? 'rag_chat'
          : undefined,

        // BackendのChatHandlerが使用する
        // 会話エンジンモード。
        chat_mode: requestedMode,

        ai_mode:
          requestedMode === CHAT_MODES.AI,
      };

      requestInFlightRef.current = true;
      setIsLoading(true);

      setBackendStatus((previous) => ({
        ...previous,
        requestedMode,
        confirmed: false,
      }));

      try {
        console.log(
          '[useAiChat] API送信:',
          apiPayload,
        );

        const response = await postChatRequest(
          apiPayload,
        );

        const contentType = (
          response.headers.get('content-type')
          || ''
        );

        if (
          contentType.includes('application/json')
        ) {
          const data = await response.json();

          console.log(
            '[useAiChat] Backend応答:',
            data,
          );

          addJsonResponseMessage(
            data,
            requestedMode,
          );
        } else {
          await consumeStreamingResponse(
            response,
            requestedMode,
          );
        }
      } catch (error) {
        handleRequestError(
          error,
          'メッセージ送信',
        );
      } finally {
        requestInFlightRef.current = false;
        abortControllerRef.current = null;
        setIsLoading(false);
      }
    },
    [
      addJsonResponseMessage,
      chatMode,
      consumeStreamingResponse,
      forceJsonMode,
      handleRequestError,
      isRagMode,
      messages,
      nextMessageId,
      postChatRequest,
    ],
  );

  const sendImage = useCallback(
    async (file) => {
      if (
        !file
        || requestInFlightRef.current
      ) {
        return;
      }

      const requestedMode = chatMode;

      requestInFlightRef.current = true;
      setIsLoading(true);

      setMessages((previous) => [
        ...previous,
        {
          id: nextMessageId(),
          role: 'user',
          type: 'text',
          content:
            `📸 画像データを送信しました: ${file.name}`,
          text:
            `📸 画像データを送信しました: ${file.name}`,
          chat_mode: requestedMode,
        },
      ]);

      try {
        const base64Image = await new Promise(
          (resolve, reject) => {
            const reader = new FileReader();

            reader.onload = () => {
              resolve(reader.result);
            };

            reader.onerror = reject;
            reader.readAsDataURL(file);
          },
        );

        const apiPayload = {
          message: '【画像解析リクエスト】',
          image_base64: base64Image,
          force_json_ui: forceJsonMode,

          history: formatHistoryForApi(
            messages,
            '【画像送信】',
          ),

          mode: isRagMode
            ? 'rag_chat'
            : undefined,

          chat_mode: requestedMode,

          ai_mode:
            requestedMode === CHAT_MODES.AI,
        };

        const response = await postChatRequest(
          apiPayload,
        );

        const contentType = (
          response.headers.get('content-type')
          || ''
        );

        if (
          contentType.includes('application/json')
        ) {
          const data = await response.json();

          addJsonResponseMessage(
            data,
            requestedMode,
          );
        } else {
          await consumeStreamingResponse(
            response,
            requestedMode,
          );
        }
      } catch (error) {
        handleRequestError(
          error,
          '画像解析',
        );
      } finally {
        requestInFlightRef.current = false;
        abortControllerRef.current = null;
        setIsLoading(false);
      }
    },
    [
      addJsonResponseMessage,
      chatMode,
      consumeStreamingResponse,
      forceJsonMode,
      handleRequestError,
      isRagMode,
      messages,
      nextMessageId,
      postChatRequest,
    ],
  );

  const modeLabel = useMemo(
    () => (
      chatMode === CHAT_MODES.AI
        ? 'AI'
        : 'チャットボット'
    ),
    [chatMode],
  );

  return {
    messages,
    isLoading,

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

    isAiMode:
      chatMode === CHAT_MODES.AI,

    isChatbotMode:
      chatMode === CHAT_MODES.CHATBOT,

    backendStatus,
    backendMode: backendStatus.mode,
    backendSource: backendStatus.source,

    isBackendModeConfirmed:
      backendStatus.confirmed,
  };
}
