export const key = 'ota';
export const label = '大田区：実績解除イベント';

/**
 * @param {object} ward - wardManifestのエントリ（code, ward, motif, hue, image, ...）
 * @param {object} ctx  - 呼び出し側が渡す共通API。例: { unlockBadge, playSound, showToast, setScore }
 */
export function onReveal(ward, ctx) {
  ctx.unlockBadge?.(`${ward.code}_first_visit`);
  ctx.playSound?.('reveal_common');
  ctx.showToast?.(`${ward.ward}「${ward.motif}」を引き当てました`);
}
