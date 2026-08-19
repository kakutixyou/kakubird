// renderer/events/wards/arakawa.js
export const key = 'arakawa';
export const label = '荒川区：都電と水辺の夕暮れ - 下町を走る光の路';

/**
 * 荒川区の演出（Canvas型）。
 * 荒川・隅田川の水辺を想起させる夕空、下町の家並み、
 * そして都電荒川線（東京さくらトラム）をモチーフにした
 * 小さな車両の往来で、荒川区らしい日常の温かさを描く。
 *
 * ※ effectKey は 'arakawa' を想定。tokyoData.js 側も合わせてください。
 */
export function run(canvas) {
  const ctx = canvas.getContext('2d');
  let w, h, raf, t = 0;

  let clouds = [];
  let rippleBands = [];
  let houses = [];
  let windowsLit = [];
  let sparkles = [];
  let tramCars = [];

  const generateScene = () => {
    const horizon = h * 0.54;
    const waterTop = h * 0.64;

    clouds = [];
    for (let i = 0; i < 5; i++) {
      clouds.push({
        y: h * (0.10 + i * 0.07),
        width: w * (0.18 + Math.random() * 0.26),
        height: h * (0.03 + Math.random() * 0.02),
        speed: 2 + Math.random() * 3,
        offset: Math.random() * w,
        alpha: 0.06 + Math.random() * 0.08,
      });
    }

    rippleBands = [];
    for (let i = 0; i < 11; i++) {
      rippleBands.push({
        y: waterTop + i * h * 0.024,
        amp: 2 + Math.random() * 4,
        freq: 0.012 + Math.random() * 0.01,
        phase: Math.random() * Math.PI * 2,
        alpha: 0.08 + i * 0.012,
      });
    }

    houses = [];
    let x = -30;
    while (x < w + 30) {
      const bw = w * (0.024 + Math.random() * 0.042);
      const bh = h * (0.045 + Math.random() * 0.13);
      houses.push({ x, w: bw, h: bh });
      x += bw + Math.random() * 5;
    }

    windowsLit = [];
    houses.forEach(b => {
      const cols = Math.max(1, Math.floor(b.w / 9));
      const rows = Math.max(1, Math.floor(b.h / 11));
      for (let c = 0; c < cols; c++) {
        for (let r = 0; r < rows; r++) {
          if (Math.random() > 0.84) {
            windowsLit.push({
              x: b.x + 4 + c * 9,
              y: horizon + h * 0.03 - b.h + 6 + r * 11,
              phase: Math.random() * Math.PI * 2,
            });
          }
        }
      }
    });

    sparkles = [];
    for (let i = 0; i < 26; i++) {
      sparkles.push({
        x: Math.random() * w,
        y: h * (0.68 + Math.random() * 0.22),
        phase: Math.random() * Math.PI * 2,
        drift: 5 + Math.random() * 12,
      });
    }

    // 都電風の車両（2編成）
    tramCars = [
      { base: 0.10, speed: 0.018, color: '#7a3d2f', phase: 0 },
      { base: 0.78, speed: -0.014, color: '#6d2f25', phase: Math.PI * 0.8 },
    ];
  };

  const resize = () => {
    w = canvas.width = canvas.clientWidth;
    h = canvas.height = canvas.clientHeight;
    if (w > 0 && h > 0) generateScene();
  };
  window.addEventListener('resize', resize);
  resize();

  function drawSky() {
    const horizon = h * 0.54;
    const grad = ctx.createLinearGradient(0, 0, 0, horizon);
    grad.addColorStop(0, '#263761');
    grad.addColorStop(0.34, '#516c96');
    grad.addColorStop(0.68, '#f09a69');
    grad.addColorStop(1, '#ffd9ad');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, horizon);

    // 夕陽
    const sx = w * 0.70;
    const sy = horizon - h * 0.035;
    const sr = Math.min(w, h) * 0.055;
    ctx.save();
    ctx.shadowBlur = 45 + Math.sin(t * 1.2) * 6;
    ctx.shadowColor = 'rgba(255,200,130,0.82)';
    ctx.fillStyle = '#ffe8c9';
    ctx.beginPath();
    ctx.arc(sx, sy, sr, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // 雲
    clouds.forEach(c => {
      const x = (c.offset + t * c.speed * 10) % (w + c.width) - c.width;
      const g = ctx.createLinearGradient(x, c.y, x + c.width, c.y);
      g.addColorStop(0, 'rgba(255,230,210,0)');
      g.addColorStop(0.5, `rgba(255,230,210,${c.alpha})`);
      g.addColorStop(1, 'rgba(255,230,210,0)');
      ctx.fillStyle = g;
      ctx.fillRect(x, c.y, c.width, c.height);
    });
  }

  function drawTownAndTracks() {
    const horizon = h * 0.54;

    // 下町シルエット
    ctx.fillStyle = 'rgba(30,25,35,0.56)';
    houses.forEach(b => {
      ctx.fillRect(b.x, horizon + h * 0.03 - b.h, b.w, b.h);

      // 屋根
      ctx.beginPath();
      ctx.moveTo(b.x - 1, horizon + h * 0.03 - b.h);
      ctx.lineTo(b.x + b.w * 0.5, horizon + h * 0.03 - b.h - h * 0.015);
      ctx.lineTo(b.x + b.w + 1, horizon + h * 0.03 - b.h);
      ctx.closePath();
      ctx.fill();
    });

    // 窓の灯り
    windowsLit.forEach(l => {
      const a = 0.35 + (Math.sin(t * 3 + l.phase) * 0.3 + 0.3);
      ctx.fillStyle = `rgba(255,214,150,${a})`;
      ctx.fillRect(l.x, l.y, 3, 4);
    });

    // 軌道（都電）
    const trackY = h * 0.74;
    ctx.strokeStyle = 'rgba(90,70,70,0.75)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, trackY);
    ctx.lineTo(w, trackY);
    ctx.moveTo(0, trackY + h * 0.03);
    ctx.lineTo(w, trackY + h * 0.03);
    ctx.stroke();

    // 枕木
    ctx.strokeStyle = 'rgba(75,58,55,0.55)';
    ctx.lineWidth = 1.2;
    for (let x = -10; x < w + 10; x += 16) {
      ctx.beginPath();
      ctx.moveTo(x, trackY - 1);
      ctx.lineTo(x + 7, trackY + h * 0.031);
      ctx.stroke();
    }

    // 架線ポール風
    ctx.strokeStyle = 'rgba(65,55,58,0.45)';
    ctx.lineWidth = 1;
    for (let x = 20; x < w; x += 90) {
      ctx.beginPath();
      ctx.moveTo(x, trackY - h * 0.12);
      ctx.lineTo(x, trackY - h * 0.005);
      ctx.stroke();
    }
    ctx.beginPath();
    ctx.moveTo(0, trackY - h * 0.12);
    ctx.lineTo(w, trackY - h * 0.12);
    ctx.stroke();
  }

  function drawRiver() {
    const waterTop = h * 0.64;

    const rg = ctx.createLinearGradient(0, waterTop, 0, h);
    rg.addColorStop(0, '#4b6788');
    rg.addColorStop(0.45, '#35536f');
    rg.addColorStop(1, '#243f58');
    ctx.fillStyle = rg;
    ctx.fillRect(0, waterTop, w, h - waterTop);

    // 夕陽反射
    const reflectGrad = ctx.createLinearGradient(w * 0.70, waterTop, w * 0.70, h);
    reflectGrad.addColorStop(0, 'rgba(255,220,175,0.28)');
    reflectGrad.addColorStop(1, 'rgba(255,220,175,0)');
    ctx.fillStyle = reflectGrad;
    ctx.fillRect(w * 0.61, waterTop, w * 0.18, h - waterTop);

    rippleBands.forEach(rp => {
      ctx.strokeStyle = `rgba(220,235,255,${rp.alpha})`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let x = 0; x <= w; x += 8) {
        const y = rp.y + Math.sin(x * rp.freq + t * 2 + rp.phase) * rp.amp;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    });

    // 水面のきらめき
    sparkles.forEach(sp => {
      const x = sp.x + Math.cos(t * 0.8 + sp.phase) * sp.drift * 0.22;
      const y = sp.y + Math.sin(t * 1.1 + sp.phase) * 2;
      const a = 0.2 + (Math.sin(t * 2.4 + sp.phase) * 0.25 + 0.25);
      ctx.fillStyle = `rgba(255,230,185,${a})`;
      ctx.beginPath();
      ctx.arc(x, y, 1.7, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  function drawTram() {
    const y = h * 0.705;
    tramCars.forEach((car, i) => {
      const px = ((car.base + t * car.speed) % 1 + 1) % 1; // 0..1 ループ
      const x = px * (w + 120) - 60;
      const bodyW = w * 0.10;
      const bodyH = h * 0.045;

      // 本体
      ctx.save();
      ctx.fillStyle = car.color;
      ctx.fillRect(x, y, bodyW, bodyH);

      // 上部帯
      ctx.fillStyle = 'rgba(255,232,210,0.75)';
      ctx.fillRect(x, y + bodyH * 0.10, bodyW, bodyH * 0.18);

      // 窓
      for (let k = 0; k < 4; k++) {
        const wx = x + bodyW * (0.12 + k * 0.2);
        const flick = 0.45 + (Math.sin(t * 4 + i + k) * 0.25 + 0.25);
        ctx.fillStyle = `rgba(255,220,165,${flick})`;
        ctx.fillRect(wx, y + bodyH * 0.36, bodyW * 0.12, bodyH * 0.28);
      }

      // ヘッド/テールライト
      const frontX = car.speed > 0 ? x + bodyW : x;
      ctx.fillStyle = 'rgba(255,240,190,0.85)';
      ctx.beginPath();
      ctx.arc(frontX, y + bodyH * 0.55, 2, 0, Math.PI * 2);
      ctx.fill();

      // 車輪影
      ctx.fillStyle = 'rgba(20,20,20,0.5)';
      ctx.fillRect(x + bodyW * 0.15, y + bodyH, bodyW * 0.12, 3);
      ctx.fillRect(x + bodyW * 0.72, y + bodyH, bodyW * 0.12, 3);

      ctx.restore();
    });
  }

  function drawUI() {
    ctx.save();
    ctx.font = `bold italic ${h * 0.04}px "Arial Black", Impact, sans-serif`;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';

    ctx.shadowBlur = 10;
    ctx.shadowColor = '#ffd3a8';
    ctx.fillStyle = '#ffffff';
    ctx.fillText('ARK-01', w * 0.96, h * 0.98);

    ctx.shadowBlur = 0;
    ctx.fillStyle = '#ffd3a8';
    ctx.fillRect(w * 0.965, h * 0.94, w * 0.015, h * 0.04);
    ctx.restore();
  }

  function draw() {
    t += 0.016;
    if (w === 0 || h === 0) {
      raf = requestAnimationFrame(draw);
      return;
    }

    ctx.clearRect(0, 0, w, h);

    drawSky();
    drawRiver();
    drawTownAndTracks();
    drawTram();
    drawUI();

    raf = requestAnimationFrame(draw);
  }
  draw();

  return function stop() {
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', resize);
  };
}