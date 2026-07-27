import React from 'react';
import { Link } from 'react-router-dom';
import { Page } from '../../types';

interface PageListItemProps {
  page: Page;
  onDelete: (page: Page) => void;
}

export default function PageListItem({ page, onDelete }: PageListItemProps) {
  const isPublished = page.status === 'published';

  return (
    <div className="flex items-center justify-between p-4 hover:bg-blue-50 transition-colors">
      <div>
        <p className="font-bold text-gray-800 text-sm">{page.title}</p>
        <p className="text-xs text-gray-400 font-mono">/{page.slug}</p>
      </div>
      <div className="flex items-center gap-4">
        <span className={`text-[10px] font-bold px-2 py-1 rounded-full uppercase ${
          isPublished ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
        }`}>
          {page.status}
        </span>
        <Link
          to={`/builder/${page.id}`}
          className="text-sm font-bold text-blue-600 hover:text-blue-800"
        >
          編集
        </Link>
        <button
          onClick={() => onDelete(page)}
          className="text-red-400 hover:text-red-600 text-base"
          title="削除"
        >
          🗑️
        </button>
      </div>
    </div>
  );
}