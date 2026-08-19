import React from "react";
import { NavLink } from "react-router-dom";
import clsx from "clsx";

const NAV_ITEMS = [
  { path: "/", label: "ダッシュボード", icon: "🏛️" },
  { path: "/builder", label: "ビルダー", icon: "⚔️" },
  { path: "/templates", label: "テンプレート", icon: "📜" },
  { path: "/databases", label: "データベース", icon: "🏺" },
  { path: "/memory", label: "メモリー", icon: "🧠" },
  { path: "/settings-api", label: "テーマ設定", icon: "👑" },
  { path: '/relocation-map', label: '移住スコアリング', icon: '🗺️', sub: '住みやすさ可視化' }
];

export default function SidebarAlexandros() {
  return (
    <aside
      className="
      w-64
      bg-amber-50
      border-r
      border-amber-300
      flex
      flex-col
    "
    >
      <div className="p-5 border-b border-amber-300">
        <h1
          className="
          text-amber-800
          font-bold
          text-xl
        "
        >
          Alexandros
        </h1>
      </div>

      <nav className="flex-1 py-3">
        {NAV_ITEMS.map(item => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 px-4 py-3 transition-all",
                isActive
                  ? "bg-amber-200 text-amber-900"
                  : "hover:bg-amber-100"
              )
            }
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="p-4 text-xs text-amber-700">
        Kingdom of Alexandros
      </div>
    </aside>
  );
}