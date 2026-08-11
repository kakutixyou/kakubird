// frontend/src/components/blocks/CodeFormatBlock.jsx
import React, { useState } from 'react';

export default function CodeFormatBlock({ language, code }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code || "");
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (e) {
      console.warn("コピーに失敗しました:", e);
    }
  };

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-950 overflow-hidden w-full">
      <div className="flex items-center justify-between px-3 py-2 bg-neutral-900 border-b border-neutral-800">
        <span className="text-xs text-neutral-400 font-mono">
          {language || "code"}
        </span>
        <button
          onClick={handleCopy}
          className="text-xs text-neutral-400 hover:text-neutral-200 transition-colors"
        >
          {copied ? "コピーしました ✓" : "コピー"}
        </button>
      </div>
      <pre className="p-3 overflow-x-auto text-sm">
        <code className="text-neutral-100 font-mono whitespace-pre">
          {code}
        </code>
      </pre>
    </div>
  );
}