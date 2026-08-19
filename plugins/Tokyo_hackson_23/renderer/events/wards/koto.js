export const key = 'koto';
export const label = '江東区：水彩都市・湾岸の光';

/**
 * 江東区の発見時処理
 */
export function onReveal(ward, ctx) {
  ctx.unlockBadge?.(`${ward.code}_first_visit`);
  ctx.playSound?.('reveal_common');
  ctx.showToast?.(`${ward.ward}「${ward.motif}」を引き当てました`);
}

/**
 * 江東区演出
 *
 * モチーフ：
 * - 水彩都市
 * - 川・運河
 * - 橋
 * - 湾岸都市
 *
 * Canvasの2D描画のみで構成。
 */
export function run(canvas) {
  const ctx = canvas.getContext('2d');

  let w;
  let h;
  let raf;
  let t = 0;

  const startTime = performance.now();
  const REVEAL_MS = 2200;

  const resize = () => {
    const dpr = window.devicePixelRatio || 1;

    w = canvas.clientWidth;
    h = canvas.clientHeight;

    canvas.width = w * dpr;
    canvas.height = h * dpr;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  };

  window.addEventListener('resize', resize);
  resize();

  function easeOutCubic(x) {
    return 1 - Math.pow(1 - x, 3);
  }

  // --------------------------------
  // 空
  // --------------------------------

  function drawSky(progress) {
    const grad = ctx.createLinearGradient(0, 0, 0, h * 0.65);

    grad.addColorStop(0, '#061522');
    grad.addColorStop(0.55, '#0b3345');
    grad.addColorStop(1, '#176078');

    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h * 0.65);

    // 湾岸の光
    for (let i = 0; i < 12; i++) {
      const x = (w / 12) * i;
      const y = h * 0.25 + Math.sin(i * 2.4) * h * 0.08;

      const glow = ctx.createRadialGradient(
        x,
        y,
        0,
        x,
        y,
        w * 0.04
      );

      glow.addColorStop(
        0,
        `rgba(120,220,240,${0.35 * progress})`
      );

      glow.addColorStop(
        1,
        'rgba(120,220,240,0)'
      );

      ctx.fillStyle = glow;

      ctx.fillRect(
        x - w * 0.05,
        y - w * 0.05,
        w * 0.1,
        w * 0.1
      );
    }
  }

  // --------------------------------
  // 水面
  // --------------------------------

  function drawWater() {
    const waterTop = h * 0.58;

    const grad = ctx.createLinearGradient(
      0,
      waterTop,
      0,
      h
    );

    grad.addColorStop(0, '#0b5268');
    grad.addColorStop(1, '#031018');

    ctx.fillStyle = grad;

    ctx.fillRect(
      0,
      waterTop,
      w,
      h - waterTop
    );

    // 波
    for (let layer = 0; layer < 5; layer++) {
      ctx.beginPath();

      const baseY =
        waterTop +
        layer * h * 0.08;

      ctx.moveTo(0, baseY);

      for (let x = 0; x <= w; x += 10) {
        const wave =
          Math.sin(
            x * 0.018 +
            t * (1 + layer * 0.3)
          ) *
          (3 + layer * 2);

        ctx.lineTo(
          x,
          baseY + wave
        );
      }

      ctx.strokeStyle =
        `rgba(100,210,225,${0.12 + layer * 0.04})`;

      ctx.lineWidth = 1;

      ctx.stroke();
    }
  }

  // --------------------------------
  // 橋
  // --------------------------------

  function drawBridge(progress) {
    const waterTop = h * 0.58;

    const bridgeY = h * 0.48;

    const left = w * 0.12;
    const right = w * 0.88;

    const center = w * 0.5;

    const currentLeft =
      left +
      (center - left) *
      progress;

    const currentRight =
      right -
      (right - center) *
      progress;

    // 橋脚
    ctx.fillStyle = 'rgba(20,45,55,0.95)';

    ctx.fillRect(
      left - w * 0.015,
      bridgeY,
      w * 0.03,
      waterTop - bridgeY
    );

    ctx.fillRect(
      right - w * 0.015,
      bridgeY,
      w * 0.03,
      waterTop - bridgeY
    );

    // 橋桁
    ctx.strokeStyle =
      'rgba(150,225,230,0.9)';

    ctx.lineWidth = 4;

    ctx.beginPath();

    ctx.moveTo(
      left,
      bridgeY
    );

    ctx.lineTo(
      currentLeft,
      bridgeY
    );

    ctx.stroke();

    ctx.beginPath();

    ctx.moveTo(
      right,
      bridgeY
    );

    ctx.lineTo(
      currentRight,
      bridgeY
    );

    ctx.stroke();

    // 光
    if (progress > 0.95) {
      const glowProgress =
        (t * 0.25) % 1;

      const glowX =
        left +
        (right - left) *
        glowProgress;

      const gradient =
        ctx.createRadialGradient(
          glowX,
          bridgeY,
          0,
          glowX,
          bridgeY,
          w * 0.06
        );

      gradient.addColorStop(
        0,
        'rgba(180,250,255,0.9)'
      );

      gradient.addColorStop(
        1,
        'rgba(180,250,255,0)'
      );

      ctx.fillStyle = gradient;

      ctx.fillRect(
        glowX - w * 0.06,
        bridgeY - w * 0.06,
        w * 0.12,
        w * 0.12
      );
    }
  }

  // --------------------------------
  // 湾岸のシルエット
  // --------------------------------

  function drawCity(progress) {
    const baseY = h * 0.58;

    const buildings = [
      { x: 0.10, width: 0.06, height: 0.16 },
      { x: 0.20, width: 0.05, height: 0.24 },
      { x: 0.30, width: 0.07, height: 0.13 },
      { x: 0.67, width: 0.06, height: 0.21 },
      { x: 0.77, width: 0.05, height: 0.30 },
      { x: 0.87, width: 0.07, height: 0.18 }
    ];

    buildings.forEach((building, index) => {
      const x = w * building.x;
      const width = w * building.width;
      const height = h * building.height;

      ctx.fillStyle =
        `rgba(8,25,35,${0.7 * progress})`;

      ctx.fillRect(
        x,
        baseY - height,
        width,
        height
      );

      // 窓
      for (
        let y = baseY - height + 10;
        y < baseY - 10;
        y += 14
      ) {
        ctx.fillStyle =
          `rgba(150,230,240,${0.18 + Math.sin(t * 2 + index) * 0.08})`;

        ctx.fillRect(
          x + width * 0.25,
          y,
          3,
          4
        );
      }
    });
  }

  // --------------------------------
  // メインループ
  // --------------------------------

  function draw() {
    t += 0.016;

    const elapsed =
      performance.now() - startTime;

    const progress =
      easeOutCubic(
        Math.min(1, elapsed / REVEAL_MS)
      );

    ctx.clearRect(
      0,
      0,
      w,
      h
    );

    drawSky(progress);
    drawCity(progress);
    drawBridge(progress);
    drawWater();

    raf = requestAnimationFrame(draw);
  }

  draw();

  // --------------------------------
  // 停止処理
  // --------------------------------

  return function stop() {
    cancelAnimationFrame(raf);

    window.removeEventListener(
      'resize',
      resize
    );
  };
}