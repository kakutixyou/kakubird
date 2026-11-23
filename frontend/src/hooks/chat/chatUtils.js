// React に依存しない処理をすべてここへ追い出します。通信エラー担当
// frontend/src/hooks/chat/chatUtils.js
export const CHAT_MODES = Object.freeze({
  AI: 'ai',
  CHATBOT: 'chatbot',
  LINK_NAVIGATOR: 'link_navigator',
});

export const DEFAULT_CHAT_MODE = CHAT_MODES.AI;
const CHAT_MODE_STORAGE_KEY = 'ai_chat_mode';

export const isObject = (value) => (
  value !== null && typeof value === 'object' && !Array.isArray(value)
);

export const normalizeChatMode = (value, fallback = null) => (
  value === CHAT_MODES.AI || value === CHAT_MODES.CHATBOT ? value : fallback
);

export const readStoredChatMode = () => {
  if (typeof window === 'undefined') return null;
  try {
    return normalizeChatMode(window.localStorage.getItem(CHAT_MODE_STORAGE_KEY), null);
  } catch (error) {
    console.warn('[useAiChat] モード設定を読み込めませんでした。', error);
    return null;
  }
};

export const saveStoredChatMode = (mode) => {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(CHAT_MODE_STORAGE_KEY, mode);
  } catch (error) {
    console.warn('[useAiChat] モード設定を保存できませんでした。', error);
  }
};

export const valueToText = (value) => {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);

  if (isObject(value)) {
    const preferred = value.message ?? value.text ?? value.response ?? value.content;
    if (preferred !== undefined && preferred !== value) {
      return valueToText(preferred);
    }
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
};

export const formatHistoryForApi = (currentMessages, lastUserText) => {
  const nextHistory = [...currentMessages, { role: 'user', content: lastUserText }];
  return nextHistory
    .filter((m) => m?.role)
    .map((m) => ({
      role: m.role,
      content: valueToText(m.content ?? m.text ?? m.message ?? ''),
    }));
};

export const unwrapJsonResponse = (data) => {
  if (!isObject(data)) return { outer: {}, content: data, payload: {} };
  const nestedContent = data.content;
  const nestedPayload = isObject(nestedContent) ? nestedContent : {};
  return {
    outer: data,
    content: nestedContent,
    payload: { ...data, ...nestedPayload },
  };
};

export const extractBackendStatus = (data, requestedMode) => {
  const { outer, payload } = unwrapJsonResponse(data);
  const confirmedMode = normalizeChatMode(
    payload.chat_mode ?? payload.mode ?? outer.chat_mode ?? outer.mode,
    null,
  );
  const effectiveMode = confirmedMode ?? requestedMode;
  const explicitAi = payload.ai_enabled ?? outer.ai_enabled;
  const explicitBot = payload.chatbot_enabled ?? outer.chatbot_enabled;

  return {
    requestedMode,
    mode: effectiveMode,
    aiEnabled: typeof explicitAi === 'boolean' ? explicitAi : effectiveMode === CHAT_MODES.AI,
    chatbotEnabled: typeof explicitBot === 'boolean' ? explicitBot : effectiveMode === CHAT_MODES.CHATBOT,
    source: payload.source ?? outer.source ?? 'unknown',
    llmAvailable: typeof payload.llm_available === 'boolean' ? payload.llm_available : null,
    confirmed: confirmedMode !== null,
    updatedAt: new Date().toISOString(),
  };
};

export const extractStreamText = (parsed) => {
  if (!isObject(parsed)) return '';
  return valueToText(
    parsed.message?.content
      ?? parsed.delta?.content
      ?? parsed.token
      ?? parsed.response
      ?? parsed.text
      ?? (typeof parsed.content === 'string' ? parsed.content : ''),
  );
};

export const buildApiError = async (response) => {
  let responseBody = '';
  try {
    responseBody = (await response.text()).trim();
  } catch {
    responseBody = '';
  }

  let details = responseBody;
  if (responseBody) {
    try {
      const parsed = JSON.parse(responseBody);
      details = valueToText(parsed.detail ?? parsed.message ?? parsed.error ?? responseBody);
    } catch {
      // プレーンテキストはそのまま利用
    }
  }

  const error = new Error(response.status === 404 ? '404_NOT_FOUND' : `HTTP_${response.status}`);
  error.status = response.status;
  error.statusText = response.statusText;
  error.details = details;
  return error;
};

export const formatErrorMessage = (error, requestLabel) => {
  if (error?.name === 'AbortError') return `${requestLabel}をキャンセルしました。`;
  if (error?.message === '404_NOT_FOUND') {
    return 'AIサーバー（Backend）が見つかりません。Python側の起動状態と /api/chat を確認してください。';
  }
  if (error instanceof TypeError && /failed to fetch|networkerror|load failed/i.test(error.message)) {
    return 'AIサーバーへ接続できません。Backendが起動しているか、ポート8765を確認してください。';
  }
  if (Number(error?.status) >= 500) {
    const details = error?.details ? `\nBackend詳細: ${error.details}` : '';
    return `${requestLabel}中にBackend内部エラー（HTTP ${error.status}）が発生しました。${details}`;
  }
  if (error?.message === 'STREAM_BODY_NOT_FOUND') {
    return 'ストリーミング本文を取得できませんでした。';
  }
  const details = error?.details ? `\n詳細: ${error.details}` : '';
  return `${requestLabel}で通信エラーが発生しました。Backendの状態を確認してください。${details}`;
};

export const readFileAsDataUrl = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = () => resolve(reader.result);
  reader.onerror = reject;
  reader.readAsDataURL(file);
});