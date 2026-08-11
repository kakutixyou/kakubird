// frontend/src/components/Layout/sidebar_themes/Sidebar_default.tsx

import React, { useState } from "react";
import { NavLink } from "react-router-dom";
import clsx from "clsx";

const NAV_ITEMS = [
 
    { path: '/', label: 'ダッシュボード', icon: '📊', exact: true },
  { path: '/templates', label: 'テンプレートを探す', icon: '🎨', sub: 'HTMLサンプル集' },
  { path: '/builder', label: 'HTMLビルダー', icon: '🏗', sub: '自由に編集する' },
  { path: '/databases', label: 'データベース', icon: '🗄️', sub: '生成済みDB管理' },
  { path: '/settings-api', label: 'API設定', icon: '🔌', sub: 'データ連携' },
  { path: '/memory', label: 'AIメモリー', icon: '🧠', sub: '会話履歴・メモ・タスク' },
  // 👇 新規追加: 移住スコアリングアプリへのリンク
  { path: '/relocation-map', label: '移住スコアリング', icon: '🗺️', sub: '住みやすさ可視化' }
];

export default function SidebarDefault() {

  const [chatHistory] = useState([
    {
      id: 1,
      title: "技術評論社のスクレイピング"
    },
    {
      id: 2,
      title: "Ollamaのベクトル化テスト"
    },
    {
      id: 3,
      title: "ReactのUIコンポーネント設計"
    }
  ]);

  return (
    <aside
      className="
        w-64
        bg-gray-900
        text-gray-100
        flex
        flex-col
        h-screen
        flex-shrink-0
        border-r
        border-gray-800
      "
    >
      {/* Logo */}
      <div className="p-4 border-b border-gray-800 flex items-center gap-2">
        <span className="text-2xl">✨</span>

        <span className="font-bold text-lg">
          Project To
        </span>
      </div>

      {/* New Chat */}
      <div className="p-4">
        <button
          className="
            flex
            items-center
            justify-center
            gap-2
            w-full
            py-2.5
            bg-blue-600
            hover:bg-blue-500
            text-white
            rounded
            font-medium
            transition-colors
          "
        >
          <span className="text-xl leading-none">
            +
          </span>

          <span>
            新しいチャット
          </span>
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto flex flex-col">

        {/* Recent Chat */}
        <div className="px-2 mb-4">

          <div
            className="
              text-xs
              font-bold
              text-gray-500
              px-2
              mb-2
              tracking-wider
            "
          >
            最近のチャット
          </div>

          <div className="space-y-1">

            {chatHistory.map((chat) => (
              <button
                key={chat.id}
                className="
                  w-full
                  text-left
                  px-3
                  py-2
                  rounded
                  hover:bg-gray-800
                  text-sm
                  truncate
                  text-gray-300
                  hover:text-white
                  transition-colors
                "
              >
                💬 {chat.title}
              </button>
            ))}

          </div>
        </div>

        {/* Menu */}
        <nav
          className="
            border-t
            border-gray-800
            pt-4
          "
        >

          <div
            className="
              text-xs
              font-bold
              text-gray-500
              px-4
              mb-2
              tracking-wider
            "
          >
            システムメニュー
          </div>

          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.exact}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 px-4 py-3 text-sm transition-colors",

                  isActive
                    ? "bg-blue-600/10 text-blue-400 border-r-2 border-blue-500"
                    : "text-gray-300 hover:bg-gray-800 hover:text-white"
                )
              }
            >
              <span className="text-lg w-6 text-center">
                {item.icon}
              </span>

              <div>

                <div className="font-medium">
                  {item.label}
                </div>

                {item.sub && (
                  <div className="text-xs opacity-50 mt-0.5">
                    {item.sub}
                  </div>
                )}

              </div>
            </NavLink>
          ))}

        </nav>
      </div>

      {/* Footer */}
      <div
        className="
          p-4
          border-t
          border-gray-800
          text-xs
          text-gray-500
          flex
          justify-between
          items-center
        "
      >
        <span>
          Project To v1.0
        </span>

        <span
          className="
            cursor-pointer
            hover:text-gray-300
          "
        >
          ⚙️
        </span>
      </div>
    </aside>
  );
}