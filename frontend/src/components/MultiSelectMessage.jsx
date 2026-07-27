import React, { useState } from 'react';

export default function MultiSelectMessage({ message, onSubmit }) {
  const [selected, setSelected] = useState([]);

  const toggleOption = (option) => {
    setSelected((prev) =>
      prev.includes(option)
        ? prev.filter((item) => item !== option)
        : [...prev, option]
    );
  };

  const handleSubmit = () => {
    if (selected.length === 0) return;
    onSubmit(selected);
  };

  return (
    <div className="max-w-[90%] bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-4 shadow-sm">
      <div className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-3">
        {message.question}
      </div>

      <div className="space-y-2">
        {message.options.map((option) => {
          const isSelected = selected.includes(option);

          return (
            <button
              key={option}
              type="button"
              onClick={() => toggleOption(option)}
              className={`w-full text-left px-3 py-2 rounded-lg border transition-colors ${
                isSelected
                  ? 'bg-indigo-50 border-indigo-500 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300'
                  : 'bg-slate-50 border-slate-200 text-slate-700 dark:bg-slate-900 dark:border-slate-700 dark:text-slate-300'
              }`}
            >
              {isSelected ? '☑ ' : '☐ '}
              {option}
            </button>
          );
        })}
      </div>

      <button
        type="button"
        onClick={handleSubmit}
        disabled={selected.length === 0}
        className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 dark:disabled:bg-slate-700 text-white rounded-lg transition-colors"
      >
        選択内容を送信
      </button>
    </div>
  );
}