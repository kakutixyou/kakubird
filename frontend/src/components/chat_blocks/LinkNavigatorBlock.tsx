// frontend/src/components/chat_blocks/LinkNavigatorBlock.tsx
import React, { useState } from 'react';

export interface LinkNavigatorPayload {
  mode?: string;
  clean_url?: string;
  warning_note?: string;
  steps?: unknown[];
  qr_base64?: string;
  data?: LinkNavigatorPayload;
}

export interface LinkNavigatorBlockProps {
  title?: string;
  data?: LinkNavigatorPayload | Record<string, any>;
}

export function LinkNavigatorBlock({
  title,
  data,
}: LinkNavigatorBlockProps): React.ReactElement {
  const [copied, setCopied] = useState(false);

  // RenderBlocks 経由で data.data に包まれて渡された場合にも対応
  const raw = (data ?? {}) as LinkNavigatorPayload;
  const payload: LinkNavigatorPayload =
    raw.clean_url || raw.qr_base64 || raw.steps
      ? raw
      : (raw.data ?? raw);

  const cleanUrl = String(payload?.clean_url || '');
  const warningNote =
    typeof payload?.warning_note === 'string' ? payload.warning_note : '';
  const steps = Array.isArray(payload?.steps) ? payload.steps : [];
  const qrBase64 =
    typeof payload?.qr_base64 === 'string' ? payload.qr_base64 : '';
  const isToShare = payload?.mode === 'to_share';

  const handleCopy = async () => {
    if (!cleanUrl) return;
    try {
      await navigator.clipboard?.writeText(cleanUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // クリップボードAPIが使えない環境は無視
    }
  };

  return (
    <div className="my-2 rounded-xl border border-blue-500/40 bg-slate-950 p-3.5 text-slate-100 space-y-3 shadow-md">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <span className="text-xs font-extrabold text-blue-400 flex items-center gap-1.5">
          <span>{isToShare ? '🛡️' : '🧭'}</span>
          <span>
            {title ||
              (isToShare
                ? 'To Share 署名付き共有リンク'
                : 'アクセス手順ナビゲーター')}
          </span>
        </span>
        <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/20 text-blue-300">
          {isToShare ? 'Ed25519 Signed' : 'LinkNavigator'}
        </span>
      </div>

      {warningNote && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-2.5 text-xs text-amber-200">
          <span className="font-bold">💡 開く前のポイント：</span>
          <br />
          {warningNote}
        </div>
      )}

      {steps.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-[11px] font-bold text-slate-400">
            リンクを開いた後の進め方：
          </div>
          <ol className="list-decimal space-y-1 pl-4 text-xs text-slate-200">
            {steps.map((step, idx) => (
              <li key={idx} className="leading-relaxed">
                {String(step)}
              </li>
            ))}
          </ol>
        </div>
      )}

      {cleanUrl && (
        <div className="space-y-2 pt-1">
          <div className="rounded-lg border border-slate-800 bg-slate-900 px-2.5 py-1.5 text-[11px] font-mono text-slate-300 break-all">
            {cleanUrl}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <a
              href={cleanUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg bg-blue-600/80 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-500 transition"
            >
              PCでページを開く ↗
            </a>
            <button
              type="button"
              onClick={handleCopy}
              className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 transition"
            >
              {copied ? '✅ コピーしました' : '📋 URLをコピー'}
            </button>
          </div>
        </div>
      )}

      {qrBase64 && (
        <details
          open
          className="mt-2 rounded-lg border border-blue-500/40 bg-slate-900/50 p-2 text-xs"
        >
          <summary className="cursor-pointer font-semibold text-blue-300 hover:text-blue-200">
            📱 スマホ用QRコード（カメラで読み取り）
          </summary>
          <div className="mt-3 flex flex-col items-center gap-2 border-t border-slate-700 pt-3">
            <img
              src={qrBase64}
              alt="共有用QRコード"
              className="h-40 w-40 rounded-lg border border-slate-600 bg-white p-1.5"
            />
            <p className="text-center text-[10px] text-slate-400">
              ※外部通信なしでオフライン生成済み。スマホのカメラで読み取ってください。
            </p>
          </div>
        </details>
      )}
    </div>
  );
}

export default LinkNavigatorBlock;