// frontend/src/components/chat_blocks/UiCodePreviewBlock.tsx
import React from 'react';

export interface UiCodePreviewBlockProps {
  block: any;
  onOpenManualEdit?: (block: unknown) => void;
  onInsertCode?: (code: string) => void;
}

export function UiCodePreviewBlock({
  block,
  onOpenManualEdit,
  onInsertCode,
}: UiCodePreviewBlockProps): React.ReactElement {
  const code =
    block?.code ||
    block?.html ||
    block?.content ||
    JSON.stringify(block, null, 2);

  return (
    <div className="my-2 rounded-xl border border-cyan-500/40 bg-slate-950 text-slate-100 overflow-hidden">
      <div className="px-3.5 py-2 bg-slate-900 border-b border-slate-800 flex items-center justify-between text-xs">
        <span className="font-bold text-cyan-300">💻 生成コード / UIブロック</span>
        <div className="flex items-center gap-2">
          {onOpenManualEdit && (
            <button
              type="button"
              onClick={() => onOpenManualEdit(block)}
              className="px-2 py-0.5 rounded bg-cyan-600/30 border border-cyan-500/50 text-cyan-200 hover:bg-cyan-600/50 text-[11px] font-semibold"
            >
              ✏️ 自分で編集
            </button>
          )}
          {onInsertCode && (
            <button
              type="button"
              onClick={() => onInsertCode(String(code))}
              className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px]"
            >
              📥 エディタへ挿入
            </button>
          )}
        </div>
      </div>
      <pre className="p-3 text-[11px] font-mono text-slate-200 overflow-x-auto max-h-60">
        {String(code)}
      </pre>
    </div>
  );
}

export default UiCodePreviewBlock;
