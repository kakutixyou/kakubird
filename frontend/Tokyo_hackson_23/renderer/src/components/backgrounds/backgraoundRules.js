// ============================================================
// 「1〜100の数値 → どの演出を出すか」を決めるルールテーブル。
// 区のスコア（パーセンタイルランク0〜100）や、テスト用に手でクリックした
// 数値など、0〜100の値を渡せる場面ならどこでも使い回せる。
//
// 上から順に評価し、最初にマッチしたルールを採用する。
// どれにもマッチしなければ 'default' にフォールバック。
// ============================================================

export const backgroundRules = [
  // 93〜100 → 葛飾区の柴又帝釈天参道演出
  { min: 93, max: 100, key: 'katsushika' },

  // 中央区の橋がかかる演出をとりあえず80〜92に仮置き
  // （実際のしきい値・区マッピングが決まったら調整してください）
  { min: 80, max: 92, key: 'chuo' },

  // それ以外は 'default'（浮世絵・金箔・桜）にフォールバックさせる
];

/**
 * 0〜100の数値から、対応する演出キーを返す。
 * @param {number} value
 * @returns {string} 演出キー（マッチなしなら 'default'）
 */
export function resolveEffectKeyByValue(value) {
  const rule = backgroundRules.find((r) => value >= r.min && value <= r.max);
  return rule ? rule.key : 'default';
}