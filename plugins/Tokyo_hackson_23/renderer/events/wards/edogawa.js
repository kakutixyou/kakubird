// renderer/events/wards/edogawa.js
export const key = 'edogawa';
export const label = '江戸川区：川辺と観覧車の灯り - 花火きらめく水辺の夜';

/**
 * 江戸川区の演出（Canvas型）。
 * 広い川辺の空、対岸の街あかり、観覧車を想起するシルエット、
 * そして江戸川の花火を思わせる光で、
 * 江戸川区の「水辺の開放感とにぎわい」を表現する。
 *
 * ※ effectKey は 'edogawa' を想定。tokyoData.js 側も合わせてください。
 */
export function run(canvas) {
  const ctx = canvas.getContext('2d');
  let w, h, raf, t = 0;

  let clouds = [];
  let riverRipples = [];
  let skyline = [];
  let windowLights = [];
  let fireworks = [];
  let sparkleDots = [];
  let ferrisCabins = [];

  const generateScene = () => {
    const horizon = h * 0.53;
    const riverTop = h * 0.63;

    // 雲
    clouds = [];
    for (let i = 0; i < 6; i++) {
      clouds.push({
        y: h * (0.08 + i * 0.065),
        width: w * (0.2 + Math.random() * 0.24),
        height: h * (0.028 + Math.random() * 0.02),
        speed: 2 + Math.random() * 3.5,
        offset: Math.random() * w,
        alpha: 0.05 + Math.random() * 0.08,
      });
    }

    // 川のさざ波
    riverRipples = [];
    for (let i = 0; i < 13; i++) {
      riverRipples.push({
        y: riverTop + i * h * 0.021,
        amp: 2 + Math.random() * 4,
        freq: 0.010 + Math.random() * 0.011,
        phase: Math.random() * Math.PI * 2,
        alpha: 0.08 + i * 0.01,
      });
    }

    // 対岸の街並み
    skyline = [];
    let x = -20;
    while (x < w + 20) {
      const bw = w * (0.016 + Math.random() * 0.038);
      const bh = h * (0.05 + Math.random() * 0.16);
      skyline.push({ x, w: bw, h: bh });
      x += bw + Math.random() * 4;
    }

    // 窓あかり
    windowLights = [];
    skyline.forEach(b => {
      const cols = Math.max(1, Math.floor(b.w / 8));
      const rows = Math.max(1, Math.floor(b.h / 10));
      for (let c = 0; c < cols; c++) {
        for (let r = 0; r < rows; r++) {
          if (Math.random() > 0.84) {
            windowLights.push({
              x: b.x + 3 + c * 8,
              y: horizon + h * 0.03 - b.h + 5 + r * 10,
              phase: Math.random() * Math.PI * 2,
            });
          }
        }
      }
    });

    // 花火
    fireworks = [];
    for (let i = 0; i < 6; i++) {
      fireworks.push(spawnFirework(true));
    }

    // 水面のきらめき
    sparkleDots = [];
    for (let i = 0; i < 34; i++) {
      sparkleDots.push({
        x: Math.random() * w,
        y: h * (0.68 + Math.random() * 0.22),
        phase: Math.random() * Math.PI * 2,
        drift: 8 + Math.random() * 14,
      });
    }

    // 観覧車ゴンドラ（回転用）
    ferrisCabins = [];
    for (let i = 0; i < 12; i++) {
      ferrisCabins.push({
        a: (i / 12) * Math.PI * 2,
        color: i % 2 ? '#ffd39a' : '#ffc27a',
      });
    }
  };

  function spawnFirework(initial = false) {
    return {
      x: w * (0.28 + Math.random() * 0.6),
      y: h * (0.14 + Math.random() * 0.26),
      r: 10 + Math.random() * 20,
      life: initial ? Math.random() : 0,
      speed: 0.22 + Math.random() * 0.2,
      hue: [20, 35, 48, 330, 200][Math.floor(Math.random() * 5)],
    };
  }

  const resize = () => {
    w = canvas.width = canvas.clientWidth;
    h = canvas.height = canvas.clientHeight;
    if (w > 0 && h > 0) generateScene();
  };
  window.addEventListener('resize', resize);
  resize();

  function drawSky() {
    const horizon = h * 0.53;
    const grad = ctx.createLinearGradient(0, 0, 0, horizon);
    grad.addColorStop(0, '#1f2f58');
    grad.addColorStop(0.34, '#3f628f');
    grad.addColorStop(0.66, '#e0895f');
    grad.addColorStop(1, '#ffd7ad');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, horizon);

    // 夕日
    const sx = w * 0.7;
    const sy = horizon - h * 0.03;
    const sr = Math.min(w, h) * 0.058;
    ctx.save();
    ctx.shadowBlur = 50 + Math.sin(t * 1.3) * 7;
    ctx.shadowColor = 'rgba(255,198,130,0.8)';
    ctx.fillStyle = '#ffe9cc';
    ctx.beginPath();
    ctx.arc(sx, sy, sr, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // 雲
    clouds.forEach(c => {
      const x = (c.offset + t * c.speed * 10) % (w + c.width) - c.width;
      const g = ctx.createLinearGradient(x, c.y, x + c.width, c.y);
      g.addColorStop(0, 'rgba(255,235,220,0)');
      g.addColorStop(0.5, `rgba(255,235,220,${c.alpha})`);
      g.addColorStop(1, 'rgba(255,235,220,0)');
      ctx.fillStyle = g;
      ctx.fillRect(x, c.y, c.width, c.height);
    });
  }

  function drawSkyline() {
    const horizon = h * 0.53;

    // 対岸シルエット
    ctx.fillStyle = 'rgba(28,23,34,0.58)';
    skyline.forEach(b => {
      ctx.fillRect(b.x, horizon + h * 0.03 - b.h, b.w, b.h);
    });

    // 窓明かり
    windowLights.forEach(l => {
      const a = 0.35 + (Math.sin(t * 3 + l.phase) * 0.3 + 0.3);
      ctx.fillStyle = `rgba(255,215,155,${a})`;
      ctx.fillRect(l.x, l.y, 3, 4);
    });
  }

  function drawRiver() {
    const riverTop = h * 0.63;

    // 川面
    const rg = ctx.createLinearGradient(0, riverTop, 0, h);
    rg.addColorStop(0, '#496785');
    rg.addColorStop(0.48, '#35536e');
    rg.addColorStop(1, '#223f58');
    ctx.fillStyle = rg;
    ctx.fillRect(0, riverTop, w, h - riverTop);

    // 夕日の反射
    const reflection = ctx.createLinearGradient(w * 0.7, riverTop, w * 0.7, h);
    reflection.addColorStop(0, 'rgba(255,222,182,0.3)');
    reflection.addColorStop(1, 'rgba(255,222,182,0)');
    ctx.fillStyle = reflection;
    ctx.fillRect(w * 0.61, riverTop, w * 0.18, h - riverTop);

    // 波
    riverRipples.forEach(r => {
      ctx.strokeStyle = `rgba(220,236,255,${r.alpha})`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let x = 0; x <= w; x += 8) {
        const y = r.y + Math.sin(x * r.freq + t * 2 + r.phase) * r.amp;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    });

    // きらめき
    sparkleDots.forEach(s => {
      const x = s.x + Math.cos(t * 0.8 + s.phase) * s.drift * 0.2;
      const y = s.y + Math.sin(t * 1.1 + s.phase) * 2.5;
      const a = 0.18 + (Math.sin(t * 2.5 + s.phase) * 0.24 + 0.24);
      ctx.fillStyle = `rgba(255,230,185,${a})`;
      ctx.beginPath();
      ctx.arc(x, y, 1.8, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  function drawFerrisWheel() {
    // 葛西臨海公園の観覧車を想起させる抽象モチーフ
    const cx = w * 0.18;
    const cy = h * 0.60;
    const rr = Math.min(w, h) * 0.13;
    const rot = t * 0.12;

    ctx.save();

    // 支柱
    ctx.strokeStyle = 'rgba(80,70,78,0.6)';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(cx - rr * 0.35, h * 0.76);
    ctx.lineTo(cx, cy + rr * 0.25);
    ctx.lineTo(cx + rr * 0.35, h * 0.76);
    ctx.stroke();

    // 輪
    ctx.strokeStyle = 'rgba(230,235,240,0.35)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(cx, cy, rr, 0, Math.PI * 2);
    ctx.stroke();

    // スポーク
    for (let i = 0; i < 8; i++) {
      const a = (i / 8) * Math.PI * 2 + rot;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr);
      ctx.stroke();
    }

    // ゴンドラ
    ferrisCabins.forEach(c => {
      const a = c.a + rot;
      const gx = cx + Math.cos(a) * rr;
      const gy = cy + Math.sin(a) * rr;
      const flick = 0.45 + Math.sin(t * 3 + c.a * 4) * 0.2;
      ctx.fillStyle = `rgba(255,220,165,${flick})`;
      ctx.beginPath();
      ctx.arc(gx, gy, 3, 0, Math.PI * 2);
      ctx.fill();
    });

    ctx.restore();
  }

  function drawFireworks() {
    fireworks.forEach((f, i) => {
      f.life += f.speed * 0.016 * 60;
      const p = (Math.sin(f.life * Math.PI) + 1) / 2;
      const r = f.r * (0.55 + p);

      ctx.save();
      ctx.translate(f.x, f.y);

      for (let k = 0; k < 16; k++) {
        const a = (k / 16) * Math.PI * 2 + f.life * 0.6;
        const ex = Math.cos(a) * r;
        const ey = Math.sin(a) * r;
        ctx.strokeStyle = `hsla(${f.hue}, 92%, 72%, ${0.08 + p * 0.26})`;
        ctx.lineWidth = 1.4;
        ctx.beginPath();
        ctx.moveTo(ex * 0.45, ey * 0.45);
        ctx.lineTo(ex, ey);
        ctx.stroke();
      }

      ctx.restore();

      if (f.life > 1.2) fireworks[i] = spawnFirework(false);
    });
  }

  function drawLevee() {
    // 手前の河川敷
    ctx.fillStyle = '#2e4b30';
    ctx.beginPath();
    ctx.moveTo(0, h);
    ctx.lineTo(0, h * 0.82);
    ctx.quadraticCurveTo(w * 0.25, h * 0.77, w * 0.52, h * 0.83);
    ctx.quadraticCurveTo(w * 0.8, h * 0.89, w, h * 0.84);
    ctx.lineTo(w, h);
    ctx.closePath();
    ctx.fill();
  }

  function drawUI() {
    ctx.save();
    ctx.font = `bold italic ${h * 0.04}px "Arial Black", Impact, sans-serif`;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';

    ctx.shadowBlur = 10;
    ctx.shadowColor = '#ffd8ad';
    ctx.fillStyle = '#ffffff';
    ctx.fillText('EDG-01', w * 0.96, h * 0.98);

    ctx.shadowBlur = 0;
    ctx.fillStyle = '#ffd8ad';
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
    drawSkyline();
    drawRiver();
    drawFerrisWheel();
    drawFireworks();
    drawLevee();
    drawUI();

    raf = requestAnimationFrame(draw);
  }
  draw();

  return function stop() {
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', resize);
  };
}