import React from 'react';
import PageCreateForm from './PageCreateForm';
import PageListItem from './PageListItem';
import DatabaseManager from '../DatabaseManager';
import AiChatPanel from '../AiChatPanel';
import { Page } from '../../types';

interface BuilderDashboardProps {
  pages: Page[];
  newPageTitle: string;
  setNewPageTitle: (val: string) => void;
  onCreatePage: () => void;
  onDeletePage: (page: Page) => void;
}

export default function BuilderDashboard({
  pages,
  newPageTitle,
  setNewPageTitle,
  onCreatePage,
  onDeletePage
}:  BuilderDashboardProps) {
  return (
    <div className="p-8 bg-gray-50 h-full overflow-y-auto w-full">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">プロジェクト・ダッシュボード</h1>
          <p className="text-sm text-gray-500 mt-2">AI / Database / Builder を統合管理</p>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
          {/* 左側：ページ管理 */}
          <div className="xl:col-span-2 space-y-6">
            <PageCreateForm
              title={newPageTitle}
              onChange={setNewPageTitle}
              onCreate={onCreatePage}
            />

            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="p-4 bg-gray-50 border-b border-gray-200">
                <h3 className="font-bold text-gray-700 text-sm">作成済みページ ({pages.length})</h3>
              </div>
              <div className="divide-y divide-gray-100">
                {pages.length === 0 ? (
                  <div className="p-12 text-center text-gray-400 text-sm">まだページがありません</div>
                ) : (
                  pages.map((page) => (
                    <PageListItem key={page.id} page={page} onDelete={onDeletePage} />
                  ))
                )}
              </div>
            </div>
          </div>

          {/* 右側：DB管理 ＆ コマンドなしAIチャット */}
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                <span>🗄️</span> データベース管理
              </h3>
              <DatabaseManager />
            </div>
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
              <AiChatPanel onAiCommand={null} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

  // if (showPageList || !pageId) {
  //   return (
  //     <BuilderDashboard
  //       pages={pages}
  //       newPageTitle={newPageTitle}
  //       setNewPageTitle={setNewPageTitle}
  //       onCreatePage={createPage}
  //       onDeletePage={deletePage}
  //     />
  //   );
  // }