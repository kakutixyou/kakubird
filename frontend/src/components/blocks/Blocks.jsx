// frontend/src/components/blocks.jsx
import React from 'react';

// import MemoryStatusBlock from "src/components/blocks/MemoryStatusBlock";
import ChatBlock from "./ChatBlock";
import GithubRepoListBlock from "./GithubRepoListBlock";

import DatabaseSchemaBlock from './DatabaseSchemaBlock';
import FileDownloadBlock from './FileDownloadBlock';
import RecruitReportBlock from './RecruitReportBlock';
import DiffBlock from './DiffBlock';
import JsonViewerBlock from './JsonViewerBlock';
import SqlPreviewBlock from './SqlPreviewBlock';
import ProjectTreeBlock from './ProjectTreeBlock';
import ChatActionBlock from './ChatActionBlock';
import HtmlCssPreviewBlock from './HtmlCssPreviewBlock';
import DeploymentBlock from './DeploymentBlock';
import ConversionJsonBlock from './conversion_jsonBlock';
import MarkdownChatBlock from './MarkdownChatBlock';
import PhpPreviewBlock from './PhpPreviewBlock';  
import CodeFormatBlock from './CodeFormatBlock';   

// 💡 export を付けて外部からimport可能にする
export const BLOCK_COMPONENTS = {
  // MemoryStatusBlock: MemoryStatusBlock,
  GithubRepoList: GithubRepoListBlock,
  RecruitReportBlock: RecruitReportBlock,
  // HeroBlock: HeroBlock,
  DatabaseSchema: DatabaseSchemaBlock,
  FileDownload: FileDownloadBlock,
  DiffBlock: DiffBlock,
  JsonViewerBlock: JsonViewerBlock,
  SqlPreviewBlock: SqlPreviewBlock,
  SqlExampleModal: SqlPreviewBlock,
  ProjectTreeBlock: ProjectTreeBlock,
  ChatActionBlock: ChatActionBlock,
  HtmlCssPreviewBlock: HtmlCssPreviewBlock,
  DeploymentBlock: DeploymentBlock,
  conversion_jsonBlock: ConversionJsonBlock,
  ChatBlock: ChatBlock,
  MarkdownChatBlock: MarkdownChatBlock,
  PhpPreviewBlock: PhpPreviewBlock,     
  CodeBlock: CodeFormatBlock,           
};

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
            <Component
              block={block}
              {...block.props}
              onOptionSelect={onOptionSelect}
              onOpenManualEdit={onOpenManualEdit}
            />
          </div>
        );
      })}
    </div>
  );
}