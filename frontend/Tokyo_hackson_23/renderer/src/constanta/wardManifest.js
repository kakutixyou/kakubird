// ============================================================
// 23区の唯一の情報源（Single Source of Truth）。
//
// 背景（backgroundRegistry）もイベント（eventRegistry）も、
// 「区固有のデータ」はここだけを見る。ここに無い情報を
// WardDivination.jsx や各演出ファイルに書き足さないこと。
//
// backgroundKey / eventKey は「どのファイルに実装を探しに行くか」の
// キー。省略した場合は code をそのまま使う（1区1ファイルの規約と
// 揃えているので、基本は省略でOK。演出を複数区で使い回したい時だけ
// 明示的に指定する）。
// ============================================================

export const wardManifest = [
  { code: 'chiyoda',    ward: '千代田区', range: [1, 4],    hue: 28,  motif: '神田明神曙之景',             x: 50, y: 45 },
  { code: 'minato',     ward: '港区',     range: [5, 8],    hue: 205, motif: '高輪うしまち',               x: 48, y: 52 },
  { code: 'shinjuku',   ward: '新宿区',   range: [9, 13],   hue: 280, motif: '四ツ谷内藤新宿',             x: 38, y: 42 },
  { code: 'bunkyo',     ward: '文京区',   range: [14, 17],  hue: 140, motif: '湯しま天神坂上眺望',         x: 46, y: 35 },
  { code: 'taito',      ward: '台東区',   range: [18, 21],  hue: 15,  motif: '浅草金龍山',                 x: 54, y: 35 },
  { code: 'sumida',     ward: '墨田区',   range: [22, 25],  hue: 190, motif: '両ごく回向院元柳橋',         x: 60, y: 38 },
  { code: 'koto',       ward: '江東区',   range: [26, 29],  hue: 220, motif: '大はしあたけの夕立',         x: 62, y: 48 },
  { code: 'chuo',       ward: '中央区',   range: [30, 35],  hue: 40,  motif: '日本橋南詰盛況乃図',         x: 55, y: 42 },
  { code: 'shinagawa',  ward: '品川区',   range: [36, 39],  hue: 195, motif: '品川すさき',                 x: 44, y: 62 },
  { code: 'meguro',     ward: '目黒区',   range: [40, 43],  hue: 160, motif: '目黒新富士',                 x: 38, y: 58 },
  { code: 'ota',        ward: '大田区',   range: [44, 48],  hue: 330, motif: '蒲田の梅園',                 x: 36, y: 72 },
  { code: 'setagaya',   ward: '世田谷区', range: [49, 52],  hue: 250, motif: '玉川秋月',                   x: 26, y: 58 },
  { code: 'shibuya',    ward: '渋谷区',   range: [53, 56],  hue: 300, motif: '太田記念美術館',             x: 36, y: 48 },
  { code: 'nakano',     ward: '中野区',   range: [57, 60],  hue: 320, motif: '中野ブロードウェイ',         x: 26, y: 42 },
  { code: 'suginami',   ward: '杉並区',   range: [61, 65],  hue: 265, motif: '杉並アニメーションミュージアム', x: 18, y: 48 },
  { code: 'toshima',    ward: '豊島区',   range: [66, 69],  hue: 100, motif: '高田姿見のはし俤の橋砂利場', x: 36, y: 32 },
  { code: 'kita',       ward: '北区',     range: [70, 73],  hue: 175, motif: '王子瀧の川',                 x: 42, y: 20 },
  { code: 'arakawa',    ward: '荒川区',   range: [74, 77],  hue: 20,  motif: '日暮里諏訪の台',             x: 52, y: 26 },
  { code: 'itabashi',   ward: '板橋区',   range: [78, 82],  hue: 45,  motif: '東京大仏(乗蓮寺)',           x: 30, y: 20 },
  { code: 'nerima',     ward: '練馬区',   range: [83, 86],  hue: 310, motif: '東映動画発祥の地',           x: 18, y: 28 },
  { code: 'adachi',     ward: '足立区',   range: [87, 90],  hue: 210, motif: '千住之大橋',                 x: 56, y: 15 },
  { code: 'katsushika', ward: '葛飾区',   range: [91, 95],  hue: 270, motif: '堀切の花菖蒲',               x: 66, y: 20 },
  { code: 'edogawa',    ward: '江戸川区', range: [96, 100], hue: 230, motif: '地下鉄博物館',               x: 70, y: 35 },
].map((w) => ({
  ...w,
  image: `/assets/ward-motifs/${w.code}.png`,
  backgroundKey: w.backgroundKey || w.code,
  eventKey: w.eventKey || w.code,
}));

/** 1〜100の数値から、対応する区エントリを返す（見つからなければnull） */
export function getWardByValue(value) {
  return wardManifest.find((w) => value >= w.range[0] && value <= w.range[1]) || null;
}

/** codeから区エントリを直接引く */
export function getWardByCode(code) {
  return wardManifest.find((w) => w.code === code) || null;
}

/** 1〜100のランダムな数値を1つ引き、対応する区エントリを返す */
export function rollWard() {
  const n = 1 + Math.floor(Math.random() * 100);
  return { value: n, ward: getWardByValue(n) };
}
