// frontend/src/components/blocks/FileDownloadBlock.jsx

import React from 'react';

export default function FileDownloadBlock({ block }) {
  const files = block?.props?.files || [];

  if (!files.length) return null;

  return (
    <div className="space-y-3">
      {files.map((file, idx) => (
        <div
          key={idx}
          className="border rounded-xl p-4 bg-white dark:bg-slate-900"
        >
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold">{file.name}</h3>

              <p className="text-sm text-slate-500">
                {file.description}
              </p>
            </div>

            <a
              href={file.url}
              download
              className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm"
            >
              Download
            </a>
          </div>
        </div>
      ))}
    </div>
  );
}