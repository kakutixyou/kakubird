export const key = 'chuo';
export const label = '中央区：日本橋 架橋演出';

/**
 * @param {object} ward - wardManifestのエントリ（code, ward, motif, hue, image, ...）
 * @param {object} ctx  - 呼び出し側が渡す共通API。例: { unlockBadge, playSound, showToast, setScore }
 */
export function onReveal(ward, ctx) {
  ctx.unlockBadge?.(`${ward.code}_first_visit`);
  ctx.playSound?.('reveal_common');
  ctx.showToast?.(`${ward.ward}「${ward.motif}」を引き当てました`);
}

/**
 * 中央区の演出（Canvas型）。
 * 日本橋モチーフ：橋が左右から中央へ架かっていき、
 * 橋を構成する3本のライン（欄干・親柱ライン・桁）が順に煌めきながら
 * 水面に反射する。全て2D Canvasの図形描画のみで構成。
 */
export function run(canvas) {
  const ctx = canvas.getContext('2d');
  let w, h, raf, t = 0;
  const buildStart = performance.now();
  const BUILD_MS = 2200; // 橋が架かりきるまでの時間

  const resize = () => {
    w = canvas.width = canvas.clientWidth;
    h = canvas.height = canvas.clientHeight;
  };
  window.addEventListener('resize', resize);
  resize();

  // ---- 波（水面。中央区は落ち着いた金色の反射にする） ----
  const waveLayers = [
    { amp: 5, freq: 0.022, speed: 0.02, alpha: 0.18, yRatio: 0.66 },
    { amp: 9, freq: 0.015, speed: 0.04, alpha: 0.26, yRatio: 0.76 },
    { amp: 14, freq: 0.011, speed: 0.06, alpha: 0.38, yRatio: 0.88 },
  ];

  // ---- 橋を構成する3本のライン（上から：親柱ライン／欄干ライン／桁ライン） ----
  // yRatio: 橋の中でのライン位置、pulseOffset: 光が流れるタイミングをずらす
  const bridgeLines = [
    { yRatio: 0.0, pulseOffset: 0.0 },
    { yRatio: 0.45, pulseOffset: 0.33 },
    { yRatio: 1.0, pulseOffset: 0.66 },
  ];

  function easeOutCubic(x) {
    return 1 - Math.pow(1 - x, 3);
  }

  function drawSky() {
    const bridgeTopY = h * 0.5;
    const grad = ctx.createLinearGradient(0, 0, 0, bridgeTopY);
    grad.addColorStop(0, '#120d05');
    grad.addColorStop(0.6, '#2a1c0c');
    grad.addColorStop(1, '#4a3212');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, bridgeTopY);
  }

  function drawWater(reflectPoints) {
    const waterTop = h * 0.62;
    const grad = ctx.createLinearGradient(0, waterTop, 0, h);
    grad.addColorStop(0, '#26190a');
    grad.addColorStop(1, '#050301');
    ctx.fillStyle = grad;
    ctx.fillRect(0, waterTop, w, h - waterTop);

    waveLayers.forEach((layer) => {
      ctx.beginPath();
      ctx.moveTo(0, h);
      const baseY = h * layer.yRatio;
      for (let x = 0; x <= w; x += 8) {
        const y = baseY + Math.sin(x * layer.freq + t * layer.speed * 30) * layer.amp;
        ctx.lineTo(x, y);
      }
      ctx.lineTo(w, h);
      ctx.closePath();
      ctx.fillStyle = `rgba(120,90,40,${layer.alpha})`;
      ctx.fill();
    });

    // 橋の3本ラインからの光の反射（水面に落ちる縦の光の帯、波でゆらぐ）
    reflectPoints.forEach(({ x, glow }) => {
      if (glow <= 0.02) return;
      for (let y = waterTop; y < h; y += 6) {
        const sway = Math.sin(y * 0.05 + t * 1.5) * 6 * ((y - waterTop) / (h - waterTop));
        const fade = 1 - (y - waterTop) / (h - waterTop);
        ctx.fillStyle = `rgba(255,210,120,${glow * fade * 0.35})`;
        ctx.fillRect(x + sway - 1.5, y, 3, 4);
      }
    });
  }

  function draw() {
    t += 0.016;
    const elapsed = performance.now() - buildStart;
    const buildProgress = easeOutCubic(Math.min(1, elapsed / BUILD_MS));

    ctx.clearRect(0, 0, w, h);
    drawSky();

    const bridgeTopY = h * 0.5;
    const bridgeBottomY = h * 0.62;
    const centerX = w * 0.5;
    const pierLeftX = w * 0.18;
    const pierRightX = w * 0.82;
    const bridgeHalfSpan = (centerX - pierLeftX) * buildProgress;

    // ---- 橋脚（両端。先に立ち上がる） ----
    const pierH = (bridgeBottomY - bridgeTopY * 0.3) * Math.min(1, buildProgress * 1.6);
    ctx.fillStyle = 'rgba(40,28,14,0.9)';
    [pierLeftX, pierRightX].forEach((px) => {
      ctx.fillRect(px - w * 0.012, bridgeBottomY - pierH, w * 0.024, pierH);
    });

    // ---- 橋桁：左右の橋脚から中央へ向かって伸びていく ----
    const deckLeftEndX = pierLeftX + bridgeHalfSpan;
    const deckRightEndX = pierRightX - bridgeHalfSpan;

    const reflectPoints = [];

    bridgeLines.forEach((line, i) => {
      const y = bridgeTopY + (bridgeBottomY - bridgeTopY) * line.yRatio;

      // 左側スパン
      ctx.strokeStyle = 'rgba(220,190,140,0.85)';
      ctx.lineWidth = i === 1 ? 3 : 2;
      ctx.beginPath();
      ctx.moveTo(pierLeftX, y);
      ctx.lineTo(deckLeftEndX, y);
      ctx.stroke();

      // 右側スパン
      ctx.beginPath();
      ctx.moveTo(pierRightX, y);
      ctx.lineTo(deckRightEndX, y);
      ctx.stroke();

      // 光が流れるハイライト（架かりきった後にライン上を走る）
      if (buildProgress >= 0.99) {
        const cycle = (t * 0.18 + line.pulseOffset) % 1;
        const glowX = pierLeftX + (pierRightX - pierLeftX) * cycle;
        const glowAlpha = 0.9;
        const glowGrad = ctx.createRadialGradient(glowX, y, 0, glowX, y, w * 0.05);
        glowGrad.addColorStop(0, `rgba(255,225,160,${glowAlpha})`);
        glowGrad.addColorStop(1, 'rgba(255,225,160,0)');
        ctx.fillStyle = glowGrad;
        ctx.fillRect(glowX - w * 0.05, y - w * 0.05, w * 0.1, w * 0.1);

        reflectPoints.push({ x: glowX, glow: 1 });
      }
    });

    // 橋がまだ架かりきっていない間は、伸びている先端に軽い火花
    if (buildProgress < 0.99 && buildProgress > 0.01) {
      [deckLeftEndX, deckRightEndX].forEach((ex) => {
        ctx.fillStyle = 'rgba(255,230,180,0.8)';
        ctx.beginPath();
        ctx.arc(ex, bridgeTopY + (bridgeBottomY - bridgeTopY) * 0.45, 3, 0, Math.PI * 2);
        ctx.fill();
      });
    }

    drawWater(reflectPoints);

    raf = requestAnimationFrame(draw);
  }
  draw();

  return function stop() {
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', resize);
  };
}