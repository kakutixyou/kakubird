// frontend/src/components/blocks/index.jsx
import React, { Suspense, lazy } from 'react';

// 1. Viteの魔法の関数：ディレクトリ内のすべての .jsx ファイルを自動収集
const modules = import.meta.glob('./*.jsx');

export const BLOCK_COMPONENTS = {};

// 2. 収集したファイルを自動的に lazy コンポーネントとして一括登録
for (const path in modules) {
  // 自分自身（index.jsx）は読み込まないように除外
  if (path.includes('index.jsx')) continue;

  // "./CodeFormatBlock.jsx" -> "CodeFormatBlock" のようにファイル名を取り出す
  const componentName = path.split('/').pop().replace('.jsx', '');
  
  // 自動登録！
  BLOCK_COMPONENTS[componentName] = lazy(modules[path]);
}

// ==========================================
// 3. エイリアス（別名）の賢いルーティング設定
// ==========================================

// 🌟 先ほど作った「万能コードブロック」に、類似の要求をすべて横流しする
if (BLOCK_COMPONENTS.CodeFormatBlock) {
  BLOCK_COMPONENTS.PhpPreviewBlock = BLOCK_COMPONENTS.CodeFormatBlock;
  BLOCK_COMPONENTS.SqlPreviewBlock = BLOCK_COMPONENTS.CodeFormatBlock;
  BLOCK_COMPONENTS.HtmlCssPreviewBlock = BLOCK_COMPONENTS.CodeFormatBlock;
  BLOCK_COMPONENTS.JsonViewerBlock = BLOCK_COMPONENTS.CodeFormatBlock;
  
  // AIが末尾の"Block"を付け忘れて呼んできた時用の保険
  BLOCK_COMPONENTS.CodeBlock = BLOCK_COMPONENTS.CodeFormatBlock;
  // SqlExampleModal も実態はSQLのプレビューなので万能ブロックに任せる
  BLOCK_COMPONENTS.SqlExampleModal = BLOCK_COMPONENTS.CodeFormatBlock;
}

// その他の名前揺れ対応（ファイル名とAIの指定タイプ名がズレているもの）
if (BLOCK_COMPONENTS.GithubRepoListBlock) BLOCK_COMPONENTS.GithubRepoList = BLOCK_COMPONENTS.GithubRepoListBlock;
if (BLOCK_COMPONENTS.DatabaseSchemaBlock) BLOCK_COMPONENTS.DatabaseSchema = BLOCK_COMPONENTS.DatabaseSchemaBlock;
if (BLOCK_COMPONENTS.FileDownloadBlock) BLOCK_COMPONENTS.FileDownload = BLOCK_COMPONENTS.FileDownloadBlock;

// ==========================================
// 4. ブロックを画面にレンダリングする本体
// ==========================================
export function RenderBlocks({ blocks, onOptionSelect, onOpenManualEdit }) {
  if (!blocks || !Array.isArray(blocks) || blocks.length === 0) return null;

  return (
    <div className="ai-custom-blocks-container my-3 space-y-4 w-full">
      {blocks.map((block, index) => {
        const Component = BLOCK_COMPONENTS[block.type];

        // 登録されていないブロックが来た場合のエラーハンドリング
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
            <Suspense fallback={<div className="animate-pulse h-10 bg-gray-200/20 rounded"></div>}>
              <Component
                block={block}
                {...block.props} // 既存の後方互換性のために残す
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