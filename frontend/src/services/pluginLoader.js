import cssPlugin from '../../../plugins/my-awesome-builder-main/packages/style-system/plugins/css-command-plugin.json';

export function loadPlugin(name) {
  if (name === 'css') {
    return {
      name: 'css-command-plugin',
      data: cssPlugin,
    };
  }
  return null;
}
const pluginMap = {
  css: {
    name: 'css-command-plugin',
    data: cssPlugin,
  },
};

// export function loadPlugin(command) {
//   return pluginMap[command] || null;
// }
