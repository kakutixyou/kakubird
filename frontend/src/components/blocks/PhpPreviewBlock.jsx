import React from "react";

export default function PhpPreviewBlock({ block }) {
  const {
    title,
    description,
    code,
    language = "php",
  } = block.props || {};

  if (!code) return null;

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-5 max-w-4xl mx-auto my-2">
      <h3 className="font-bold text-slate-200">
        {title || "PHP Code Preview"}
      </h3>

      {description && (
        <p className="text-xs text-slate-400 mb-3">
          {description}
        </p>
      )}

      <pre className="bg-slate-950 p-4 rounded-lg font-mono text-sm text-amber-400 overflow-x-auto">
        <code>{code}</code>
      </pre>

      <button
        onClick={() => alert("サーバーで実行します")}
        className="mt-3 px-4 py-2 bg-amber-500 text-slate-900 rounded-lg text-xs font-bold"
      >
        PHPを実行 🚀
      </button>
    </div>
  );
}