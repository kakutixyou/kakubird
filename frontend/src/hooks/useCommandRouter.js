// packages/ai-chat-component/src/hooks/useCommandRouter.js

import { loadPlugin } from '../services/pluginLoader';

export function buildCommandPayload(input) {
  // 通常のメッセージ
  if (!input.startsWith('/')) {
    return {
      message: input,
      mode: 'custom',
      plugin: null,
      config: null,
    };
  }

  // 例: "/css 月光の第三楽章みたいなCSS"
  const [command, ...rest] = input.trim().split(' ');
  const commandName = command.slice(1); // "/css" → "css"
  const prompt = rest.join(' ').trim();

  // 対応するプラグインを読み込む
  const plugin = loadPlugin(commandName);

  // プラグインが見つからない場合
  if (!plugin) {
    return {
      message: input,
      mode: 'custom',
      plugin: null,
      config: null,
    };
  }

  // コマンド用 payload
  return {
    message: prompt,
    mode: `${commandName}_generation`,
    plugin: plugin.name,
    config: plugin.data.defaults,
  };
}