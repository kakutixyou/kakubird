// suginami.js
// 杉並区：アニメと食文化が織りなす下北・高円寺の夜（アニメミュージアム × ラーメン激戦区）
export const key = 'suginami';
export const label = '杉並区：アニメと食文化が織りなす下北・高円寺の夜（アニメミュージアム × ラーメン激戦区）';

// 使い方: import { run } from './suginami.js';
// const stop = run(canvas); // 停めるときは stop();

export function run(canvas) {
  if (!canvas || !(canvas instanceof HTMLCanvasElement)) {
    throw new Error('run: canvas element required');
  }
  const ctx = canvas.getContext('2d');
  const DPR = window.devicePixelRatio || 1;
  let w = 0, h = 0;
  let raf = null;
  let t = 0;

  // オブジェクト
  const stars = [];
  const cels = [];
  const steams = [];
  const buildings = [];

  function resizeCanvas() {
    const cw = Math.max(1, canvas.clientWidth);
    const ch = Math.max(1, canvas.clientHeight);
    w = Math.floor(cw);
    h = Math.floor(ch);
    canvas.width = Math.floor(w * DPR);
    canvas.height = Math.floor(h * DPR);
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  }

  function rand(a, b) { return a + Math.random() * (b - a); }
  function choice(arr) { return arr[Math.floor(Math.random() * arr.length)]; }

  function initStars() {
    stars.length = 0;
    const count = Math.max(30, Math.floor((w * h) / 60000));
    for (let i = 0; i < count; i++) {
      stars.push({
        x: Math.random() * w,
        y: Math.random() * h * 0.45,
        r: rand(0.3, 1.6),
        phase: Math.random() * Math.PI * 2,
        speed: rand(0.0005, 0.002)
      });
    }
  }

  function initCels() {
    cels.length = 0;
    const count = Math.max(10, Math.floor(w / 120));
    for (let i = 0; i < count; i++) {
      cels.push({
        x: rand(0, w),
        y: rand(h * 0.5, h * 0.85),
        w: rand(48, 120),
        h: rand(28, 72),
        rot: rand(-0.4, 0.4),
        vx: rand(-10, 10),
        vy: rand(-6, -24),
        hue: rand(200, 320),
        alpha: rand(0.3, 0.9)
      });
    }
  }

  function initSteams() {
    steams.length = 0;
    const shopCount = 3;
    for (let i = 0; i < shopCount; i++) {
      const baseX = w * (0.15 + i * (0.7 / Math.max(1, shopCount - 1)));
      for (let j = 0; j < 6; j++) {
        steams.push({
          baseX: baseX + rand(-18, 18),
          baseY: h * 0.82 + rand(-8, 8),
          t: Math.random() * 2,
          speed: rand(0.3, 0.9),
          size: rand(8, 22),
          life: rand(2, 4),
          drift: rand(-10, 10)
        });
      }
    }
  }

  function initBuildings() {
    buildings.length = 0;
    const count = Math.max(12, Math.floor(w / 100));
    for (let i = 0; i < count; i++) {
      const bw = rand(0.06, 0.18) * w;
      const bh = rand(0.18, 0.6) * h;
      buildings.push({
        x: (i / count),
        w: bw,
        h: bh,
        pattern: generateWindowPattern(Math.ceil(bh / 14), Math.ceil(bw / 24))
      });
    }
  }

  function generateWindowPattern(rows, cols) {
    const pat = [];
    for (let r = 0; r < rows; r++) {
      const row = [];
      for (let c = 0; c < cols; c++) {
        if (Math.random() > 0.65) {
          const r0 = Math.random();
          row.push(r0 > 0.75 ? 'rgba(200,230,255,0.95)' : (r0 > 0.5 ? 'rgba(255,230,160,0.95)' : 'rgba(255,250,220,0.9)'));
        } else {
          row.push(null);
        }
      }
      pat.push(row);
    }
    return pat;
  }

  function initAll() {
    resizeCanvas();
    initStars();
    initCels();
    initSteams();
    initBuildings();
  }

  // 描画パーツ
  function drawSky() {
    const g = ctx.createLinearGradient(0, 0, 0, h);
    g.addColorStop(0, '#050417');
    g.addColorStop(0.5, '#0a1130');
    g.addColorStop(1, '#0d1624');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);
  }

  function drawStars(dt) {
    for (const s of stars) {
      s.phase += s.speed * dt;
      const a = 0.6 + 0.4 * Math.sin(s.phase * 3);
      ctx.fillStyle = `rgba(255,255,255,${a})`;
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r * (1 + 0.6 * Math.sin(s.phase * 2)), 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function drawCitySilhouette() {
    const base = h * 0.25;
    ctx.save();
    ctx.translate(0, h);
    ctx.scale(1, -1);
    ctx.beginPath();
    ctx.moveTo(0, base);
    const blocks = Math.max(6, Math.floor(w / 120));
    for (let i = 0; i <= blocks; i++) {
      const bx = (i / blocks) * w;
      const bh = rand(20, 120);
      ctx.lineTo(bx, base + bh);
    }
    ctx.lineTo(w, base);
    ctx.lineTo(w, 0);
    ctx.lineTo(0, 0);
    ctx.closePath();
    const g = ctx.createLinearGradient(0, 0, 0, h * 0.6);
    g.addColorStop(0, 'rgba(10,12,20,0.96)');
    g.addColorStop(1, 'rgba(10,12,20,0.7)');
    ctx.fillStyle = g;
    ctx.fill();
    ctx.restore();
  }

  // アニメーションミュージアムの屋上フィルム（回転する丸）
  let filmAngle = 0;
  function drawAnimationMuseum(dt) {
    const cx = w * 0.2;
    const cy = h * 0.62;
    const bw = Math.min(160, w * 0.18);
    const bh = bw * 0.6;
    // 建物
    ctx.fillStyle = '#141722';
    ctx.fillRect(cx - bw/2, cy - bh/2, bw, bh);
    // 窓（簡易）
    ctx.fillStyle = 'rgba(250,230,200,0.85)';
    ctx.fillRect(cx - bw/4, cy - bh/6, bw/2, bh/6);
    // 屋上フィルム
    ctx.save();
    filmAngle += dt * 0.0005;
    ctx.translate(cx, cy - bh/2 - 10);
    ctx.rotate(filmAngle);
    const r = Math.min(32, bw * 0.16);
    ctx.fillStyle = 'rgba(240,220,110,0.95)';
    ctx.beginPath();
    ctx.arc(0, 0, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = 'rgba(28,28,36,0.95)';
    for (let i = 0; i < 5; i++) {
      ctx.beginPath();
      ctx.arc(Math.cos(i * Math.PI * 2 / 5) * r * 0.6, Math.sin(i * Math.PI * 2 / 5) * r * 0.6, r * 0.2, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  function drawFloatingCels(dt) {
    for (const c of cels) {
      c.x += c.vx * dt * 0.001;
      c.y += c.vy * dt * 0.001;
      c.rot += (c.vx * 0.001) * 0.02;
      c.alpha += Math.sin((t * 0.002) + c.rot * 2) * 0.002;
      if (c.y + c.h < 0 || c.x < -200 || c.x > w + 200) {
        c.x = rand(0, w);
        c.y = rand(h * 0.55, h * 0.85);
        c.vx = rand(-10, 10);
        c.vy = rand(-6, -20);
      }
      ctx.save();
      ctx.translate(c.x, c.y);
      ctx.rotate(c.rot);
      ctx.globalAlpha = Math.max(0.06, Math.min(1, c.alpha)) * 0.95;
      ctx.fillStyle = `hsla(${c.hue},70%,60%,0.06)`;
      ctx.fillRect(-c.w/2, -c.h/2, c.w, c.h);
      ctx.strokeStyle = `hsla(${c.hue - 20},80%,30%,${0.9})`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(-c.w/2 + 6, -c.h/6);
      ctx.quadraticCurveTo(0, -c.h/2, c.w/2 - 6, -c.h/6);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(-c.w/4, c.h/6);
      ctx.quadraticCurveTo(0, c.h/2, c.w/4, c.h/6);
      ctx.stroke();
      ctx.restore();
    }
  }

  function drawRamenStreet(dt) {
    const baseY = h * 0.82;
    const shops = 3;
    for (let i = 0; i < shops; i++) {
      const sx = w * (0.12 + i * (0.76 / Math.max(1, shops - 1)));
      const shopW = Math.min(160, w * 0.22);
      const shopH = Math.min(110, h * 0.12);
      ctx.fillStyle = 'rgba(48,30,18,0.95)';
      ctx.fillRect(sx - shopW/2, baseY - shopH, shopW, shopH);
      // のれん
      ctx.fillStyle = 'rgba(180,60,50,0.96)';
      const norenW = shopW * 0.9;
      const norenH = shopH * 0.34;
      ctx.fillRect(sx - norenW/2, baseY - norenH - 8, norenW, norenH);
      ctx.fillStyle = 'rgba(255,255,255,0.92)';
      ctx.font = `${Math.max(10, Math.floor(norenH * 0.46))}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('ラーメン', sx, baseY - norenH/2 - 8);
      // 器と湯気
      ctx.fillStyle = 'rgba(34,20,12,1)';
      ctx.fillRect(sx - 18, baseY - 16, 36, 12);
      ctx.beginPath();
      ctx.ellipse(sx, baseY - 22, 22, 10, 0, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(240,220,180,0.98)';
      ctx.fill();
    }
  }

  function drawSteams(dt) {
    for (const s of steams) {
      s.t += s.speed * dt * 0.001;
      if (s.t > s.life) {
        s.t = 0;
        s.baseX += rand(-8, 8);
        s.size = rand(8, 22);
      }
      const p = s.t / s.life;
      const x = s.baseX + s.drift * p;
      const y = s.baseY - p * (60 + s.size * 2);
      const alpha = Math.max(0, 0.8 * (1 - p));
      const rad = s.size * (0.5 + p * 0.9);
      const g = ctx.createRadialGradient(x, y, rad * 0.1, x, y, rad);
      g.addColorStop(0, `rgba(255,255,255,${0.26 * alpha})`);
      g.addColorStop(1, `rgba(200,200,200,0)`);
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.ellipse(x, y, rad, rad * 0.6, p, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function drawBuildings(dt) {
    const baseY = h * 0.92;
    const scroll = (t * 0.0008) % 1;
    buildings.forEach((b) => {
      const bx = (((b.x - scroll) % 1) + 1) % 1 * w;
      const bw = b.w;
      const bh = b.h;
      const by = baseY - bh;
      ctx.fillStyle = '#0f1016';
      ctx.fillRect(bx, by, bw, bh);
      // 窓
      const winW = Math.max(1.4, bw * 0.035);
      const winH = Math.max(3, bh * 0.012);
      const gapX = winW * 2.6;
      const gapY = winH * 2.4;
      const cols = Math.min(b.pattern[0].length, Math.floor(bw / gapX));
      const rows = Math.min(b.pattern.length, Math.floor(bh / gapY));
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          if (b.pattern[r][c]) {
            ctx.fillStyle = b.pattern[r][c];
            ctx.fillRect(bx + winW + c * gapX, by + winH + r * gapY, winW, winH);
          }
        }
      }
    });
  }

  function drawForeground(dt) {
    // 前景の色味反射（柔らかく）
    ctx.save();
    ctx.globalAlpha = 0.06;
    const grad = ctx.createLinearGradient(0, h * 0.6, 0, h);
    grad.addColorStop(0, '#ff7a4d');
    grad.addColorStop(1, '#2ea6ff');
    ctx.fillStyle = grad;
    ctx.fillRect(0, h * 0.6, w, h * 0.4);
    ctx.restore();
  }

  // ループ
  let last = performance.now();
  function loop(now) {
    const dt = now - last;
    last = now;
    t += dt;
    // 背景
    drawSky();
    drawStars(dt);
    drawCitySilhouette();
    drawBuildings(dt);
    drawAnimationMuseum(dt);
    drawFloatingCels(dt);
    drawRamenStreet(dt);
    drawSteams(dt);
    drawForeground(dt);
    raf = requestAnimationFrame(loop);
  }

  // 初期化と開始
  initAll();
  window.addEventListener('resize', onWindowResize);
  function onWindowResize() {
    initAll();
  }
  last = performance.now();
  raf = requestAnimationFrame(loop);

  // 停止関数を返す
  return function stop() {
    if (raf) cancelAnimationFrame(raf);
    window.removeEventListener('resize', onWindowResize);
  };
}