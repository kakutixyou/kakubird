// src/plugins/PluginManager.ts
import fs from 'fs';
import path from 'path';

export interface Plugin {
  id: string;
  name: string;
  version: string;
  description?: string;
  routes?: any; // ExpressのRouterオブジェクトなどを想定
  onInstall?: () => void;
  onUninstall?: () => void;
}

export class PluginManager {
  static register(githubSearchPlugin: any) {
    throw new Error('Method not implemented.');
  }
  static isActive(arg0: string) {
    throw new Error('Method not implemented.');
  }
  private plugins: Map<string, Plugin> = new Map();

  register(plugin: Plugin) {
    this.plugins.set(plugin.id, plugin);
    console.log(`Plugin registered: ${plugin.name} v${plugin.version}`);
  }

  unregister(id: string) {
    const plugin = this.plugins.get(id);
    if (plugin) {
      if (plugin.onUninstall) plugin.onUninstall();
      this.plugins.delete(id);
    }
  }

  get(id: string): Plugin | undefined {
    return this.plugins.get(id);
  }

  getAll(): Plugin[] {
    return Array.from(this.plugins.values());
  }

  isActive(id: string): boolean {
    return this.plugins.has(id);
  }

  /**
   * 追加：指定ディレクトリ配下のプラグインを動的にスキャン・登録する
   */
  async loadPluginsFromDirectory(targetDir: string) {
    if (!fs.existsSync(targetDir)) {
      console.warn(`Plugin directory not found: ${targetDir}`);
      return;
    }

    const entries = fs.readdirSync(targetDir);

    for (const entry of entries) {
      const pluginFullPath = path.join(targetDir, entry);
      
      // ディレクトリ（github_searchなど）であるかチェック
      if (fs.statSync(pluginFullPath).isDirectory()) {
        try {
          // 各プラグインのメインファイル（index.ts）を動的インポート
          // ※ 実行環境（ts-nodeかビルド後か）に応じてパスや拡張子に注意
          const indexPath = path.join(pluginFullPath, 'index');
          const pluginModule = await import(indexPath);

          // default もしくは名前付きエクスポートから Plugin インターフェースを満たすオブジェクトを取得
          const pluginInstance: Plugin = pluginModule.default || pluginModule.plugin;

          if (pluginInstance && pluginInstance.id) {
            // 既存のレジスタ機能を使って登録
            this.register(pluginInstance);
          } else {
            console.error(`Invalid plugin structure in: ${entry}`);
          }
        } catch (error) {
          console.error(`Failed to load plugin [${entry}]:`, error);
        }
      }
    }
  }
}

export const pluginManager = new PluginManager();