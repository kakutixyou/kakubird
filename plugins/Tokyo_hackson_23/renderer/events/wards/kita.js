export const key = 'kita';
export const label = '北区：旧古河庭園と飛鳥山の景 - 洋館・桜・参道の灯り';

/**
 * 北区の演出（Canvas型）。
 * 旧古河庭園の洋館とバラ庭園、飛鳥山公園の桜と高台の緑、
 * さらに十条銀座の賑わいを連想させる提灯の灯り、
 * 王子稲荷神社・王子神社・赤羽八幡神社をイメージした鳥居のシルエットを重ねた夕景。
 *
 * 「背景が変わった」と感じられるよう、
 * 色相遷移・レイヤー移動・点滅・花びら・暖色グローを強めに設計。
 *
 * ※ effectKey は 'kita' を想定。tokyoData.js 側も合わせてください。
 */
export function run(canvas) {
  const ctx = canvas.getContext('2d');
  let w, h, raf, t = 0;

  let petals = [];
  let clouds = [];
  let mistBands = [];
  let hillLights = [];
  let roseLights = [];
  let mansionWindows = [];
  let lanterns = [];
  let shoppers = [];
  let sparkle = [];

  const mansion = { x: 0, y: 0, w: 0, h: 0 };
  const torii = { x: 0, y: 0, s: 1 };

  const generateScene = () => {
    const horizon = h * 0.57;

    // 桜吹雪
    petals = [];
    for (let i = 0; i < 68; i++) petals.push(makePetal(true));

    // 雲帯
    clouds = [];
    for (let i = 0; i < 6; i++) {
      clouds.push({
        y: h * (0.08 + i * 0.065),
        width: w * (0.2 + Math.random() * 0.24),
        height: h * (0.024 + Math.random() * 0.02),
        speed: 1.4 + Math.random() * 2.8,
        offset: Math.random() * w,
        alpha: 0.05 + Math.random() * 0.08,
      });
    }

    // 霞帯（丘〜庭園）
    mistBands = [];
    for (let i = 0; i < 4; i++) {
      mistBands.push({
        y: horizon + h * (0.02 + i * 0.045),
        speed: 3 + Math.random() * 4,
        offset: Math.random() * w,
        heightRatio: 0.028 + Math.random() * 0.02,
      });
    }

    // 旧古河庭園の洋館
    mansion.w = w * 0.34;
    mansion.h = h * 0.18;
    mansion.x = w * 0.1;
    mansion.y = horizon + h * 0.01 - mansion.h;

    // 洋館の窓
    mansionWindows = [];
    const cols = 7;
    const rows = 3;
    for (let c = 0; c < cols; c++) {
      for (let r = 0; r < rows; r++) {
        if (Math.random() > 0.18) {
          mansionWindows.push({
            x: mansion.x + mansion.w * 0.1 + c * (mansion.w * 0.11),
            y: mansion.y + mansion.h * 0.2 + r * (mansion.h * 0.24),
            phase: Math.random() * Math.PI * 2,
          });
        }
      }
    }

    // バラ庭園の光
    roseLights = [];
    for (let i = 0; i < 38; i++) {
      roseLights.push({
        x: w * (0.06 + Math.random() * 0.52),
        y: h * (0.62 + Math.random() * 0.26),
        r: 2 + Math.random() * 3,
        phase: Math.random() * Math.PI * 2,
      });
    }

    // 飛鳥山の丘の灯り
    hillLights = [];
    for (let i = 0; i < 30; i++) {
      hillLights.push({
        x: w * (0.45 + Math.random() * 0.5),
        y: h * (0.54 + Math.random() * 0.27),
        phase: Math.random() * Math.PI * 2,
      });
    }

    // 十条銀座イメージの提灯列
    lanterns = [];
    const count = 12;
    for (let i = 0; i < count; i++) {
      lanterns.push({
        x: w * (0.54 + (i / (count - 1)) * 0.4),
        y: h * (0.34 + Math.sin(i * 0.55) * 0.01),
        r: 7 + (i % 3 === 0 ? 1.2 : 0),
        phase: Math.random() * Math.PI * 2,
      });
    }

    // 商店街の人影ドット
    shoppers = [];
    for (let i = 0; i < 28; i++) {
      shoppers.push({
        x: w * (0.5 + Math.random() * 0.46),
        y: h * (0.73 + Math.random() * 0.1),
        phase: Math.random() * Math.PI * 2,
      });
    }

    // きらめき
    sparkle = [];
    for (let i = 0; i < 22; i++) {
      sparkle.push({
        x: Math.random() * w,
        y: h * (0.12 + Math.random() * 0.62),
        phase: Math.random() * Math.PI * 2,
        life: 0.4 + Math.random() * 0.6,
      });
    }

    // 神社モチーフの鳥居位置
    torii.x = w * 0.78;
    torii.y = h * 0.66;
    torii.s = Math.min(w, h) / 900;
  };

  function makePetal(randomY) {
    return {
      x: Math.random() * w,
      y: randomY ? Math.random() * h : -10,
      size: 3 + Math.random() * 3,
      fallSpeed: 12 + Math.random() * 14,
      driftAmp: 18 + Math.random() * 28,
      driftSpeed: 0.5 + Math.random() * 0.85,
      phase: Math.random() * Math.PI * 2,
      rot: Math.random() * Math.PI * 2,
      rotSpeed: (Math.random() - 0.5) * 2,
    };
  }

  const resize = () => {
    w = canvas.width = canvas.clientWidth;
    h = canvas.height = canvas.clientHeight;
    if (w > 0 && h > 0) generateScene();
  };
  window.addEventListener('resize', resize);
  resize();

  // ---- 1. 空・夕陽・雲 ----
  function drawSky() {
    const horizon = h * 0.57;

    // 時間変化：ほんのり色相が揺れる
    const warm = 0.5 + Math.sin(t * 0.25) * 0.08;

    const grad = ctx.createLinearGradient(0, 0, 0, horizon);
    grad.addColorStop(0, '#20345c');
    grad.addColorStop(0.35, '#4f6f9b');
    grad.addColorStop(0.66, `rgba(${230 + warm * 10}, ${158 + warm * 12}, ${112 + warm * 10}, 1)`);
    grad.addColorStop(1, '#ffe3c1');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, horizon);

    // 夕陽
    const sx = w * 0.72;
    const sy = horizon - h * 0.025;
    const sr = Math.min(w, h) * 0.053;
    ctx.save();
    ctx.shadowBlur = 48 + Math.sin(t * 1.2) * 7;
    ctx.shadowColor = 'rgba(255,205,145,0.82)';
    ctx.fillStyle = '#fff1dc';
    ctx.beginPath();
    ctx.arc(sx, sy, sr, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // 雲
    clouds.forEach(c => {
      const x = (c.offset + t * c.speed * 10) % (w + c.width) - c.width;
      const g = ctx.createLinearGradient(x, c.y, x + c.width, c.y);
      g.addColorStop(0, 'rgba(255,240,225,0)');
      g.addColorStop(0.5, `rgba(255,240,225,${c.alpha})`);
      g.addColorStop(1, 'rgba(255,240,225,0)');
      ctx.fillStyle = g;
      ctx.fillRect(x, c.y, c.width, c.height);
    });
  }

  // ---- 2. 飛鳥山公園の丘 ----
  function drawAsukayamaHill() {
    ctx.fillStyle = '#3e5f42';
    ctx.beginPath();
    ctx.moveTo(w * 0.38, h);
    ctx.lineTo(w * 0.38, h * 0.66);
    ctx.quadraticCurveTo(w * 0.58, h * 0.5, w * 0.9, h * 0.63);
    ctx.quadraticCurveTo(w * 1.02, h * 0.69, w, h * 0.75);
    ctx.lineTo(w, h);
    ctx.closePath();
    ctx.fill();

    hillLights.forEach(l => {
      const a = 0.18 + (Math.sin(t * 2.5 + l.phase) * 0.2 + 0.2);
      ctx.fillStyle = `rgba(255,228,186,${a})`;
      ctx.beginPath();
      ctx.arc(l.x, l.y, 1.8, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  // ---- 3. 旧古河庭園の洋館 ----
  function drawFurukawaMansion() {
    // 本体
    ctx.fillStyle = 'rgba(52,43,48,0.88)';
    ctx.fillRect(mansion.x, mansion.y, mansion.w, mansion.h);

    // 屋根
    ctx.fillStyle = 'rgba(37,29,34,0.96)';
    ctx.beginPath();
    ctx.moveTo(mansion.x - mansion.w * 0.02, mansion.y);
    ctx.lineTo(mansion.x + mansion.w * 0.5, mansion.y - mansion.h * 0.27);
    ctx.lineTo(mansion.x + mansion.w * 1.02, mansion.y);
    ctx.closePath();
    ctx.fill();

    // 塔屋
    const tw = mansion.w * 0.13;
    const th = mansion.h * 0.34;
    const tx = mansion.x + mansion.w * 0.72;
    const ty = mansion.y - th;
    ctx.fillStyle = 'rgba(44,36,42,0.93)';
    ctx.fillRect(tx, ty, tw, th);
    ctx.beginPath();
    ctx.moveTo(tx - tw * 0.06, ty);
    ctx.lineTo(tx + tw * 0.5, ty - th * 0.5);
    ctx.lineTo(tx + tw * 1.06, ty);
    ctx.closePath();
    ctx.fill();

    // 窓
    mansionWindows.forEach(win => {
      const a = 0.34 + (Math.sin(t * 2.8 + win.phase) * 0.3 + 0.3);
      ctx.fillStyle = `rgba(255,220,172,${a})`;
      ctx.fillRect(win.x, win.y, 6, 8);
    });
  }

  // ---- 4. 庭園（バラ）・霞 ----
  function drawGardenAndMist() {
    // 庭園地形
    ctx.fillStyle = '#2f4d36';
    ctx.beginPath();
    ctx.moveTo(0, h);
    ctx.lineTo(0, h * 0.76);
    ctx.quadraticCurveTo(w * 0.2, h * 0.7, w * 0.42, h * 0.78);
    ctx.quadraticCurveTo(w * 0.58, h * 0.85, w * 0.78, h * 0.8);
    ctx.quadraticCurveTo(w * 0.9, h * 0.77, w, h * 0.82);
    ctx.lineTo(w, h);
    ctx.closePath();
    ctx.fill();

    // バラの光
    roseLights.forEach(r => {
      const a = 0.24 + (Math.sin(t * 3 + r.phase) * 0.24 + 0.24);
      ctx.save();
      ctx.shadowBlur = 11;
      ctx.shadowColor = `rgba(255,138,162,${a * 0.85})`;
      ctx.fillStyle = `rgba(255,120,148,${a})`;
      ctx.beginPath();
      ctx.arc(r.x, r.y, r.r, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    });

    // 霞
    mistBands.forEach(m => {
      const x = (m.offset + t * m.speed) % (w * 2) - w * 0.5;
      const g = ctx.createLinearGradient(x, 0, x + w, 0);
      g.addColorStop(0, 'rgba(255,236,212,0)');
      g.addColorStop(0.5, 'rgba(255,236,212,0.2)');
      g.addColorStop(1, 'rgba(255,236,212,0)');
      ctx.fillStyle = g;
      ctx.fillRect(x, m.y, w, h * m.heightRatio);
    });
  }

  // ---- 5. 十条銀座（提灯）・神社モチーフ ----
  function drawStreetAndShrineMotifs() {
    // 商店街のライン
    ctx.strokeStyle = 'rgba(120,88,68,0.5)';
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    ctx.moveTo(w * 0.52, h * 0.33);
    ctx.quadraticCurveTo(w * 0.74, h * 0.36, w * 0.94, h * 0.34);
    ctx.stroke();

    // 提灯
    lanterns.forEach((ln, i) => {
      const bob = Math.sin(t * 1.8 + i * 0.65) * 2;
      const flick = 0.45 + (Math.sin(t * 3 + ln.phase) * 0.25 + 0.25);

      ctx.strokeStyle = 'rgba(96,72,58,0.45)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(ln.x, h * 0.34 + Math.sin(i * 0.4) * 2);
      ctx.lineTo(ln.x, ln.y + bob - ln.r - 2);
      ctx.stroke();

      ctx.save();
      ctx.shadowBlur = 13;
      ctx.shadowColor = `rgba(255,198,132,${0.55 * flick})`;
      ctx.fillStyle = `rgba(255,168,108,${0.7 + flick * 0.24})`;
      ctx.beginPath();
      ctx.ellipse(ln.x, ln.y + bob, ln.r, ln.r * 1.2, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      ctx.fillStyle = 'rgba(184,72,54,0.64)';
      ctx.fillRect(ln.x - ln.r * 0.9, ln.y + bob - 2, ln.r * 1.8, 3);
    });

    // 人影
    shoppers.forEach(s => {
      const a = 0.16 + (Math.sin(t * 2.7 + s.phase) * 0.15 + 0.15);
      ctx.fillStyle = `rgba(35,28,36,${a})`;
      ctx.beginPath();
      ctx.arc(s.x, s.y, 2.2, 0, Math.PI * 2);
      ctx.fill();
    });

    // 鳥居（王子稲荷・王子神社・赤羽八幡の象徴として抽象化）
    const tx = torii.x;
    const ty = torii.y;
    const sc = torii.s * (0.95 + Math.sin(t * 0.8) * 0.02);

    ctx.strokeStyle = 'rgba(125,45,34,0.9)';
    ctx.lineWidth = 10 * sc;
    ctx.beginPath();
    ctx.moveTo(tx - 28 * sc, ty + 54 * sc);
    ctx.lineTo(tx - 28 * sc, ty - 8 * sc);
    ctx.moveTo(tx + 28 * sc, ty + 54 * sc);
    ctx.lineTo(tx + 28 * sc, ty - 8 * sc);
    ctx.moveTo(tx - 40 * sc, ty - 8 * sc);
    ctx.lineTo(tx + 40 * sc, ty - 8 * sc);
    ctx.stroke();

    ctx.lineWidth = 5 * sc;
    ctx.beginPath();
    ctx.moveTo(tx - 35 * sc, ty - 20 * sc);
    ctx.lineTo(tx + 35 * sc, ty - 20 * sc);
    ctx.stroke();
  }

  // ---- 6. 桜吹雪・きらめき ----
  function drawPetalsAndSparkle() {
    petals.forEach(p => {
      p.y += p.fallSpeed * 0.016;
      p.x += Math.sin(t * p.driftSpeed + p.phase) * p.driftAmp * 0.016;
      p.rot += p.rotSpeed * 0.016;

      if (p.y > h + 10) {
        Object.assign(p, makePetal(false));
        p.x = Math.random() * w;
        p.y = -10;
      }

      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rot);
      ctx.fillStyle = 'rgba(255,210,225,0.84)';
      ctx.beginPath();
      ctx.ellipse(0, 0, p.size, p.size * 0.62, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    });

    sparkle.forEach(s => {
      const a = (0.2 + Math.sin(t * 3 + s.phase) * 0.2) * s.life;
      if (a < 0.02) return;
      ctx.strokeStyle = `rgba(255,245,226,${a})`;
      ctx.lineWidth = 1;
      const r = 2.5;
      ctx.beginPath();
      ctx.moveTo(s.x - r, s.y);
      ctx.lineTo(s.x + r, s.y);
      ctx.moveTo(s.x, s.y - r);
      ctx.lineTo(s.x, s.y + r);
      ctx.stroke();
    });
  }

  // ---- 7. UI装飾 ----
  function drawUI() {
    ctx.save();
    ctx.font = `bold italic ${h * 0.04}px "Arial Black", Impact, sans-serif`;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';

    ctx.shadowBlur = 10;
    ctx.shadowColor = '#ffd9b7';
    ctx.fillStyle = '#ffffff';
    ctx.fillText('KTA-02', w * 0.96, h * 0.98);

    ctx.shadowBlur = 0;
    ctx.fillStyle = '#ffd9b7';
    ctx.fillRect(w * 0.965, h * 0.94, w * 0.015, h * 0.04);
    ctx.restore();
  }

  // ---- メインループ ----
  function draw() {
    t += 0.016;
    if (w === 0 || h === 0) {
      raf = requestAnimationFrame(draw);
      return;
    }

    ctx.clearRect(0, 0, w, h);

    drawSky();
    drawAsukayamaHill();
    drawFurukawaMansion();
    drawGardenAndMist();
    drawStreetAndShrineMotifs();
    drawPetalsAndSparkle();
    drawUI();

    raf = requestAnimationFrame(draw);
  }
  draw();

  return function stop() {
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', resize);
  };
}