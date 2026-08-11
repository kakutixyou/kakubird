// frontend/Tokyo_hackson_23/src/utils/PillarMeta.js

export const PILLAR_CATEGORIES = [
  { id: 'Work', name: 'ワーク環境', icon: '💻', weight: 0.20, enabled: true },
  { id: 'Medical', name: '医療・病院', icon: '🏥', weight: 0.25, enabled: true },
  { id: 'Shopping', name: '買い物・スーパー', icon: '🛒', weight: 0.25, enabled: true },
  { id: 'Health', name: '健康・スポーツ', icon: '🏃', weight: 0.15, enabled: true },
  { id: 'Park', name: '公園・緑地', icon: '🌳', weight: 0.15, enabled: true },
];

// 2点間の距離（メートル）を球面三角法（Haversine）で算出
// 呼び出し側の使い方 ([lat,lng]配列を2つ渡す) に合わせて引数を統一しています
export const calculateDistanceMeters = (pos1, pos2) => {
  const [lat1, lon1] = pos1;
  const [lat2, lon2] = pos2;
  const R = 6371e3;
  const φ1 = (lat1 * Math.PI) / 180;
  const φ2 = (lat2 * Math.PI) / 180;
  const Δφ = ((lat2 - lat1) * Math.PI) / 180;
  const Δλ = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
    Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
};

// 徒歩分数からのスコア算出（距離ベースのスコアリングはこの1箇所に統一）
export const getDistanceScore = (minutes) => {
  if (minutes <= 5) return 100;
  if (minutes <= 10) return 90;
  if (minutes <= 15) return 75;
  if (minutes <= 30) return 50;
  return 30;
};