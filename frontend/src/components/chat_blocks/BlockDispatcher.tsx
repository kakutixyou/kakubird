// frontend/src/components/chat_blocks/BlockDispatcher.tsx
import React from 'react';
import MarkdownMessageBlock from './MarkdownMessageBlock';
import ToolAndHandlerBlock from './ToolAndHandlerBlock';
import UiCodePreviewBlock from './UiCodePreviewBlock';
import GameSimResultBlock from './GameSimResultBlock';
import LinkNavigatorBlock from './LinkNavigatorBlock';
import ElevatorNavigatorBlock from './ElevatorNavigatorBlock';
import type { ElevatorData } from './ElevatorNavigatorBlock';
export interface BlockDispatcherProps {
  msg: any;
  rawText: string;
  onOptionSelect?: (payload: unknown) => void;
  onOpenManualEdit?: (block: unknown) => void;
  onInsertCode?: (code: string) => void;
}

/**
 * 様々な Handler (OcrRecruitHandler, StockHandler, GameSimHandler, MathHandler等) や
 * tools/ フォルダー (math, search, sql, blender, unity, filesystem等) から返却された
 * メッセージ・blocks を自動判別して適切な専用コンポーネントへ振り分けるディスパッチャー
 */

export function BlockDispatcher({
  msg,
  rawText,
  onOptionSelect,
  onOpenManualEdit,
  onInsertCode,
}: BlockDispatcherProps): React.ReactElement {
  const blocks: any[] =
    msg?.content?.blocks ||
    msg?.blocks ||
    msg?.text?.blocks ||
    [];

  const msgType = String(msg?.type || msg?.response_type || '').toLowerCase();
  const toolCategory = String(
    msg?.tool_category || msg?.metadata?.tool || msg?.tool || '',
  );
  const handlerName = String(
    msg?.handler || msg?.metadata?.handler || msg?.metadata?.source || '',
  );
  const elevator: ElevatorData | null =
    msg?.elevator ||
    msg?.content?.elevator ||
    msg?.data?.elevator ||
    null;
  return (
    <div className="space-y-2.5">
      {/* 1. メインテキスト本文 */}
      {rawText && <MarkdownMessageBlock text={rawText} />}
      {msgType === 'link_navigator' && (
        <LinkNavigatorBlock data={msg?.data || msg?.content || msg} />
      )}
      {elevator && (
        <ElevatorNavigatorBlock elevator={elevator} onOptionSelect={onOptionSelect} />
      )}
      {/* 2. ゲームシミュレーション系ハンドラー出力 */}
      {(msgType === 'game_sim' || handlerName.toLowerCase().includes('game')) &&
        msg?.data && (
          <GameSimResultBlock data={msg.data} onOptionSelect={onOptionSelect} />
        )}

      {/* 3. UIコード生成モード (ui_code) */}
      {msgType === 'ui_code' && blocks.length === 0 && (
        <UiCodePreviewBlock
          block={msg?.content || msg}
          onOpenManualEdit={onOpenManualEdit}
          onInsertCode={onInsertCode}
        />
      )}

      {/* 4. blocks配列（JsonViewerBlock / コードブロック / 各種Handler・tools出力） */}
      {Array.isArray(blocks) &&
        blocks.map((b, i) => {
          const bType = String(b?.type || '').toLowerCase();
          if (bType.includes('code') || bType.includes('html') || b?.code) {
            return (
              <UiCodePreviewBlock
                key={`blk-${i}`}
                block={b}
                onOpenManualEdit={onOpenManualEdit}
                onInsertCode={onInsertCode}
              />
            );
          }
          if (bType.includes('game')) {
            return (
              <GameSimResultBlock
                key={`blk-${i}`}
                data={b?.props?.data || b}
                onOptionSelect={onOptionSelect}
              />
            );
          }
          return (
            <ToolAndHandlerBlock
              key={`blk-${i}`}
              block={b}
              toolCategory={toolCategory || b?.tool || 'system'}
              handlerName={handlerName || b?.handler}
            />
          );
        })}
    </div>
  );
}

export default BlockDispatcher;
