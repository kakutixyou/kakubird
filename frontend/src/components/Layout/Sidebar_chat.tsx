// frontend/src/components/Layout/Sidebar_chat.tsx
import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import clsx from 'clsx';
import { useThemeStore } from "../../store/themeStore";
 import console from 'console';

// 元のコードから継承した美しいデータ構造
const NAV_ITEMS = [
  { path: '/', label: 'ダッシュボード', icon: '📊', exact: true },
  { path: '/templates', label: 'テンプレートを探す', icon: '🎨', sub: 'HTMLサンプル集' },
  { path: '/builder', label: 'HTMLビルダー', icon: '🏗', sub: '自由に編集する' },
  { path: '/databases', label: 'データベース', icon: '🗄️', sub: '生成済みDB管理' },
  { path: '/settings-api', label: 'API設定', icon: '🔌', sub: 'データ連携' },
  { path: '/memory', label: 'AIメモリー', icon: '🧠', sub: '会話履歴・メモ・タスク' }
];

export default function SidebarChatTheme() {
  const { currentTheme } = useThemeStore();
  console.log(
  "Current Theme:",
  currentTheme
  );
  // バックエンド連携までのダミーデータ
  const [chatHistory] = useState([
    { id: 1, title: '技術評論社のスクレイピング' },
    { id: 2, title: 'Ollamaのベクトル化テスト' },
    { id: 3, title: 'ReactのUIコンポーネント設計' },
  ]);

  return (
    <aside className="w-64 bg-gray-900 text-gray-100 flex flex-col h-screen flex-shrink-0 border-r border-gray-800">
      {/* 1. ロゴエリア (元のコードのまま) */}
      <div className="p-4 border-b border-gray-800 flex items-center gap-2">
        <span className="text-2xl">✨</span>
        <span className="font-bold text-lg">Project To</span>
      </div>

      {/* 2. New Chat ボタン (新規追加) */}
      <div className="p-4">
        <button className="flex items-center justify-center gap-2 w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded font-medium transition-colors">
          <span className="text-xl leading-none">+</span>
          <span>新しいチャット</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto flex flex-col">
        {/* 3. チャット履歴エリア (新規追加) */}
        <div className="px-2 mb-4">
          <div className="text-xs font-bold text-gray-500 px-2 mb-2 tracking-wider">最近のチャット</div>
          <div className="space-y-0.5">
            {chatHistory.map((chat) => (
              <button
                key={chat.id}
                className="w-full text-left px-3 py-2 rounded hover:bg-gray-800 text-sm truncate text-gray-300 hover:text-white transition-colors"
              >
                💬 {chat.title}
              </button>
            ))}
          </div>
        </div>

        {/* 4. メインメニューエリア (元のコードの進化版) */}
        <nav className="border-t border-gray-800 pt-4">
          <div className="text-xs font-bold text-gray-500 px-4 mb-2 tracking-wider">システムメニュー</div>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.exact}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-4 py-3 text-sm transition-colors',
                  isActive
                    ? 'bg-blue-600/10 text-blue-400 border-r-2 border-blue-500' // アクティブ時のデザインを少しモダンに
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                )
              }
            >
              <span className="text-lg w-6 text-center">{item.icon}</span>
              <div>
                <div className="font-medium">{item.label}</div>
                {item.sub && <div className="text-xs opacity-50 mt-0.5">{item.sub}</div>}
              </div>
            </NavLink>
          ))}
        </nav>
      </div>

      {/* 5. フッターエリア (元のコードのまま) */}
      <div className="p-4 border-t border-gray-800 text-xs text-gray-500 flex justify-between items-center">
        <span>Project To v1.0</span>
        {/* 将来的に設定やプロフィールアイコンを入れるスペース */}
        <span className="cursor-pointer hover:text-gray-300">⚙️</span>
      </div>
    </aside>
  );
}
