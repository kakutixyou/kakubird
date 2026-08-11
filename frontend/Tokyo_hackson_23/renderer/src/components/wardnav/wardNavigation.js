// districtsData.js が既に持っている x,y (地図上のパーセント座標) だけを使って
// 「今の区から見て上/下/左/右に一番近い区」を探す。
// 行政境界の正確なポリゴンデータを別途用意しなくても、既存の座標だけで
// 十分自然な隣接ナビゲーションになる。React に依存しない純粋関数なので
// テストもしやすい。

const DIRECTIONS = {
  up: { dx: 0, dy: -1 },
  down: { dx: 0, dy: 1 },
  left: { dx: -1, dy: 0 },
  right: { dx: 1, dy: 0 },
};

// 指定方向との角度差が小さく、かつ距離が近い区ほど良いスコア(小さい値)にする
export function findWardInDirection(currentDistrict, direction, allDistricts) {
  const dir = DIRECTIONS[direction];
  if (!dir || !currentDistrict) return null;

  let best = null;
  let bestScore = Infinity;

  for (const d of allDistricts) {
    if (d.code === currentDistrict.code) continue;
    const dx = d.x - currentDistrict.x;
    const dy = d.y - currentDistrict.y;
    const dist = Math.hypot(dx, dy);
    if (dist === 0) continue;

    const dot = (dx / dist) * dir.dx + (dy / dist) * dir.dy;
    // 進みたい方向から大きく外れている候補(cosで見て概ね72度以上ズレ)は除外
    if (dot <= 0.3) continue;

    // 角度のズレが小さいほど・距離が近いほどスコアが小さくなるようにする
    const score = dist * (1.4 - dot);
    if (score < bestScore) {
      bestScore = score;
      best = d;
    }
  }
  return best;
}

// タッチのスワイプ量(dx, dy)を上下左右いずれかの方向に変換する。
// 「指を左に動かす = カメラは右の区へ進む」という一般的なスワイプ感覚に合わせてある。
// 逆の感覚にしたい場合はここだけ直せばよい。
export function swipeToDirection(dx, dy) {
  if (Math.abs(dx) < 24 && Math.abs(dy) < 24) return null; // 誤操作防止のしきい値
  if (Math.abs(dx) > Math.abs(dy)) {
    return dx > 0 ? 'left' : 'right';
  }
  return dy > 0 ? 'up' : 'down';
}