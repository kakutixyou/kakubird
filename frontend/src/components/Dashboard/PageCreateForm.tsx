import React from 'react';

interface PageCreateFormProps {
  title: string;
  onChange: (val: string) => void;
  onCreate: () => void;
}

export default function PageCreateForm({ title, onChange, onCreate }: PageCreateFormProps) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
      <h3 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
        <span>📄</span> 新しいページを作成
      </h3>
      <div className="flex gap-3">
        <input
          type="text"
          value={title}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onCreate()}
          placeholder="ページタイトルを入力..."
          className="flex-1 border border-gray-200 rounded-xl px-4 py-2 outline-none focus:ring-2 focus:ring-blue-500/20 text-sm"
        />
        <button
          onClick={onCreate}
          className="bg-blue-600 text-white px-6 py-2 rounded-xl font-bold hover:bg-blue-700 transition-all text-sm"
        >
          作成
        </button>
      </div>
    </div>
  );
}