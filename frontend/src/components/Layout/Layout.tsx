// frontend/src/components/Layout/Layout.tsx
import React from 'react';
import { Outlet } from 'react-router-dom';
import SidebarDefault from './sidebar_themes/Sidebar_default';

export default function Layout() {
  return (
    // 画面全体を固定し、横並び(flex)にする
    <div className="flex h-screen w-screen bg-slate-50 overflow-hidden">
      
      {/* 🟢 左側: サイドバー領域 (絶対に縮ませず、一番手前に表示) */}
      <div className="flex-shrink-0 z-[9999] relative h-full shadow-xl">
        <SidebarDefault />
      </div>
      
      {/* 🔵 右側: メイン画面 (マップなどがここにはまる) */}
      <main className="flex-1 relative h-full overflow-hidden">
        <Outlet />
      </main>
      
    </div>
  );
}