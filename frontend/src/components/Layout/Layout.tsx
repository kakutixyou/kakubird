// frontend/src/components/Layout/Layout.tsx
import React from 'react';
import { Outlet } from 'react-router-dom';
// 👇 作成した index.tsx から Sidebar を読み込むように変更
import { Sidebar } from './sidebar_themes'; 

export default function Layout() {
  return (
    <div className="flex h-screen w-full bg-white dark:bg-slate-900 overflow-hidden text-slate-800 dark:text-slate-200">
      <Sidebar />
      <main className="flex-1 flex flex-col h-full relative">
        <div className="flex-1 overflow-y-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}