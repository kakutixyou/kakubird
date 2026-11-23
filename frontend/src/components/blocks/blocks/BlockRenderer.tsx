// BlockRenderer.tsx
import * as React from "react";

import GithubRepoListBlock from "./GithubRepoListBlock";
import HeroBlock from "./HeroBlock";
import DatabaseSchemaBlock from "./DatabaseSchemaBlock";
import ProjectBuildBlock from "./ProjectBuildBlock";

export interface ChatBlock {
  type: string;
  data?: unknown;
  id?: string | number | null;
  [key: string]: unknown;
}

export interface BlockComponentProps {
  block: ChatBlock;
  data?: unknown;
  apiBaseUrl?: string;
}

export type BlockComponent = React.ComponentType<BlockComponentProps>;
export type BlockRendererRegistry = Record<string, BlockComponent>;

export interface BlockRendererProps {
  block: ChatBlock | null | undefined;
  /** 既存アプリのレンダラーは組み込みレンダラーとマージされます。 */
  renderers?: BlockRendererRegistry;
  apiBaseUrl?: string;
  fallback?: React.ReactNode | ((block: ChatBlock) => React.ReactNode);
}

/* ------------------------------------------------------------------ */
/* 既存ブロック（旧 BlockRenderer.jsx 由来）                             */
/* これらのコンポーネントは block プロップのみを受け取る前提のため、       */
/* 新しいレジストリ形式に合わせてアダプターでラップする。                  */
/* ------------------------------------------------------------------ */

const GithubRepoListAdapter: BlockComponent = ({ block }) => (
  <GithubRepoListBlock block={block} />
);

const HeroBlockAdapter: BlockComponent = ({ block }) => <HeroBlock block={block} />;

const DatabaseSchemaAdapter: BlockComponent = ({ block }) => (
  <DatabaseSchemaBlock block={block} />
);

/* ------------------------------------------------------------------ */
/* 新規ブロック（project_generation 機能）                              */
/* ------------------------------------------------------------------ */

const ProjectBuildBlockAdapter: BlockComponent = ({ block, data, apiBaseUrl }) => (
  <ProjectBuildBlock block={block} data={data} apiBaseUrl={apiBaseUrl} />
);

/** このファイルが提供する組み込みレンダラー一覧。 */
export const blockRenderers: BlockRendererRegistry = {
  // 旧 switch 文の分岐をそのまま移植
  githubrepolist: GithubRepoListAdapter,
  heroblock: HeroBlockAdapter,
  databaseschema: DatabaseSchemaAdapter,

  // project_generation 機能で追加されたブロック
  project_build: ProjectBuildBlockAdapter,
  "project-build": ProjectBuildBlockAdapter,
  projectbuild: ProjectBuildBlockAdapter,
};

export function normalizeBlockType(value: unknown): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "_");
}

/** 既存ブロックを消さずに project_generation のブロックを追加する。 */
export function createBlockRenderers(
  existing: BlockRendererRegistry = {},
): BlockRendererRegistry {
  return {
    ...existing,
    ...blockRenderers,
  };
}

function DefaultFallback({ block }: { block: ChatBlock }): React.ReactElement {
  return (
    <div
      role="note"
      style={{
        padding: "10px 12px",
        border: "1px solid #d9e2ec",
        borderRadius: 10,
        background: "#f8fafc",
        color: "#5f6c7b",
        fontSize: 13,
        lineHeight: 1.5,
      }}
    >
      未対応の表示ブロックです: <code>{block.type || "unknown"}</code>
    </div>
  );
}

export function BlockRenderer({
  block,
  renderers,
  apiBaseUrl,
  fallback,
}: BlockRendererProps): React.ReactElement | null {
  if (!block || typeof block.type !== "string") return null;

  const registry = renderers ? createBlockRenderers(renderers) : blockRenderers;
  const Renderer = registry[normalizeBlockType(block.type)];
  if (Renderer) {
    return <Renderer block={block} data={block.data} apiBaseUrl={apiBaseUrl} />;
  }

  if (typeof fallback === "function") {
    return <>{fallback(block)}</>;
  }
  if (fallback !== undefined) {
    return <>{fallback}</>;
  }
  return <DefaultFallback block={block} />;
}

export default BlockRenderer;