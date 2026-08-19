// chiyoda.js
export const key = 'chiyoda';
export const label = '千代田区：神田明神曙之景 - 桜咲く夜明けの高台';

/**
 * 千代田区の演出（Canvas型）。
 * 歌川広重「江戸名所百景・神田明神曙之景」に着想を得た夜明けの情景。
 * 左手前に神田明神の高台と満開の桜、眼下には朝靄に沈む江戸の町並み、
 * 遠くには朝焼けに染まる富士。桜吹雪と朝靄、そして昇る朝日の光が
 * ゆっくりと画面全体に「時間の経過」を与えています。
 *
 * ※ ファイル名・key は他区のファイル（sumida.js / setagaya.js）と
 *    命名規則を揃えるため、「千代田区」ではなく effectKey として
 *    'chiyoda' を採用しています。tokyoData.js 側の effectKey も
 *    'chiyoda' に合わせてください。
 */
export function run(canvas) {
  const ctx = canvas.getContext('2d');
  let w, h, raf, t = 0;

  let petals = [];
  let rooftops = [];
  let mistBands = [];
  let birds = [];
  let lightWindows = [];

  const generateScene = () => {
    const horizon = h * 0.56;

    // 桜吹雪の花びら
    petals = [];
    const numPetals = 70;
    for (let i = 0; i < numPetals; i++) {
      petals.push(makePetal(true));
    }

    // 町並みのシルエット（複数レイヤーの屋根の連なり）
    rooftops = [];
    ['far', 'mid', 'near'].forEach((layer, li) => {
      const baseY = horizon + h * (0.02 + li * 0.05);
      const roofs = [];
      let x = -50;
      while (x < w + 50) {
        const rw = w * (0.02 + Math.random() * 0.035);
        const rh = h * (0.02 + Math.random() * 0.035) * (1 + li * 0.4);
        roofs.push({ x, w: rw, h: rh });
        x += rw + Math.random() * 6;
      }
      rooftops.push({ layer, baseY, roofs, alpha: 0.35 + li * 0.25 });
    });

    // 町並みの灯り（ちらほら灯る窓）
    lightWindows = [];
    rooftops[2].roofs.forEach(r => {
      if (Math.random() > 0.6) {
        lightWindows.push({
          x: r.x + r.w * 0.5,
          y: rooftops[2].baseY - r.h * 0.4,
          phase: Math.random() * Math.PI * 2,
        });
      }
    });

    // 朝靄の帯
    mistBands = [];
    for (let i = 0; i < 4; i++) {
      mistBands.push({
        y: horizon + h * (0.02 + i * 0.04),
        speed: 4 + Math.random() * 5,
        offset: Math.random() * w,
        heightRatio: 0.03 + Math.random() * 0.02,
      });
    }

    // 空を渡る鳥
    birds = [];
    for (let i = 0; i < 3; i++) {
      birds.push({
        y: h * (0.14 + Math.random() * 0.12),
        speed: 5 + Math.random() * 5,
        offset: Math.random() * w,
        phase: Math.random() * Math.PI * 2,
      });
    }
  };

  function makePetal(randomY) {
    return {
      x: Math.random() * w,
      y: randomY ? Math.random() * h : -10,
      size: 3 + Math.random() * 3,
      fallSpeed: 12 + Math.random() * 14,
      driftAmp: 20 + Math.random() * 30,
      driftSpeed: 0.5 + Math.random() * 0.8,
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

  // ---- 1. 夜明けの空と朝日 ----
  function drawSky() {
    const horizon = h * 0.56;
    const grad = ctx.createLinearGradient(0, 0, 0, horizon);
    grad.addColorStop(0, '#2b2c52');
    grad.addColorStop(0.35, '#7a4a68');
    grad.addColorStop(0.65, '#e07a5f');
    grad.addColorStop(0.85, '#f4a261');
    grad.addColorStop(1, '#ffe1a8');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, horizon);

    // 朝日（地平線近くに半分沈んだような光）
    const sx = w * 0.62;
    const sy = horizon - h * 0.02;
    const sr = Math.min(w, h) * 0.05;
    ctx.save();
    ctx.shadowBlur = 50 + Math.sin(t * 1.5) * 8;
    ctx.shadowColor = 'rgba(255,220,150,0.85)';
    ctx.fillStyle = '#fff3d6';
    ctx.beginPath();
    ctx.arc(sx, sy, sr, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // 富士のシルエット
    ctx.save();
    ctx.fillStyle = 'rgba(90,70,100,0.55)';
    ctx.beginPath();
    ctx.moveTo(w * 0.30, horizon);
    ctx.lineTo(w * 0.40, horizon - h * 0.14);
    ctx.lineTo(w * 0.43, horizon - h * 0.155);
    ctx.lineTo(w * 0.46, horizon - h * 0.13);
    ctx.lineTo(w * 0.55, horizon);
    ctx.closePath();
    ctx.fill();
    // 雪化粧の頂（朝焼けに照らされる）
    ctx.fillStyle = 'rgba(255,225,190,0.6)';
    ctx.beginPath();
    ctx.moveTo(w * 0.415, horizon - h * 0.145);
    ctx.lineTo(w * 0.43, horizon - h * 0.155);
    ctx.lineTo(w * 0.445, horizon - h * 0.145);
    ctx.lineTo(w * 0.435, horizon - h * 0.12);
    ctx.lineTo(w * 0.425, horizon - h * 0.12);
    ctx.closePath();
    ctx.fill();
    ctx.restore();

    // 鳥
    ctx.strokeStyle = 'rgba(40,25,35,0.55)';
    ctx.lineWidth = 1.5;
    birds.forEach(b => {
      const x = (b.offset + t * b.speed * 10) % (w + 100) - 50;
      const flap = Math.sin(t * 8 + b.phase) * 3;
      ctx.beginPath();
      ctx.moveTo(x - 6, b.y - flap);
      ctx.lineTo(x, b.y);
      ctx.lineTo(x + 6, b.y - flap);
      ctx.stroke();
    });
  }

  // ---- 2. 江戸の町並み（靄にかすむ屋根の連なり） ----
  function drawCityscape() {
    rooftops.forEach(layer => {
      ctx.fillStyle = `rgba(35,25,35,${layer.alpha})`;
      layer.roofs.forEach(r => {
        ctx.beginPath();
        ctx.moveTo(r.x, layer.baseY);
        ctx.lineTo(r.x + r.w / 2, layer.baseY - r.h);
        ctx.lineTo(r.x + r.w, layer.baseY);
        ctx.closePath();
        ctx.fill();
      });
    });

    // 灯り
    lightWindows.forEach(lw => {
      const flick = 0.5 + Math.sin(t * 3 + lw.phase) * 0.3 + 0.3;
      ctx.save();
      ctx.globalAlpha = flick;
      ctx.fillStyle = '#ffcf8a';
      ctx.beginPath();
      ctx.arc(lw.x, lw.y, 1.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    });

    // 朝靄（横に流れる霞の帯）
    mistBands.forEach(m => {
      const x = (m.offset + t * m.speed) % (w * 2) - w * 0.5;
      const grad = ctx.createLinearGradient(x, 0, x + w, 0);
      grad.addColorStop(0, 'rgba(255,235,210,0)');
      grad.addColorStop(0.5, 'rgba(255,235,210,0.22)');
      grad.addColorStop(1, 'rgba(255,235,210,0)');
      ctx.fillStyle = grad;
      ctx.fillRect(x, m.y, w, h * m.heightRatio);
    });
  }

  // ---- 3. 神田明神の高台と社殿 ----
  function drawShrine() {
    const horizon = h * 0.56;
    const hillX0 = 0, hillX1 = w * 0.34;

    // 高台（前景の地面のシルエット）
    ctx.save();
    ctx.fillStyle = '#1c130f';
    ctx.beginPath();
    ctx.moveTo(hillX0, h);
    ctx.lineTo(hillX0, horizon + h * 0.06);
    ctx.quadraticCurveTo(hillX1 * 0.5, horizon - h * 0.02, hillX1, horizon + h * 0.03);
    ctx.lineTo(hillX1, h);
    ctx.closePath();
    ctx.fill();

    // 社殿（朱色の屋根、シルエット気味に）
    const shrineX = w * 0.14;
    const shrineY = horizon - h * 0.01;
    ctx.fillStyle = '#5c1f18';
    ctx.beginPath();
    ctx.moveTo(shrineX - w * 0.07, shrineY);
    ctx.lineTo(shrineX, shrineY - h * 0.07);
    ctx.lineTo(shrineX + w * 0.07, shrineY);
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = '#2a1510';
    ctx.fillRect(shrineX - w * 0.05, shrineY, w * 0.10, h * 0.04);

    // 鳥居
    const toriiX = w * 0.24;
    const toriiY = horizon + h * 0.05;
    ctx.strokeStyle = '#7a2a1e';
    ctx.lineWidth = Math.min(w, h) * 0.012;
    ctx.beginPath();
    ctx.moveTo(toriiX - w * 0.03, toriiY + h * 0.06);
    ctx.lineTo(toriiX - w * 0.03, toriiY - h * 0.01);
    ctx.moveTo(toriiX + w * 0.03, toriiY + h * 0.06);
    ctx.lineTo(toriiX + w * 0.03, toriiY - h * 0.01);
    ctx.moveTo(toriiX - w * 0.04, toriiY - h * 0.01);
    ctx.lineTo(toriiX + w * 0.04, toriiY - h * 0.01);
    ctx.stroke();
    ctx.lineWidth = Math.min(w, h) * 0.006;
    ctx.beginPath();
    ctx.moveTo(toriiX - w * 0.036, toriiY - h * 0.022);
    ctx.lineTo(toriiX + w * 0.036, toriiY - h * 0.022);
    ctx.stroke();

    ctx.restore();
  }

  // ---- 4. 満開の桜（手前の枝） ----
  function drawSakuraTree() {
    ctx.save();
    // 太い枝（画面左端から斜めに伸びる）
    ctx.strokeStyle = '#1a120c';
    ctx.lineCap = 'round';

    const sway = Math.sin(t * 0.5) * 0.03;

    ctx.lineWidth = Math.min(w, h) * 0.035;
    ctx.beginPath();
    ctx.moveTo(-10, h * 0.55);
    ctx.quadraticCurveTo(w * 0.12, h * (0.30 + sway), w * 0.30, h * (0.15 + sway * 1.5));
    ctx.stroke();

    ctx.lineWidth = Math.min(w, h) * 0.018;
    ctx.beginPath();
    ctx.moveTo(w * 0.08, h * 0.40);
    ctx.quadraticCurveTo(w * 0.20, h * (0.20 + sway), w * 0.36, h * (0.08 + sway * 1.5));
    ctx.stroke();

    // 花の房（枝に沿って淡いピンクの点描）
    const clusters = [
      [w * 0.02, h * 0.50], [w * 0.10, h * 0.38], [w * 0.18, h * 0.28],
      [w * 0.26, h * 0.18], [w * 0.33, h * 0.11], [w * 0.15, h * 0.22],
      [w * 0.22, h * 0.14], [w * 0.06, h * 0.44],
    ];
    clusters.forEach(([cx, cy], i) => {
      const bob = Math.sin(t * 1.2 + i) * 2;
      ctx.fillStyle = 'rgba(255,205,220,0.85)';
      for (let j = 0; j < 6; j++) {
        const ang = (j / 6) * Math.PI * 2;
        ctx.beginPath();
        ctx.arc(cx + Math.cos(ang) * 9, cy + bob + Math.sin(ang) * 9, 6, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.fillStyle = 'rgba(255,235,240,0.9)';
      ctx.beginPath();
      ctx.arc(cx, cy + bob, 7, 0, Math.PI * 2);
      ctx.fill();
    });
    ctx.restore();
  }

  // ---- 5. 桜吹雪 ----
  function drawPetals() {
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
      ctx.fillStyle = 'rgba(255,210,225,0.85)';
      ctx.beginPath();
      ctx.ellipse(0, 0, p.size, p.size * 0.6, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    });
  }

  // ---- 6. UI装飾 ----
  function drawUI() {
    ctx.save();
    ctx.font = `bold italic ${h * 0.04}px "Arial Black", Impact, sans-serif`;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';

    ctx.shadowBlur = 10;
    ctx.shadowColor = '#ffcf8a';
    ctx.fillStyle = '#ffffff';
    ctx.fillText("CYD-01", w * 0.96, h * 0.98);

    ctx.shadowBlur = 0;
    ctx.fillStyle = '#ffcf8a';
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
    drawCityscape();
    drawShrine();
    drawSakuraTree();
    drawPetals();
    drawUI();

    raf = requestAnimationFrame(draw);
  }
  draw();

  return function stop() {
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', resize);
  };
}