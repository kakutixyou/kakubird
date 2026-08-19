import React from "react";
import { NavLink } from "react-router-dom";
import clsx from "clsx";

const NAV_ITEMS = [
  { path: "/", label: "ダッシュボード", icon: "🚀" },
  { path: "/builder", label: "Builder", icon: "⚡" },
  { path: "/templates", label: "Templates", icon: "🎨" },
  { path: "/databases", label: "Database", icon: "🧬" },
  { path: "/memory", label: "Memory", icon: "🧠" },
  { path: "/settings-api", label: "Theme", icon: "⚙️" },
  { path: '/relocation-map', label: '移住スコアリング', icon: '🗺️', sub: '住みやすさ可視化' }
];

export default function SidebarFuturePurple() {
  return (
    <aside
      className="
      w-64
      bg-gradient-to-b
      from-violet-950
      via-purple-900
      to-slate-950
      text-white
      border-r
      border-violet-700
      flex
      flex-col
    "
    >
      <div className="p-5 border-b border-violet-700">
        <h1 className="font-bold text-xl">
          Future Purple
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
                  ? "bg-violet-500/30 border-l-4 border-fuchsia-400"
                  : "hover:bg-violet-700/30"
              )
            }
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="p-4 text-xs text-violet-300">
        AI Future Interface
      </div>
    </aside>
  );
}