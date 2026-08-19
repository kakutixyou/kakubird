import { wardManifest, getWardByValue } from '../../constants/wardManifest';

// ============================================================
// 背景（演出）レジストリ。
//
// 1区1ファイルの規約:
//   canvas型     … ./canvas/<key>.js       に export const key / label / run(canvas)
//   component型  … ./components/<key>/*.jsx に export const key / label と default export（Component）
//
// ファイルを置くだけで自動登録される（このファイルを編集する必要はない）。
// import.meta.glob の第一引数は静的な文字列である必要があるので、
// パス自体を動的に組み立てることはできない点に注意。
// ============================================================

const registry = {};

function registerCanvasEffect(key, def) {
  registry[key] = { type: 'canvas', ...def };
}

function registerComponentEffect(key, def) {
  registry[key] = { type: 'component', ...def };
}

// ---- canvas型を自動収集 ----
const canvasModules = import.meta.glob('./canvas/*.js', { eager: true });
Object.entries(canvasModules).forEach(([path, mod]) => {
  if (!mod.key || typeof mod.run !== 'function') {
    console.warn(`[backgroundRegistry] ${path} に key または run(canvas) がありません。スキップします。`);
    return;
  }
  registerCanvasEffect(mod.key, { label: mod.label || mod.key, run: mod.run });
});

// ---- component型を自動収集 ----
const componentModules = import.meta.glob('./components/**/*.jsx', { eager: true });
Object.entries(componentModules).forEach(([path, mod]) => {
  if (!mod.key || !mod.default) {
    console.warn(`[backgroundRegistry] ${path} に key または default export（Component）がありません。スキップします。`);
    return;
  }
  registerComponentEffect(mod.key, { label: mod.label || mod.key, Component: mod.default });
});

/**
 * 指定キーの演出を取得。無ければ 'default' にフォールバック。
 */
export function getEffect(key) {
  return registry[key] || registry.default;
}

export function listEffects() {
  return Object.entries(registry).map(([key, def]) => ({ key, label: def.label, type: def.type }));
}

/**
 * 1〜100の数値から、対応する演出キーを解決する。
 * wardManifest の range を見るだけなので、区を1つ足すときは
 * wardManifest.js に1行足すだけで背景側も自動で追従する。
 * どの区にも当たらない場合は 'default' を返す。
 */
export function resolveEffectKeyByValue(value) {
  const ward = getWardByValue(value);
  return ward ? ward.backgroundKey : 'default';
}

// デバッグ用途（コンソールから wardManifest.length と登録済み演出数を突き合わせたい時などに）
export function getRegisteredKeys() {
  return Object.keys(registry);
}

export { wardManifest };
