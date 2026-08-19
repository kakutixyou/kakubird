// BlockRenderer.jsx
import GithubRepoListBlock from './GithubRepoListBlock';
import HeroBlock from './HeroBlock';
import DatabaseSchemaBlock from './DatabaseSchemaBlock';

export default function BlockRenderer({ block }) {
  switch (block.type) {

    case 'GithubRepoList':
      return <GithubRepoListBlock block={block} />;

    case 'HeroBlock':
      return <HeroBlock block={block} />;

    case 'DatabaseSchema':
      return <DatabaseSchemaBlock block={block} />;

    default:
      return (
        <div className="text-red-400 text-xs">
          Unknown block type: {block.type}
        </div>
      );
  }
}