// frontend/src/components/chat_blocks/blockTypeGuards.ts
// 型Check
export interface UiBlock {
  type: string;
  title?: string;
  code?: string;
  html?: string;
  css?: string;
  props?: {
    title?: string;
    data?: unknown;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface NormalizedMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  sender: string;
  responseType: string;
  text: string;
  blocks: UiBlock[];
  rawData: Record<string, unknown> | null;
}

// 1. 任意の値がプレーンオブジェクトか判定する基本型ガード
export function isRecord(val: unknown): val is Record<string, unknown> {
  return typeof val === 'object' && val !== null && !Array.isArray(val);
}

// 2. ブロック要素（JsonViewerBlock / ui_code 等）かどうかの型ガード
export function isUiBlock(val: unknown): val is UiBlock {
  return isRecord(val) && (typeof val.type === 'string' || typeof val.code === 'string');
}

// 3. Handler / tools のバラバラな応答形式を1つの安全な型に正規化する関数
export function normalizeChatMessage(msg: unknown, index: number): NormalizedMessage {
  if (!isRecord(msg)) {
    return {
      id: `msg-${index}`,
      role: 'assistant',
      sender: 'AI ENGINEER',
      responseType: 'text',
      text: typeof msg === 'string' ? msg : JSON.stringify(msg ?? ''),
      blocks: [],
      rawData: null,
    };
  }

  const content = msg.content;
  let text = '';
  let rawBlocks: unknown[] = [];

  if (typeof content === 'string') {
    text = content;
  } else if (isRecord(content)) {
    text =
      typeof content.message === 'string'
        ? content.message
        : typeof content.text === 'string'
        ? content.text
        : '';
    if (Array.isArray(content.blocks)) {
      rawBlocks = content.blocks;
    }
  } else if (typeof msg.text === 'string') {
    text = msg.text;
  }

  // msg直下に blocks がある場合のフォールバック（AiChatPanel.tsx の ChatMessageLike 互換）
  if (rawBlocks.length === 0 && Array.isArray(msg.blocks)) {
    rawBlocks = msg.blocks;
  }

  return {
    id: typeof msg.id === 'string' || typeof msg.id === 'number' ? String(msg.id) : `msg-${index}`,
    role: msg.role === 'user' || msg.sender === 'user' ? 'user' : 'assistant',
    sender: typeof msg.sender === 'string' ? msg.sender : 'AI ENGINEER',
    responseType: typeof msg.response_type === 'string' ? msg.response_type : String(msg.type || 'text'),
    text,
    blocks: rawBlocks.filter(isUiBlock),
    rawData: isRecord(content) ? content : isRecord(msg.data) ? msg.data : null,
  };
}