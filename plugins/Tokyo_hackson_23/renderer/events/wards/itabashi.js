// renderer/events/wards/itabashi.js
export const key = 'itabashi';
export const label = '板橋区：川風と祭りの灯り - 区民まつりでつながる街';

/**
 * 板橋区の演出（Canvas型）。
 * 荒川の土手を思わせる広い空と水辺、住宅地の落ち着いた明かりに、
 * 「板橋区民まつり」をイメージした提灯とやさしい賑わいを重ねた情景。
 * 日常の穏やかさと、地域イベントの高揚感が同居する板橋らしさを描く。
 *
 * ※ effectKey は 'itabashi' を想定。tokyoData.js 側も合わせてください。
 */
export function run(canvas) {
  const ctx = canvas.getContext('2d');
  let w, h, raf, t = 0;

  let clouds = [];
  let riverRipples = [];
  let skyline = [];
  let windowLights = [];
  let grassBlades = [];
  let lanterns = [];
  let confetti = [];
  let festivalGlow = [];

  const generateScene = () => {
    const horizon = h * 0.54;
    const riverTop = h * 0.64;

    // 空の雲帯
    clouds = [];
    for (let i = 0; i < 6; i++) {
      clouds.push({
        y: h * (0.08 + i * 0.065),
        width: w * (0.2 + Math.random() * 0.25),
        height: h * (0.028 + Math.random() * 0.02),
        speed: 1.8 + Math.random() * 3.2,
        offset: Math.random() * w,
        alpha: 0.05 + Math.random() * 0.08,
      });
    }

    // 川面の波
    riverRipples = [];
    for (let i = 0; i < 12; i++) {
      riverRipples.push({
        y: riverTop + i * h * 0.022,
        amp: 2 + Math.random() * 4,
        freq: 0.010 + Math.random() * 0.012,
        phase: Math.random() * Math.PI * 2,
        alpha: 0.08 + i * 0.01,
      });
    }

    // 街並みシルエット
    skyline = [];
    let x = -20;
    while (x < w + 20) {
      const bw = w * (0.018 + Math.random() * 0.04);
      const bh = h * (0.05 + Math.random() * 0.16);
      skyline.push({ x, w: bw, h: bh });
      x += bw + Math.random() * 5;
    }

    // 窓明かり
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

    // 土手の草
    grassBlades = [];
    for (let i = 0; i < 170; i++) {
      grassBlades.push({
        x: Math.random() * w,
        y: h * (0.79 + Math.random() * 0.2),
        len: 10 + Math.random() * 16,
        lean: -0.7 + Math.random() * 1.4,
        phase: Math.random() * Math.PI * 2,
      });
    }

    // 板橋区民まつりをイメージした提灯列
    lanterns = [];
    const ropeY = h * 0.18;
    const count = 14;
    for (let i = 0; i < count; i++) {
      const px = w * (0.08 + (i / (count - 1)) * 0.84);
      lanterns.push({
        x: px,
        y: ropeY + Math.sin(i * 0.6) * 3,
        r: 8 + (i % 3 === 0 ? 1.5 : 0),
        phase: Math.random() * Math.PI * 2,
      });
    }

    // 紙吹雪（祭りのにぎわい）
    confetti = [];
    for (let i = 0; i < 44; i++) {
      confetti.push(makeConfetti(true));
    }

    // 祭り会場側のやわらかい光粒
    festivalGlow = [];
    for (let i = 0; i < 26; i++) {
      festivalGlow.push({
        x: w * (0.12 + Math.random() * 0.76),
        y: h * (0.68 + Math.random() * 0.2),
        phase: Math.random() * Math.PI * 2,
        drift: 8 + Math.random() * 12,
      });
    }
  };

  function makeConfetti(randomY) {
    return {
      x: Math.random() * w,
      y: randomY ? Math.random() * h * 0.65 : -10,
      wv: 3 + Math.random() * 3,
      hv: 2 + Math.random() * 2,
      speed: 14 + Math.random() * 18,
      driftAmp: 14 + Math.random() * 24,
      driftSpeed: 0.5 + Math.random() * 0.9,
      phase: Math.random() * Math.PI * 2,
      rot: Math.random() * Math.PI * 2,
      rotSpeed: (Math.random() - 0.5) * 2.6,
      color: ['#ffd166', '#ef476f', '#06d6a0', '#f7b267', '#9b5de5'][Math.floor(Math.random() * 5)],
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
    const horizon = h * 0.54;
    const grad = ctx.createLinearGradient(0, 0, 0, horizon);
    grad.addColorStop(0, '#22345f');
    grad.addColorStop(0.34, '#486897');
    grad.addColorStop(0.68, '#e29063');
    grad.addColorStop(1, '#ffd9af');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, horizon);

    // 夕日
    const sx = w * 0.69;
    const sy = horizon - h * 0.03;
    const sr = Math.min(w, h) * 0.056;
    ctx.save();
    ctx.shadowBlur = 48 + Math.sin(t * 1.3) * 7;
    ctx.shadowColor = 'rgba(255,198,132,0.82)';
    ctx.fillStyle = '#ffe8cb';
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

  function drawTown() {
    const horizon = h * 0.54;

    // 遠景の街
    ctx.fillStyle = 'rgba(30,24,35,0.57)';
    skyline.forEach(b => {
      ctx.fillRect(b.x, horizon + h * 0.03 - b.h, b.w, b.h);
    });

    // 窓明かり
    windowLights.forEach(l => {
      const a = 0.35 + (Math.sin(t * 2.8 + l.phase) * 0.32 + 0.32);
      ctx.fillStyle = `rgba(255,215,156,${a})`;
      ctx.fillRect(l.x, l.y, 3, 4);
    });
  }

  function drawRiver() {
    const riverTop = h * 0.64;

    // 川面
    const rg = ctx.createLinearGradient(0, riverTop, 0, h);
    rg.addColorStop(0, '#4a6887');
    rg.addColorStop(0.48, '#35536e');
    rg.addColorStop(1, '#233f58');
    ctx.fillStyle = rg;
    ctx.fillRect(0, riverTop, w, h - riverTop);

    // 夕日の反射
    const reflection = ctx.createLinearGradient(w * 0.69, riverTop, w * 0.69, h);
    reflection.addColorStop(0, 'rgba(255,224,184,0.28)');
    reflection.addColorStop(1, 'rgba(255,224,184,0)');
    ctx.fillStyle = reflection;
    ctx.fillRect(w * 0.61, riverTop, w * 0.17, h - riverTop);

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
  }

  function drawLeveeAndGrass() {
    // 河川敷の土手
    ctx.fillStyle = '#2f4b32';
    ctx.beginPath();
    ctx.moveTo(0, h);
    ctx.lineTo(0, h * 0.82);
    ctx.quadraticCurveTo(w * 0.28, h * 0.75, w * 0.52, h * 0.82);
    ctx.quadraticCurveTo(w * 0.78, h * 0.89, w, h * 0.84);
    ctx.lineTo(w, h);
    ctx.closePath();
    ctx.fill();

    // 草の揺れ
    grassBlades.forEach(g => {
      const sway = Math.sin(t * 2 + g.phase) * 4;
      ctx.strokeStyle = 'rgba(122,178,112,0.55)';
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(g.x, g.y);
      ctx.quadraticCurveTo(
        g.x + g.lean * 4 + sway,
        g.y - g.len * 0.6,
        g.x + g.lean * 8 + sway,
        g.y - g.len
      );
      ctx.stroke();
    });
  }

  function drawFestivalLanterns() {
    // 提灯を吊るすロープ
    const ropeY = h * 0.18;
    ctx.strokeStyle = 'rgba(120,80,60,0.55)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(w * 0.06, ropeY - 6);
    ctx.quadraticCurveTo(w * 0.5, ropeY + 10, w * 0.94, ropeY - 4);
    ctx.stroke();

    // 提灯（板橋区民まつりモチーフ）
    lanterns.forEach((ln, i) => {
      const bob = Math.sin(t * 1.8 + i * 0.7) * 2.2;
      const flick = 0.45 + (Math.sin(t * 3 + ln.phase) * 0.25 + 0.25);

      // 紐
      ctx.strokeStyle = 'rgba(95,70,60,0.45)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(ln.x, ropeY + Math.sin(i * 0.4) * 2);
      ctx.lineTo(ln.x, ln.y + bob - ln.r - 2);
      ctx.stroke();

      // 提灯本体
      ctx.save();
      ctx.shadowBlur = 12;
      ctx.shadowColor = `rgba(255,200,130,${0.55 * flick})`;
      ctx.fillStyle = `rgba(255,170,110,${0.7 + flick * 0.25})`;
      ctx.beginPath();
      ctx.ellipse(ln.x, ln.y + bob, ln.r, ln.r * 1.2, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      // 提灯帯
      ctx.fillStyle = 'rgba(180,70,55,0.65)';
      ctx.fillRect(ln.x - ln.r * 0.9, ln.y + bob - 2, ln.r * 1.8, 3);
    });
  }

  function drawConfettiAndGlow() {
    // 紙吹雪
    confetti.forEach(c => {
      c.y += c.speed * 0.016;
      c.x += Math.sin(t * c.driftSpeed + c.phase) * c.driftAmp * 0.016;
      c.rot += c.rotSpeed * 0.016;

      if (c.y > h * 0.9) {
        Object.assign(c, makeConfetti(false));
        c.x = Math.random() * w;
        c.y = -8;
      }

      ctx.save();
      ctx.translate(c.x, c.y);
      ctx.rotate(c.rot);
      ctx.fillStyle = c.color;
      ctx.globalAlpha = 0.78;
      ctx.fillRect(-c.wv * 0.5, -c.hv * 0.5, c.wv, c.hv);
      ctx.restore();
    });

    // 祭り会場の光粒
    festivalGlow.forEach(gl => {
      const x = gl.x + Math.cos(t * 0.9 + gl.phase) * gl.drift * 0.22;
      const y = gl.y + Math.sin(t * 1.1 + gl.phase) * 2.4;
      const a = 0.2 + (Math.sin(t * 2.4 + gl.phase) * 0.22 + 0.22);
      ctx.fillStyle = `rgba(255,226,178,${a})`;
      ctx.beginPath();
      ctx.arc(x, y, 1.8, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  function drawUI() {
    ctx.save();
    ctx.font = `bold italic ${h * 0.04}px "Arial Black", Impact, sans-serif`;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';

    ctx.shadowBlur = 10;
    ctx.shadowColor = '#ffd9ae';
    ctx.fillStyle = '#ffffff';
    ctx.fillText('ITB-01', w * 0.96, h * 0.98);

    ctx.shadowBlur = 0;
    ctx.fillStyle = '#ffd9ae';
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
    drawTown();
    drawRiver();
    drawLeveeAndGrass();
    drawFestivalLanterns();
    drawConfettiAndGlow();
    drawUI();

    raf = requestAnimationFrame(draw);
  }
  draw();

  return function stop() {
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', resize);
  };
}