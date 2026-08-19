// renderer/events/wards/bunkyo.js
export const key = 'bunkyo';
export const label = '文京区：庭園と知の灯り - 池畔に映る静かな夕景';

/**
 * 文京区の演出（Canvas型）。
 * 小石川後楽園をイメージした池と築山、落ち着いた街の明かり、
 * そして遠景に東京ドームを思わせる白いドームシルエットを重ね、
 * 文教地区らしい静謐さと都市の気配を表現する。
 *
 * ※ effectKey は 'bunkyo' を想定。tokyoData.js 側も合わせてください。
 */
export function run(canvas) {
  const ctx = canvas.getContext('2d');
  let w, h, raf, t = 0;

  let clouds = [];
  let ripples = [];
  let gardenLights = [];
  let cityBlocks = [];
  let windowsLit = [];
  let fireflies = [];
  let stones = [];

  const generateScene = () => {
    const horizon = h * 0.52;
    const pondTop = h * 0.63;

    // 空の雲
    clouds = [];
    for (let i = 0; i < 5; i++) {
      clouds.push({
        y: h * (0.09 + i * 0.07),
        width: w * (0.2 + Math.random() * 0.24),
        height: h * (0.03 + Math.random() * 0.018),
        speed: 1.8 + Math.random() * 2.8,
        offset: Math.random() * w,
        alpha: 0.06 + Math.random() * 0.08,
      });
    }

    // 池の波紋ライン
    ripples = [];
    for (let i = 0; i < 12; i++) {
      ripples.push({
        y: pondTop + i * h * 0.022,
        amp: 2 + Math.random() * 3.5,
        freq: 0.012 + Math.random() * 0.01,
        phase: Math.random() * Math.PI * 2,
        alpha: 0.07 + i * 0.012,
      });
    }

    // 遠景の街ブロック
    cityBlocks = [];
    let x = -20;
    while (x < w + 20) {
      const bw = w * (0.02 + Math.random() * 0.04);
      const bh = h * (0.05 + Math.random() * 0.15);
      cityBlocks.push({ x, w: bw, h: bh });
      x += bw + Math.random() * 5;
    }

    // 窓明かり
    windowsLit = [];
    cityBlocks.forEach(b => {
      const cols = Math.max(1, Math.floor(b.w / 9));
      const rows = Math.max(1, Math.floor(b.h / 11));
      for (let c = 0; c < cols; c++) {
        for (let r = 0; r < rows; r++) {
          if (Math.random() > 0.86) {
            windowsLit.push({
              x: b.x + 4 + c * 9,
              y: horizon + h * 0.03 - b.h + 6 + r * 11,
              phase: Math.random() * Math.PI * 2,
            });
          }
        }
      }
    });

    // 庭園の行灯風ライト
    gardenLights = [];
    for (let i = 0; i < 8; i++) {
      gardenLights.push({
        x: w * (0.08 + i * 0.1 + Math.random() * 0.02),
        y: h * (0.70 + Math.random() * 0.08),
        phase: Math.random() * Math.PI * 2,
      });
    }

    // 水辺の小さな光
    fireflies = [];
    for (let i = 0; i < 24; i++) {
      fireflies.push({
        x: Math.random() * w,
        y: h * (0.66 + Math.random() * 0.22),
        phase: Math.random() * Math.PI * 2,
        drift: 6 + Math.random() * 14,
      });
    }

    // 飛び石
    stones = [];
    for (let i = 0; i < 10; i++) {
      stones.push({
        x: w * (0.12 + i * 0.07),
        y: h * (0.78 + Math.sin(i * 0.7) * 0.015),
        rx: 8 + Math.random() * 6,
        ry: 4 + Math.random() * 3,
      });
    }
  };

  const resize = () => {
    w = canvas.width = canvas.clientWidth;
    h = canvas.height = canvas.clientHeight;
    if (w > 0 && h > 0) generateScene();
  };
  window.addEventListener('resize', resize);
  resize();

  function drawSky() {
    const horizon = h * 0.52;
    const grad = ctx.createLinearGradient(0, 0, 0, horizon);
    grad.addColorStop(0, '#24345e');
    grad.addColorStop(0.34, '#49658f');
    grad.addColorStop(0.66, '#d78962');
    grad.addColorStop(1, '#f6d9b2');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, horizon);

    // 柔らかな夕日
    const sx = w * 0.66;
    const sy = horizon - h * 0.03;
    const sr = Math.min(w, h) * 0.05;
    ctx.save();
    ctx.shadowBlur = 42 + Math.sin(t * 1.2) * 6;
    ctx.shadowColor = 'rgba(255,205,145,0.8)';
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

  function drawCityAndDome() {
    const horizon = h * 0.52;

    // 街並み
    ctx.fillStyle = 'rgba(30,25,34,0.55)';
    cityBlocks.forEach(b => {
      ctx.fillRect(b.x, horizon + h * 0.03 - b.h, b.w, b.h);
    });

    // 窓
    windowsLit.forEach(l => {
      const a = 0.35 + (Math.sin(t * 2.8 + l.phase) * 0.3 + 0.3);
      ctx.fillStyle = `rgba(255,216,156,${a})`;
      ctx.fillRect(l.x, l.y, 3, 4);
    });

    // 東京ドームを想起する白いドームシルエット（抽象）
    const dx = w * 0.36;
    const dy = horizon + h * 0.01;
    const dw = w * 0.22;
    const dh = h * 0.10;

    ctx.save();
    ctx.fillStyle = 'rgba(235,240,245,0.28)';
    ctx.beginPath();
    ctx.ellipse(dx, dy, dw * 0.5, dh * 0.5, 0, Math.PI, Math.PI * 2);
    ctx.lineTo(dx + dw * 0.5, dy);
    ctx.lineTo(dx - dw * 0.5, dy);
    ctx.closePath();
    ctx.fill();

    // ドーム下部の影
    ctx.fillStyle = 'rgba(40,35,45,0.26)';
    ctx.fillRect(dx - dw * 0.48, dy, dw * 0.96, h * 0.015);
    ctx.restore();
  }

  function drawPondAndGarden() {
    const pondTop = h * 0.63;

    // 池
    const pg = ctx.createLinearGradient(0, pondTop, 0, h);
    pg.addColorStop(0, '#45627f');
    pg.addColorStop(0.5, '#324f6a');
    pg.addColorStop(1, '#223d55');
    ctx.fillStyle = pg;
    ctx.fillRect(0, pondTop, w, h - pondTop);

    // 反射
    const refl = ctx.createLinearGradient(w * 0.66, pondTop, w * 0.66, h);
    refl.addColorStop(0, 'rgba(255,226,190,0.24)');
    refl.addColorStop(1, 'rgba(255,226,190,0)');
    ctx.fillStyle = refl;
    ctx.fillRect(w * 0.58, pondTop, w * 0.16, h - pondTop);

    // 波紋
    ripples.forEach(rp => {
      ctx.strokeStyle = `rgba(220,236,255,${rp.alpha})`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let x = 0; x <= w; x += 8) {
        const y = rp.y + Math.sin(x * rp.freq + t * 2 + rp.phase) * rp.amp;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    });

    // 左手前の築山（庭園）
    ctx.fillStyle = '#304a33';
    ctx.beginPath();
    ctx.moveTo(0, h);
    ctx.lineTo(0, h * 0.77);
    ctx.quadraticCurveTo(w * 0.13, h * 0.71, w * 0.24, h * 0.79);
    ctx.quadraticCurveTo(w * 0.30, h * 0.83, w * 0.36, h * 0.81);
    ctx.lineTo(w * 0.36, h);
    ctx.closePath();
    ctx.fill();

    // 飛び石
    stones.forEach(s => {
      ctx.fillStyle = 'rgba(160,165,170,0.45)';
      ctx.beginPath();
      ctx.ellipse(s.x, s.y, s.rx, s.ry, 0, 0, Math.PI * 2);
      ctx.fill();
    });

    // 行灯風ライト
    gardenLights.forEach(gl => {
      const a = 0.35 + (Math.sin(t * 2.5 + gl.phase) * 0.28 + 0.28);
      ctx.save();
      ctx.shadowBlur = 8;
      ctx.shadowColor = 'rgba(255,220,160,0.6)';
      ctx.fillStyle = `rgba(255,214,150,${a})`;
      ctx.fillRect(gl.x - 2, gl.y - 6, 4, 8);
      ctx.restore();
    });

    // 水辺の小光
    fireflies.forEach(f => {
      const x = f.x + Math.cos(t * 0.8 + f.phase) * f.drift * 0.2;
      const y = f.y + Math.sin(t * 1.0 + f.phase) * 2.5;
      const a = 0.18 + (Math.sin(t * 2.3 + f.phase) * 0.24 + 0.24);
      ctx.fillStyle = `rgba(255,232,180,${a})`;
      ctx.beginPath();
      ctx.arc(x, y, 1.6, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  function drawUI() {
    ctx.save();
    ctx.font = `bold italic ${h * 0.04}px "Arial Black", Impact, sans-serif`;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';

    ctx.shadowBlur = 10;
    ctx.shadowColor = '#ffd8b0';
    ctx.fillStyle = '#ffffff';
    ctx.fillText('BNK-01', w * 0.96, h * 0.98);

    ctx.shadowBlur = 0;
    ctx.fillStyle = '#ffd8b0';
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
    drawCityAndDome();
    drawPondAndGarden();
    drawUI();

    raf = requestAnimationFrame(draw);
  }
  draw();

  return function stop() {
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', resize);
  };
}