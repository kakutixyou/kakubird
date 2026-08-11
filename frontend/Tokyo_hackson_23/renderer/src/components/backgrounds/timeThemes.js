// 時間帯ごとのテーマ定義。
// 新しい時間帯を増やしたり、時間帯ごとのアニメーションを差し替えたい時は
// このファイルだけを編集すればよい(他のファイルやapp.jsxは触らない)。
//
// animation は ambientAnimations.js の ANIMATIONS のキーと対応させる。

export const TIME_THEMES = [
  { id: 'dawn', start: 5, end: 9, label: '朝', base: [255, 183, 140], animation: 'drift' },
  { id: 'day', start: 9, end: 17, label: '昼', base: [140, 200, 255], animation: 'drift' },
  { id: 'dusk', start: 17, end: 20, label: '夕', base: [255, 120, 150], animation: 'pulse' },
  { id: 'night', start: 20, end: 5, label: '夜', base: [140, 150, 255], animation: 'drift' },
];

// 深夜またぎ(例: 20時〜翌5時)にも対応した現在時刻のテーマ取得
export function getCurrentTimeTheme(date = new Date()) {
  const h = date.getHours();
  const theme = TIME_THEMES.find((t) =>
    t.start < t.end ? h >= t.start && h < t.end : h >= t.start || h < t.end
  );
  return theme || TIME_THEMES[TIME_THEMES.length - 1];
}