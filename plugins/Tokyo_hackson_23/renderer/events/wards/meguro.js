export const key = 'meguro';
export const label = '目黒区：目黒川 桜灯演出';

/**
 * @param {object} ward - wardManifestのエントリ
 * @param {object} ctx  - 共通API
 *   例: { unlockBadge, playSound, showToast, setScore }
 */
export function onReveal(ward, ctx) {
  ctx.unlockBadge?.(`${ward.code}_first_visit`);
  ctx.playSound?.('reveal_common');
  ctx.showToast?.(`${ward.ward}「${ward.motif}」を引き当てました`);
}

/**
 * 目黒区の演出（Canvas型）
 *
 * モチーフ：
 * - 目黒川
 * - 桜
 * - 夜の水面
 * - 川沿いの街灯
 *
 * 演出：
 * 1. 暗い夜の背景が徐々に現れる
 * 2. 目黒川の水面が揺れ始める
 * 3. 川沿いの光が灯る
 * 4. 桜の花びらが上から舞い落ちる
 * 5. 水面に街灯と桜の光が反射する
 */
export function run(canvas) {
  const ctx = canvas.getContext('2d');

  let w;
  let h;
  let raf;
  let t = 0;

  const startTime = performance.now();
  const REVEAL_MS = 2200;

  // 花びら
  const petals = [];

  // 川沿いの光
  const lights = [];

  const resize = () => {
    const dpr = window.devicePixelRatio || 1;

    w = canvas.clientWidth;
    h = canvas.clientHeight;

    canvas.width = w * dpr;
    canvas.height = h * dpr;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    createPetals();
    createLights();
  };

  window.addEventListener('resize', resize);

  function random(min, max) {
    return min + Math.random() * (max - min);
  }

  function easeOutCubic(x) {
    return 1 - Math.pow(1 - x, 3);
  }

  // --------------------------------
  // 桜の花びらを生成
  // --------------------------------

  function createPetals() {
    petals.length = 0;

    const count = Math.max(
      35,
      Math.floor(w / 12)
    );

    for (let i = 0; i < count; i++) {
      petals.push({
        x: random(0, w),
        y: random(-h, h),
        size: random(3, 7),
        speed: random(0.4, 1.2),
        drift: random(0.3, 1.0),
        rotation: random(0, Math.PI * 2),
        rotationSpeed: random(-0.025, 0.025),
        phase: random(0, Math.PI * 2),
        alpha: random(0.45, 0.9)
      });
    }
  }

  // --------------------------------
  // 川沿いの街灯
  // --------------------------------

  function createLights() {
    lights.length = 0;

    const count = 10;

    for (let i = 0; i < count; i++) {
      lights.push({
        x: w * 0.08 + (w * 0.84 / (count - 1)) * i,
        y: h * 0.43 + Math.sin(i * 1.7) * h * 0.025,
        radius: random(3, 5),
        phase: random(0, Math.PI * 2)
      });
    }
  }

  // --------------------------------
  // 夜空
  // --------------------------------

  function drawSky(progress) {
    const grad = ctx.createLinearGradient(0, 0, 0, h * 0.65);

    grad.addColorStop(0, '#090b18');
    grad.addColorStop(0.45, '#15182b');
    grad.addColorStop(1, '#30243a');

    ctx.fillStyle = grad;
    ctx.globalAlpha = progress;
    ctx.fillRect(0, 0, w, h * 0.65);
    ctx.globalAlpha = 1;
  }

  // --------------------------------
  // 遠景の街
  // --------------------------------

  function drawCity(progress) {
    const baseY = h * 0.54;

    const buildings = [
      { x: 0.04, width: 0.09, height: 0.15 },
      { x: 0.16, width: 0.07, height: 0.22 },
      { x: 0.27, width: 0.10, height: 0.13 },
      { x: 0.68, width: 0.08, height: 0.18 },
      { x: 0.79, width: 0.07, height: 0.25 },
      { x: 0.90, width: 0.06, height: 0.15 }
    ];

    buildings.forEach((building, index) => {
      const x = w * building.x;
      const width = w * building.width;
      const height = h * building.height;

      ctx.fillStyle = `rgba(20,19,31,${0.8 * progress})`;
      ctx.fillRect(x, baseY - height, width, height);

      // 建物の窓
      for (let y = baseY - height + 10; y < baseY - 8; y += 13) {
        const flicker = 0.12 + Math.sin(t * 1.5 + index * 2.3 + y) * 0.04;
        ctx.fillStyle = `rgba(255,210,150,${flicker})`;
        ctx.fillRect(x + width * 0.25, y, 3, 4);
      }
    });
  }

  // --------------------------------
  // 目黒川
  // --------------------------------

  function drawRiver() {
    const riverTop = h * 0.55;

    const grad = ctx.createLinearGradient(0, riverTop, 0, h);

    grad.addColorStop(0, '#142b38');
    grad.addColorStop(0.5, '#0b202d');
    grad.addColorStop(1, '#050b12');

    ctx.fillStyle = grad;
    ctx.fillRect(0, riverTop, w, h - riverTop);

    // 水面の細かな波
    for (let layer = 0; layer < 7; layer++) {
      const y = riverTop + layer * h * 0.065;

      ctx.beginPath();
      ctx.moveTo(0, y);

      for (let x = 0; x <= w; x += 8) {
        const wave = Math.sin(x * 0.025 + t * (1.2 + layer * 0.15)) * (2 + layer * 0.8);
        ctx.lineTo(x, y + wave);
      }

      ctx.strokeStyle = `rgba(120,180,190,${0.08 + layer * 0.018})`;
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  }

  // --------------------------------
  // 川沿いの街灯
  // --------------------------------

  function drawLights() {
    lights.forEach((light, index) => {
      const pulse = 0.75 + Math.sin(t * 1.8 + light.phase) * 0.12;

      const glow = ctx.createRadialGradient(
        light.x, light.y, 0,
        light.x, light.y, w * 0.055
      );

      glow.addColorStop(0, `rgba(255,220,160,${pulse})`);
      glow.addColorStop(0.25, `rgba(255,190,120,${pulse * 0.4})`);
      glow.addColorStop(1, 'rgba(255,180,100,0)');

      ctx.fillStyle = glow;
      ctx.fillRect(light.x - w * 0.06, light.y - w * 0.06, w * 0.12, w * 0.12);

      // 水面への反射
      const riverTop = h * 0.55;

      for (let y = riverTop; y < h; y += 7) {
        const depth = (y - riverTop) / (h - riverTop);
        const sway = Math.sin(y * 0.055 + t * 1.7 + index) * 5 * depth;
        const alpha = pulse * (1 - depth) * 0.22;

        ctx.fillStyle = `rgba(255,205,140,${alpha})`;
        ctx.fillRect(light.x + sway - 1, y, 2, 4);
      }
    });
  }

  // --------------------------------
  // 桜の花びら
  // --------------------------------

  function drawPetals(progress) {
    petals.forEach((petal) => {
      petal.y += petal.speed;
      petal.x += Math.sin(t * petal.drift + petal.phase) * 0.5;
      petal.rotation += petal.rotationSpeed;

      if (petal.y > h + 20) {
        petal.y = -20;
        petal.x = random(0, w);
      }

      ctx.save();
      ctx.translate(petal.x, petal.y);
      ctx.rotate(petal.rotation);
      ctx.globalAlpha = petal.alpha * progress;

      // 花びら
      ctx.beginPath();
      ctx.moveTo(0, -petal.size);
      ctx.bezierCurveTo(petal.size, -petal.size * 0.5, petal.size, petal.size * 0.7, 0, petal.size);
      ctx.bezierCurveTo(-petal.size, petal.size * 0.7, -petal.size, -petal.size * 0.5, 0, -petal.size);
      
      ctx.fillStyle = 'rgba(255,190,210,0.85)';
      ctx.fill();
      ctx.restore();
    });

    ctx.globalAlpha = 1;
  }

  // --------------------------------
  // 川沿いの桜の枝
  // --------------------------------

  function drawBranches(progress) {
    const riverTop = h * 0.55;

    ctx.strokeStyle = `rgba(35,24,30,${0.8 * progress})`;
    ctx.lineWidth = 4;

    // 左側
    ctx.beginPath();
    ctx.moveTo(0, riverTop);
    ctx.quadraticCurveTo(w * 0.12, h * 0.40, w * 0.27, h * 0.34);
    ctx.stroke();

    // 右側
    ctx.beginPath();
    ctx.moveTo(w, riverTop);
    ctx.quadraticCurveTo(w * 0.87, h * 0.39, w * 0.73, h * 0.31);
    ctx.stroke();

    // 桜の小さな光
    const blossoms = [
      [0.12, 0.42], [0.18, 0.38], [0.24, 0.35],
      [0.78, 0.37], [0.84, 0.40], [0.72, 0.34]
    ];

    blossoms.forEach(([xRatio, yRatio], index) => {
      const x = w * xRatio;
      const y = h * yRatio;
      const pulse = 0.55 + Math.sin(t * 1.5 + index) * 0.2;

      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,190,215,${pulse})`;
      ctx.fill();
    });
  }

  // --------------------------------
  // メインループ
  // --------------------------------

  function draw() {
    t += 0.016;

    const elapsed = performance.now() - startTime;
    const progress = easeOutCubic(Math.min(1, elapsed / REVEAL_MS));

    ctx.clearRect(0, 0, w, h);

    drawSky(progress);
    drawCity(progress);
    drawRiver();
    drawBranches(progress);
    drawLights();
    drawPetals(progress);

    raf = requestAnimationFrame(draw);
  }
resize();
  draw();

  // --------------------------------
  // 停止処理
  // --------------------------------

  return function stop() {
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', resize);
  };
}