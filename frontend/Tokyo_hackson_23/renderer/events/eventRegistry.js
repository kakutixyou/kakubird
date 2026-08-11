import { getWardByValue } from '../constants/wardManifest';

// ============================================================
// イベントレジストリ。
//
// 1区1ファイルの規約:
//   ./wards/<key>.js に export const key / label / onReveal(ward, ctx)
//
// ファイルを置くだけで自動登録される（このファイルを編集する必要はない）。
// backgroundRegistry.js と同じ発想・同じ import.meta.glob パターン。
// ============================================================

const registry = {};

function registerEvent(key, def) {
  registry[key] = def;
}

const eventModules = import.meta.glob('./wards/*.js', { eager: true });
Object.entries(eventModules).forEach(([path, mod]) => {
  if (!mod.key || typeof mod.onReveal !== 'function') {
    console.warn(`[eventRegistry] ${path} に key または onReveal(ward, ctx) がありません。スキップします。`);
    return;
  }
  registerEvent(mod.key, { label: mod.label || mod.key, onReveal: mod.onReveal });
});

/**
 * 指定キーのイベントを取得。登録が無ければ null
 * （背景と違い、イベントは「何も起きない」が正しいデフォルトなので default にフォールバックしない）。
 */
export function getEvent(key) {
  return registry[key] || null;
}

export function listEvents() {
  return Object.entries(registry).map(([key, def]) => ({ key, label: def.label }));
}

/**
 * 1〜100の数値から対応するイベントを解決して実行する。
 * ward.eventKey に紐づくイベントが未実装でも安全に無視される。
 *
 * @param {number} value  - 1〜100（WardDivinationなどで出た数値と同じもの）
 * @param {object} ctx    - onReveal に渡す共通API（例: { unlockBadge, playSound, setScore }）
 */
export function fireEventForValue(value, ctx = {}) {
  const ward = getWardByValue(value);
  if (!ward) return;
  const event = getEvent(ward.eventKey);
  if (!event) return; // このwardのイベントはまだ未実装 → 何もしない
  event.onReveal(ward, ctx);
}
