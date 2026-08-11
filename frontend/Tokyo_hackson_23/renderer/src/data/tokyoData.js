// tokyoData.js
export const METRIC_KEYS = {
  PARK: 'park', DISASTER: 'disaster', AED: 'aed', SPORTS: 'sports',
  CHILDCARE: 'childcare', COMMERCE_LIFE: 'commerce_life',
  COMMERCE_CBD: 'commerce_cbd', LIBRARY: 'library', COMMERCE: 'commerce',
  POPULATION: 'population', SAFETY: 'safety',
};

// カテゴリやメタデータは元のまま
export const CATEGORIES = {
  all: { id: 'all', label: '総合バランス', emoji: '✨', metrics: [METRIC_KEYS.PARK, METRIC_KEYS.DISASTER, METRIC_KEYS.AED, METRIC_KEYS.CHILDCARE, METRIC_KEYS.COMMERCE_LIFE, METRIC_KEYS.SAFETY] },
  childcare: { id: 'childcare', label: '保育・防災安心', emoji: '👶', metrics: [METRIC_KEYS.CHILDCARE, METRIC_KEYS.DISASTER, METRIC_KEYS.PARK], weights: { [METRIC_KEYS.CHILDCARE]: 0.5, [METRIC_KEYS.DISASTER]: 0.3, [METRIC_KEYS.PARK]: 0.2 } },
  education: { id: 'education', label: '教育・育成', emoji: '📚', metrics: [METRIC_KEYS.LIBRARY, METRIC_KEYS.SPORTS, METRIC_KEYS.SAFETY] },
  population: { id: 'population', label: '人口・賑わい', emoji: '📈', metrics: [METRIC_KEYS.POPULATION, METRIC_KEYS.COMMERCE_CBD, METRIC_KEYS.COMMERCE_LIFE] },
  safety: { id: 'safety', label: '治安・防犯', emoji: '🛡️', metrics: [METRIC_KEYS.SAFETY, METRIC_KEYS.DISASTER, METRIC_KEYS.AED] }
};

export const RANK_CONFIG = {
  S: { label: 'Sランク', color: '#ffd700' },
  A: { label: 'Aランク', color: '#00ff9f' },
  B: { label: 'Bランク', color: '#05d5e7' },
  C: { label: 'Cランク', color: '#aaaaaa' },
};

// 📍 3Dマップ用の x, y 座標に加えて、OSMマップジャンプ用の lat(緯度), lng(経度) を追加
export const TOKYO_23_DISTRICTS = [
  { code: '13101', name: '千代田区', effectKey: 'chiyoda', bestEmoji: '🏢', x: 50, y: 50, lat: 35.6940, lng: 139.7536, scores: { park: 80, safety: 95 } },
  { code: '13102', name: '中央区', effectKey: 'chuo', bestEmoji: '🛍️', x: 58, y: 55, lat: 35.6706, lng: 139.7715, scores: { commerce_cbd: 98, population: 95 } },
  { code: '13103', name: '港区', effectKey: 'minato', bestEmoji: '🗼', x: 48, y: 65, lat: 35.6581, lng: 139.7515, scores: { commerce_cbd: 95, safety: 85 } },
  { code: '13104', name: '新宿区', effectKey: 'shinjuku', bestEmoji: '🏙️', x: 35, y: 45, lat: 35.6938, lng: 139.7034, scores: { commerce_cbd: 100, safety: 50 } },
  { code: '13105', name: '文京区', effectKey: 'bunkyo', bestEmoji: '🎓', x: 48, y: 38, lat: 35.7078, lng: 139.7523, scores: { safety: 98, library: 95 } },
  { code: '13106', name: '台東区', effectKey: 'taito', bestEmoji: '🏮', x: 60, y: 35, lat: 35.7126, lng: 139.7802, scores: { commerce_life: 85, library: 80 } },
  { code: '13107', name: '墨田区', effectKey: 'sumida', bestEmoji: '🎆', x: 68, y: 40, lat: 35.7107, lng: 139.8015, scores: { disaster: 70, park: 70 } },
  { code: '13108', name: '江東区', effectKey: 'koto', bestEmoji: '🌉', x: 68, y: 60, lat: 35.6728, lng: 139.8174, scores: { population: 95, childcare: 90 } },
  { code: '13109', name: '品川区', effectKey: 'shinagawa', bestEmoji: '🚄', x: 45, y: 78, lat: 35.6092, lng: 139.7302, scores: { childcare: 92, commerce_life: 88 } },
  { code: '13110', name: '目黒区', effectKey: 'meguro', bestEmoji: '☕', x: 35, y: 72, lat: 35.6415, lng: 139.6981, scores: { safety: 85, commerce_life: 80 } },
  { code: '13111', name: '大田区', effectKey: 'ota', bestEmoji: '✈️', x: 45, y: 92, lat: 35.5612, lng: 139.7161, scores: { sports: 85, disaster: 70 } },
  { code: '13112', name: '世田谷区', effectKey: 'setagaya', bestEmoji: '🌳', x: 20, y: 68, lat: 35.6466, lng: 139.6533, scores: { park: 95, childcare: 88 } },
  { code: '13113', name: '渋谷区', effectKey: 'shibuya', bestEmoji: '🐕', x: 35, y: 58, lat: 35.6620, lng: 139.7038, scores: { commerce_cbd: 95, commerce_life: 92 } },
  { code: '13114', name: '中野区', effectKey: 'nakano', bestEmoji: '👾', x: 28, y: 45, lat: 35.7074, lng: 139.6638, scores: { commerce_life: 95, population: 85 } },
  { code: '13115', name: '杉並区', effectKey: 'suginami', bestEmoji: '🎸', x: 18, y: 45, lat: 35.6997, lng: 139.6355, scores: { park: 85, commerce_life: 90 } },
  { code: '13116', name: '豊島区', effectKey: 'toshima', bestEmoji: '🦉', x: 35, y: 32, lat: 35.7263, lng: 139.7169, scores: { commerce_cbd: 90, library: 85 } },
  { code: '13117', name: '北区', effectKey: 'kita', bestEmoji: '🌸', x: 48, y: 15, lat: 35.7528, lng: 139.7335, scores: { park: 85, commerce_life: 80 } },
  { code: '13118', name: '荒川区', effectKey: 'arakawa', bestEmoji: '🚋', x: 58, y: 25, lat: 35.7360, lng: 139.7836, scores: { commerce_life: 85, safety: 75 } },
  { code: '13119', name: '板橋区', effectKey: 'itabashi', bestEmoji: '🏞️', x: 28, y: 18, lat: 35.7512, lng: 139.7093, scores: { park: 85, childcare: 80 } },
  { code: '13120', name: '練馬区', effectKey: 'nerima', bestEmoji: '🥬', x: 12, y: 25, lat: 35.7356, lng: 139.6517, scores: { park: 98, disaster: 85 } },
  { code: '13121', name: '足立区', effectKey: 'adachi', bestEmoji: '♨️', x: 62, y: 10, lat: 35.7750, lng: 139.8044, scores: { commerce_life: 88, park: 80 } },
  { code: '13122', name: '葛飾区', effectKey: 'katsushika', bestEmoji: '🎬', x: 80, y: 22, lat: 35.7433, lng: 139.8471, scores: { commerce_life: 85, park: 80 } },
  { code: '13123', name: '江戸川区', effectKey: 'edogawa', bestEmoji: '👶', x: 85, y: 48, lat: 35.7067, lng: 139.8665, scores: { childcare: 95, park: 90 } },
];