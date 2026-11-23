// frontend/src/components/chat_blocks/ToolAndHandlerBlock.tsx
import React, { useState } from 'react';

export interface ToolAndHandlerBlockProps {
  block: any;
  toolCategory?: string;
  handlerName?: string;
}

// tools/ 配下の18カテゴリに対応するアイコン定義
const TOOL_ICONS: Record<string, string> = {
  registry: '🗂️',
  math: '📐',
  search: '🔍',
  weather: '⛅',
  finance: '📈',
  github: '🐙',
  filesystem: '📂',
  code: '💻',
  php: '🐘',
  html: '🌐',
  database: '🗄️',
  deployment: '🚀',
  git: '🌿',
  image: '🖼️',
  video: '🎬',
  blender: '🧊',
  unity: '🎮',
  system: '⚙️',
};

export function ToolAndHandlerBlock({
  block,
  toolCategory = 'system',
  handlerName,
}: ToolAndHandlerBlockProps): React.ReactElement {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);
  const icon = TOOL_ICONS[toolCategory.toLowerCase()] || '🛠️';
  const title =
    block?.props?.title ||
    block?.title ||
    handlerName ||
    `Tool Execution (${toolCategory})`;
  const payload = block?.props?.data ?? block?.data ?? block?.result ?? block;

  return (
    <div className="my-2 rounded-xl border border-indigo-500/30 bg-slate-950 text-slate-100 overflow-hidden shadow">
      <button
        type="button"
        onClick={() => setIsExpanded((prev) => !prev)}
        className="w-full px-3.5 py-2 bg-slate-900 hover:bg-slate-800/90 flex items-center justify-between text-xs font-bold text-indigo-300 transition"
      >
        <span className="flex items-center gap-2">
          <span>{icon}</span>
          <span>{title}</span>
        </span>
        <span className="text-[10px] text-slate-400">
          {isExpanded ? '▽ 折りたたむ' : '◁ 展開する'}
        </span>
      </button>

      {isExpanded && (
        <pre className="p-3 text-[11px] font-mono text-emerald-300 overflow-x-auto max-h-64">
          {typeof payload === 'string'
            ? payload
            : JSON.stringify(payload, null, 2)}
        </pre>
      )}
    </div>
  );
}

export default ToolAndHandlerBlock;
