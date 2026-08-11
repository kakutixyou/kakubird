import React, { Suspense, lazy } from 'react';

// 1. lazy を使って動的インポートに置き換える
// ※パスはすべて ./blocks/ などの専用ディレクトリにまとめる前提にするとさらに綺麗です
export const BLOCK_COMPONENTS = {
  GithubRepoList: lazy(() => import('./GithubRepoListBlock')),
  RecruitReportBlock: lazy(() => import('./RecruitReportBlock')),
  DatabaseSchema: lazy(() => import('./DatabaseSchemaBlock')),
  FileDownload: lazy(() => import('./FileDownloadBlock')),
  DiffBlock: lazy(() => import('./DiffBlock')),
  JsonViewerBlock: lazy(() => import('./JsonViewerBlock')),
  SqlPreviewBlock: lazy(() => import('./SqlPreviewBlock')),
  ProjectTreeBlock: lazy(() => import('./ProjectTreeBlock')),
  ChatActionBlock: lazy(() => import('./ChatActionBlock')),
  HtmlCssPreviewBlock: lazy(() => import('./HtmlCssPreviewBlock')),
  DeploymentBlock: lazy(() => import('./DeploymentBlock')),
  conversion_jsonBlock: lazy(() => import('./conversion_jsonBlock')),
  ChatBlock: lazy(() => import('./ChatBlock')),
  MarkdownChatBlock: lazy(() => import('./MarkdownChatBlock')),
  PhpPreviewBlock: lazy(() => import('./PhpPreviewBlock')),
  CodeBlock: lazy(() => import('./CodeFormatBlock')),
  TypingTestBlock: lazy(() => import('./blocks/TypingTestBlock')),
  ProofreadingTestBlock: lazy(() => import('./blocks/ProofreadingTestBlock')),
};

// エイリアス（別名）が必要な場合は後から代入する
BLOCK_COMPONENTS.SqlExampleModal = BLOCK_COMPONENTS.SqlPreviewBlock;

export function RenderBlocks({ blocks, onOptionSelect, onOpenManualEdit }) {
  if (!blocks || !Array.isArray(blocks) || blocks.length === 0) return null;

  return (
    <div className="ai-custom-blocks-container my-3 space-y-4 w-full">
      {blocks.map((block, index) => {
        const Component = BLOCK_COMPONENTS[block.type];

        if (!Component) {
          console.warn(`[RenderBlocks] 未定義のブロックタイプが検出されました: ${block.type}`);
          return (
            <div key={`error-${index}`} className="text-red-400 text-xs p-2 border border-red-900 bg-red-950/30 rounded">
              未定義のブロック: {block.type}
            </div>
          );
        }

        return (
          <div key={`${block.type}-${index}`} className="animate-fade-in w-full">
            {/* 2. lazyコンポーネントは Suspense で囲む必要がある */}
            <Suspense fallback={<div className="animate-pulse h-10 bg-gray-200/20 rounded"></div>}>
              <Component
                block={block}
                {...block.props}
                onOptionSelect={onOptionSelect}
                onOpenManualEdit={onOpenManualEdit}
              />
            </Suspense>
          </div>
        );
      })}
    </div>
  );
}