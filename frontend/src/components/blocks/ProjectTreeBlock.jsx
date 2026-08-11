import React from 'react';

export default function ProjectTreeBlock({ block }) {
    const ProjectTreeBlock = ({ block }) => {
      const { rootName = "project/", tree = [] } = block.props || {};
      
      const renderNode = (nodes, depth = 0) => {
        return nodes.map((node, idx) => (
          <div key={idx} style={{ paddingLeft: `${depth * 12}px` }} className="text-xs font-mono py-0.5">
            <span className="text-slate-400 mr-1">{node.children ? "📁" : "📄"}</span>
            <span className={node.children ? "text-indigo-600 dark:text-indigo-400 font-medium" : "text-slate-700 dark:text-slate-300"}>
              {node.name}
            </span>
            {node.children && <div className="mt-0.5">{renderNode(node.children, depth + 1)}</div>}
          </div>
        ));
      };
    
      return (
        <div className="border border-slate-200 dark:border-slate-700 rounded-lg p-3 bg-slate-50 dark:bg-slate-900/40">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Project Structure</div>
          <div className="font-mono text-xs text-indigo-600 dark:text-indigo-400 font-bold mb-1">🌿 {rootName}</div>
          <div className="border-l-2 border-slate-200 dark:border-slate-800 pl-2 space-y-1">
            {renderNode(tree)}
          </div>
        </div>
      );
    };
    const renderBlock = (block, index) => {
      switch (block.type) {
        case 'GithubRepoList':
          return <GithubRepoListBlock key={index} block={block} />;
          
        // 🌟 これを追加！ バックエンドから "RecruitReportBlock" と言われたらこれを出す
        case 'RecruitReportBlock':
          return <RecruitReportBlock key={index} block={block} />;
          
        default:
          return <div key={index}>Unknown block type: {block.type}</div>;
      }
    };
}

