export const key = 'minato';
export const label = '港区：ウォータータクシーで東京湾クルーズ';

/**
 * 港区の演出。
 * レインボーブリッジ・ビル群のシルエットを奥から手前へ流し、
 * 手前で水上タクシー（船）が波に揺られながら進んでいるように見せる。
 * 全て2D Canvasの図形描画のみで構成（画像アセット不使用）。
 */
export function run(canvas) {
  const ctx = canvas.getContext('2d');
  let w, h, raf, t = 0;

  const resize = () => {
    w = canvas.width = canvas.clientWidth;
    h = canvas.height = canvas.clientHeight;
  };
  window.addEventListener('resize', resize);
  resize();

  // ---- レインボーブリッジ（奥のランドマーク。ゆっくり左へ流れる） ----
  const bridge = { baseX: 0.62, speed: 0.006 };

  // ---- 奥のビル群シルエット（2レイヤーでパララックス） ----
  function makeSkyline(count, seedOffset) {
    const arr = [];
    for (let i = 0; i < count; i++) {
      arr.push({
        x: i * (1 / count) + seedOffset,
        wRatio: 0.03 + Math.random() * 0.05,
        hRatio: 0.12 + Math.random() * 0.22,
      });
    }
    return arr;
  }
  const skylineFar = makeSkyline(14, 0);
  const skylineNear = makeSkyline(9, 0.5);

  // ---- 水面の波（複数レイヤーの正弦波） ----
  const waveLayers = [
    { amp: 6, freq: 0.02, speed: 0.03, alpha: 0.20, yRatio: 0.62 },
    { amp: 10, freq: 0.014, speed: 0.05, alpha: 0.28, yRatio: 0.72 },
    { amp: 16, freq: 0.01, speed: 0.08, alpha: 0.4, yRatio: 0.84 },
  ];

  // ---- 水面のきらめき（光の反射） ----
  const sparkles = Array.from({ length: 40 }, () => ({
    x: Math.random(),
    y: 0.6 + Math.random() * 0.38,
    phase: Math.random() * Math.PI * 2,
    speed: 0.02 + Math.random() * 0.03,
  }));

  // ---- 船の航跡（波しぶき粒子） ----
  const wake = [];

  function drawSky() {
    const grad = ctx.createLinearGradient(0, 0, 0, h * 0.65);
    grad.addColorStop(0, '#0d1b2e');
    grad.addColorStop(0.55, '#16324f');
    grad.addColorStop(1, '#1f5c86');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h * 0.65);
  }

  function drawSkyline(layer, baseAlpha, colorHue, scrollSpeed) {
    const scroll = (t * scrollSpeed) % 1;
    layer.forEach((b) => {
      const bx = ((b.x - scroll) % 1 + 1) % 1;
      const bw = bx * w;
      const width = b.wRatio * w;
      const height = b.hRatio * h;
      const baseY = h * 0.62;
      ctx.fillStyle = `hsla(${colorHue}, 45%, 12%, ${baseAlpha})`;
      ctx.fillRect(bw - width / 2, baseY - height, width, height);
      // 窓明かり
      const winCols = Math.max(1, Math.floor(width / 6));
      const winRows = Math.max(1, Math.floor(height / 8));
      for (let r = 0; r < winRows; r++) {
        for (let c = 0; c < winCols; c++) {
          if (Math.random() > 0.86) {
            ctx.fillStyle = 'rgba(255,214,140,0.55)';
            ctx.fillRect(
              bw - width / 2 + c * 6 + 1,
              baseY - height + r * 8 + 2,
              2.5, 3
            );
          }
        }
      }
    });
  }

  function drawRainbowBridge() {
    const scroll = (t * bridge.speed) % 1;
    const cx = (((bridge.baseX - scroll) % 1) + 1) % 1 * w;
    const baseY = h * 0.62;
    const span = w * 0.5;
    const towerH = h * 0.22;

    // 主塔2本
    ctx.strokeStyle = 'rgba(210,225,240,0.55)';
    ctx.lineWidth = Math.max(2, w * 0.004);
    [cx - span * 0.32, cx + span * 0.32].forEach((tx) => {
      ctx.beginPath();
      ctx.moveTo(tx, baseY);
      ctx.lineTo(tx, baseY - towerH);
      ctx.stroke();
    });

    // メインケーブル（吊り橋の曲線）
    ctx.beginPath();
    ctx.moveTo(cx - span * 0.5, baseY - towerH * 0.2);
    ctx.quadraticCurveTo(cx - span * 0.32, baseY - towerH, cx, baseY - towerH * 0.55);
    ctx.quadraticCurveTo(cx + span * 0.32, baseY - towerH, cx + span * 0.5, baseY - towerH * 0.2);
    ctx.stroke();

    // 橋桁のライトアップ（点々）
    for (let i = -0.5; i <= 0.5; i += 0.045) {
      const lx = cx + span * i;
      const glow = 0.4 + Math.sin(t * 2 + i * 20) * 0.3;
      ctx.fillStyle = `rgba(255,255,255,${Math.max(0.15, glow)})`;
      ctx.beginPath();
      ctx.arc(lx, baseY - 4, 1.6, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function drawWater() {
    const waterTop = h * 0.6;
    const grad = ctx.createLinearGradient(0, waterTop, 0, h);
    grad.addColorStop(0, '#123c56');
    grad.addColorStop(1, '#04141f');
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
      ctx.fillStyle = `rgba(120,190,220,${layer.alpha})`;
      ctx.fill();
    });

    // きらめき
    sparkles.forEach((s) => {
      const y = s.y * h + Math.sin(t * s.speed * 20 + s.phase) * 3;
      const alpha = 0.3 + Math.sin(t * 3 + s.phase) * 0.25;
      ctx.fillStyle = `rgba(255,244,214,${Math.max(0, alpha)})`;
      ctx.fillRect(s.x * w, y, 2, 1.4);
    });
  }

  function drawBoat() {
    const bx = w * 0.5;
    const bob = Math.sin(t * 2.2) * h * 0.006;
    const tilt = Math.sin(t * 2.2 + 0.6) * 0.035;
    const by = h * 0.86 + bob;
    const scale = Math.min(w, h) * 0.22;

    ctx.save();
    ctx.translate(bx, by);
    ctx.rotate(tilt);

    // 船体
    ctx.beginPath();
    ctx.moveTo(-scale * 0.55, 0);
    ctx.quadraticCurveTo(-scale * 0.6, scale * 0.18, -scale * 0.3, scale * 0.22);
    ctx.lineTo(scale * 0.5, scale * 0.22);
    ctx.quadraticCurveTo(scale * 0.62, scale * 0.18, scale * 0.55, 0);
    ctx.closePath();
    const hullGrad = ctx.createLinearGradient(0, -scale * 0.05, 0, scale * 0.22);
    hullGrad.addColorStop(0, '#e8edf2');
    hullGrad.addColorStop(1, '#9aa9b8');
    ctx.fillStyle = hullGrad;
    ctx.fill();
    ctx.strokeStyle = 'rgba(20,30,40,0.5)';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // 船体のライン（青ライン＝タクシー感）
    ctx.strokeStyle = '#2a7fb8';
    ctx.lineWidth = scale * 0.03;
    ctx.beginPath();
    ctx.moveTo(-scale * 0.5, scale * 0.08);
    ctx.lineTo(scale * 0.48, scale * 0.08);
    ctx.stroke();

    // キャビン
    ctx.fillStyle = '#f4f7fa';
    ctx.strokeStyle = 'rgba(20,30,40,0.4)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(-scale * 0.28, -scale * 0.28, scale * 0.56, scale * 0.28, scale * 0.04);
    ctx.fill();
    ctx.stroke();

    // 窓
    ctx.fillStyle = 'rgba(120,190,230,0.85)';
    for (let i = -2; i <= 2; i++) {
      ctx.fillRect(i * scale * 0.1 - scale * 0.03, -scale * 0.22, scale * 0.06, scale * 0.1);
    }

    ctx.restore();

    // 航跡（波しぶき）を一定間隔で発生
    if (Math.random() > 0.55) {
      wake.push({
        x: bx - scale * 0.5 + (Math.random() - 0.5) * scale * 0.2,
        y: by + scale * 0.2,
        life: 1,
        r: 2 + Math.random() * 3,
      });
    }
  }

  function drawWake() {
    for (let i = wake.length - 1; i >= 0; i--) {
      const p = wake[i];
      p.x -= 1.4;
      p.y += 0.15;
      p.life -= 0.02;
      if (p.life <= 0) { wake.splice(i, 1); continue; }
      ctx.beginPath();
      ctx.fillStyle = `rgba(255,255,255,${p.life * 0.5})`;
      ctx.arc(p.x, p.y, p.r * (1 + (1 - p.life) * 1.5), 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function draw() {
    t += 0.016;
    ctx.clearRect(0, 0, w, h);
    drawSky();
    drawSkyline(skylineFar, 0.5, 210, 0.008);
    drawRainbowBridge();
    drawSkyline(skylineNear, 0.75, 205, 0.02);
    drawWater();
    drawWake();
    drawBoat();
    raf = requestAnimationFrame(draw);
  }
  draw();

  return function stop() {
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', resize);
  };
}