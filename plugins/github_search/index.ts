import { Plugin } from '../../backend/src/plugins/PluginManager';
// backend/src/plugins/github_search/index.ts

import githubSearchRoutes from './routes'; 
import pluginMeta from './meta_data/plugin.json'; // 必要に応じてjsonからメタデータを同期

export const githubSearchPlugin: Plugin = {
  id: 'github_search',
  name: 'GitHub Math Repository Searcher',
  version: '1.0.0',
  description: '数学関連の類似プロジェクトをGitHubからインテリジェントに検索するプラグイン',
  routes: githubSearchRoutes, // ここにExpressのRouterインスタンスを格納
  
  onInstall() {
    console.log('GitHub Search Plugin Installed.');
    // 必要なら初期化処理（Pythonサーバーとの疎通確認など）をここに
  },
  onUninstall() {
    console.log('GitHub Search Plugin Uninstalled.');
  }
};

export default githubSearchPlugin;