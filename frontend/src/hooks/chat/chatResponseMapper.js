// frontend/src/hooks/chat/chatResponseMapper.js　画面崩れ担当
import { isObject, unwrapJsonResponse, valueToText } from './chatUtils';

export const CUSTOM_WIDGET_TYPES = new Set([
  'malware_defense',
  'video_curator',
  'to_model_studio',
  'experience_memo',
  'github_search',
  'vscode',
  'math',
  'image',
  'link_navigator',
  'sixyumiration',
]);

/**
 * BackendからのJSON応答を、チャット一覧で描画するメッセージオブジェクトへ変換する。
 */
export function buildAssistantMessageFromJson(data, status, id) {
  const { outer, content, payload } = unwrapJsonResponse(data);

  const responseType = (
    outer.response_type ?? payload.response_type ?? outer.type ?? payload.type ?? 'text'
  );
  const blocks = Array.isArray(payload.blocks)
    ? payload.blocks
    : (Array.isArray(outer.blocks) ? outer.blocks : []);
  const hasBlocks = blocks.length > 0;
  const hasUiCode = responseType === 'ui_code' || hasBlocks;

  const elevator = isObject(payload.elevator)
    ? payload.elevator
    : (isObject(outer.elevator) ? outer.elevator : null);

  const textMessage = valueToText(
    payload.message
      ?? outer.message
      ?? outer.response
      ?? payload.response
      ?? (typeof content === 'string' ? content : ''),
  ) || (hasUiCode ? '生成結果を受信しました。' : '応答を受信しました。');

  const base = {
    id,
    role: 'assistant',
    response_type: responseType,
    source: status.source,
    chat_mode: status.mode,
    ai_enabled: status.aiEnabled,
    ...(elevator ? { elevator } : {}),
  };

  if (responseType === 'multi_select') {
    return {
      elevator,
      message: { ...payload, ...base, type: 'multi_select', content: textMessage, text: textMessage },
    };
  }

  if (!hasBlocks && CUSTOM_WIDGET_TYPES.has(responseType)) {
    const widgetData = isObject(payload.data) ? payload.data : payload;
    return {
      elevator,
      message: {
        ...payload,
        ...base,
        type: responseType,
        message: textMessage,
        content: isObject(content) ? content : widgetData,
        data: widgetData,
      },
    };
  }

  if (hasUiCode) {
    const uiContent = {
      message: textMessage,
      blocks,
      response_type: responseType,
      ...(elevator ? { elevator } : {}),
    };
    return {
      elevator,
      message: {
        ...base,
        type: 'ui_code',
        source: status.source || responseType,
        content: uiContent,
        text: uiContent,
        blocks,
      },
    };
  }

  return {
    elevator,
    message: { ...base, type: 'text', content: textMessage, text: textMessage },
  };
}