// MemoryPage.jsx
import React, { useEffect } from 'react';
import { useMemory } from '../hooks/useMemory';
import MemoryContent from '../components/MemoryContent';

// frontend/src/pages/MemoryPage.tsx

import React from "react";
import MemoryManager from "../components/MemoryManager";

/**
 * AI Memory Center
 *
 * MemoryPage は Memory 機能全体を表示するためのページ。
 *
 * 実際のデータ取得・表示・削除などは
 * MemoryManager 側に任せる。
 *
 * MemoryManager:
 * - 最近の記憶
 * - 好きなこと・興味
 * - タスク
 * - 予定
 * - 大きな課題
 * - 会話履歴
 * - 最近触ったファイル
 * - Memory統計
 * - 全記憶削除
 */
export default function MemoryPage(): React.ReactElement {
  return (
    <div className="h-full min-h-0 overflow-y-auto bg-slate-50 dark:bg-slate-950">
      <div className="min-h-full">
        <MemoryManager />
      </div>
    </div>
  );
}