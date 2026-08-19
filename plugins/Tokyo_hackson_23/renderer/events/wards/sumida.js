// sumida.js
export const key = 'sumida';
export const label = '墨田区：伝統と革新が交差する隅田川の夜';

/**
 * 墨田区の演出（Canvas型）。
 * 過去（江戸情緒）と現代（光の海・電波塔）を融合させたハイブリッドバージョン。
 * 奥には現代の輝くビル群と色が変化するリアルなスカイツリー、
 * 手前には隅田川の水面、屋形船、そして提灯が揺れる元柳橋。
 * 夜空には満月と両国花火が打ち上がります。
 */
export function run(canvas) {
  const ctx = canvas.getContext('2d');
  let w, h, raf, t = 0;

  let cityLights = [];
  let stars = [];
  let boats = [];
  let fireworks = [];
  let nextFireworkAt = 0;
  let lanterns = [];

  const generateScene = () => {
    const horizon = h * 0.55; 

    // ---- 星 ----
    stars = [];
    for (let i = 0; i < 120; i++) {
      stars.push({
        x: Math.random() * w,
        y: Math.random() * horizon * 0.85,
        r: Math.random() * 1.4 + 0.3,
        phase: Math.random() * Math.PI * 2,
        speed: Math.random() * 0.02 + 0.01,
      });
    }

    // ---- 現代の街明かり（奥） ----
    cityLights = [];
    const numLights = 2000;
    const colors = ['#ffcc66', '#ffaa44', '#ffeebb', '#ff8822', '#ffffff', '#00e5ff'];
    for (let i = 0; i < numLights; i++) {
      const depth = Math.random();
      const y = horizon - h * 0.15 + Math.pow(depth, 2) * (h * 0.25);
      const x = Math.random() * w;
      const size = 0.5 + depth * 3.0;
      cityLights.push({
        x, y, size, depth,
        color: colors[Math.floor(Math.random() * colors.length)],
        blinkSpeed: Math.random() * 0.05 + 0.01,
        phase: Math.random() * Math.PI * 2,
        isBright: Math.random() > 0.95
      });
    }

    // ---- 屋形船（川面） ----
    boats = [];
    const numBoats = 5;
    for (let i = 0; i < numBoats; i++) {
      const depth = 0.15 + Math.random() * 0.6;
      boats.push({
        baseX: Math.random() * w,
        y: horizon + depth * (h - horizon) * 0.6,
        depth,
        speed: (0.15 + depth * 0.35) * (Math.random() > 0.5 ? 1 : -1),
        bob: Math.random() * Math.PI * 2,
      });
    }

    // ---- 橋の提灯（手前） ----
    lanterns = [];
    const numLanterns = 9;
    for (let i = 0; i < numLanterns; i++) {
      const p = i / (numLanterns - 1);
      lanterns.push({
        x: w * -0.05 + p * w * 0.7, 
        p,
        flicker: Math.random() * Math.PI * 2,
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

  // ---- 1. 夜空と月 ----
  function drawSkyAndMoon() {
    const horizon = h * 0.55;
    const grad = ctx.createLinearGradient(0, 0, 0, horizon);
    grad.addColorStop(0, '#0a1025');
    grad.addColorStop(0.4, '#1a1f45');
    grad.addColorStop(0.7, '#2c2545');
    grad.addColorStop(1, '#3a2440');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, horizon);

    stars.forEach(s => {
      const tw = 0.4 + Math.sin(t * 20 * s.speed + s.phase) * 0.4 + 0.4;
      ctx.globalAlpha = Math.max(0, tw);
      ctx.fillStyle = '#fff8e6';
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fill();
    });
    ctx.globalAlpha = 1;

    const mx = w * 0.8;
    const my = h * 0.15;
    const mr = Math.min(w, h) * 0.05;

    ctx.save();
    ctx.shadowBlur = 40;
    ctx.shadowColor = 'rgba(255, 220, 180, 0.6)';
    ctx.fillStyle = '#fffae6';
    ctx.beginPath();
    ctx.arc(mx, my, mr, 0, Math.PI * 2);
    ctx.fill();

    ctx.shadowBlur = 0;
    ctx.fillStyle = 'rgba(150, 150, 160, 0.15)';
    ctx.beginPath();
    ctx.arc(mx - mr * 0.2, my + mr * 0.2, mr * 0.4, 0, Math.PI * 2);
    ctx.arc(mx + mr * 0.3, my - mr * 0.1, mr * 0.3, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  // ---- 2. 現代の街明かり（奥） ----
  function drawCityscape() {
    ctx.fillStyle = '#050302';
    ctx.fillRect(0, h * 0.4, w, h * 0.6);

    cityLights.forEach(l => {
      const flicker = 0.6 + Math.sin(t * 30 * l.blinkSpeed + l.phase) * 0.4;
      ctx.fillStyle = l.color;
      ctx.globalAlpha = flicker;
      
      if (l.isBright && l.depth > 0.5) {
        ctx.save();
        ctx.shadowBlur = 8;
        ctx.shadowColor = l.color;
        ctx.fillRect(l.x, l.y - l.size * 2, l.size, l.size * 3);
        ctx.restore();
      } else {
        ctx.fillRect(l.x, l.y, l.size, l.size);
      }
    });
    ctx.globalAlpha = 1.0;
  }

  // ---- 3. 両国花火 ----
  function spawnFirework() {
    const x = w * (0.45 + Math.random() * 0.3);
    const y = h * (0.15 + Math.random() * 0.15);
    const colors = ['#ff6b6b', '#ffd166', '#7fdbff', '#f7f7f7', '#ff9edb'];
    const color = colors[Math.floor(Math.random() * colors.length)];
    const numParticles = 45;
    const particles = [];
    for (let i = 0; i < numParticles; i++) {
      const angle = (i / numParticles) * Math.PI * 2;
      const speed = 1.2 + Math.random() * 1.5;
      particles.push({ angle, speed, x, y });
    }
    fireworks.push({ x, y, color, particles, life: 1.0 });
  }

  function drawFireworks() {
    if (t > nextFireworkAt) {
      spawnFirework();
      nextFireworkAt = t + 2 + Math.random() * 3;
    }

    fireworks.forEach(f => {
      f.life -= 0.01;
      ctx.save();
      ctx.globalAlpha = Math.max(0, f.life);
      ctx.fillStyle = f.color;
      ctx.shadowBlur = 10;
      ctx.shadowColor = f.color;
      f.particles.forEach(p => {
        const dist = (1 - f.life) * 80 * p.speed;
        const px = f.x + Math.cos(p.angle) * dist;
        const py = f.y + Math.sin(p.angle) * dist + Math.pow(1 - f.life, 2) * 40; 
        ctx.beginPath();
        ctx.arc(px, py, 1.5, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.restore();
    });
    fireworks = fireworks.filter(f => f.life > 0);
  }

  // ---- 4. 🌟東京スカイツリー（3部位のカラーシフト） ----
  function drawSkytree() {
    const tx = w * 0.27;//角度？
    const bottom = h * 0.58;//高さ
    const top = h * 0.05;
    const towerH = bottom - top;
    const baseW = w * 0.08;

    // 時間(t)に応じて色を変化させる（HSLカラー）
    // 下から上へ光の波が移動するように、部位ごとにhue（色相）を+60度ずらす
    const speed = 20; 
    const hue1 = (t * speed) % 360;      // 部位1: 心柱・トラス
    const hue2 = (t * speed + 60) % 360; // 部位2: 天望デッキ
    const hue3 = (t * speed + 120) % 360;// 部位3: 天望回廊〜ゲイン塔

    const col1 = `hsl(${hue1}, 80%, 65%)`;
    const col2 = `hsl(${hue2}, 90%, 70%)`;
    const col3 = `hsl(${hue3}, 90%, 75%)`;

    ctx.save();

  // ==========================================
    // 部位1: 心柱と鉄骨トラス
    // ==========================================
    const deck1Y = bottom - towerH * 0.5;
    
    // 心柱（中心の太い柱）
    ctx.shadowBlur = 20;
    ctx.shadowColor = col1;
    ctx.strokeStyle = `hsl(${hue1}, 60%, 85%)`;
    // 根元を少し太くしたい場合はここの数値を上げる (例: w * 0.008)
    ctx.lineWidth = Math.max(2.0, w * 0.014); 
    ctx.beginPath();
    ctx.moveTo(tx, bottom);
    ctx.lineTo(tx, deck1Y);
    ctx.stroke();

    // 鉄骨（細かい網目）
    ctx.shadowBlur = 0;
    ctx.strokeStyle = `hsla(${hue1}, 70%, 75%, 0.5)`; // 少しだけ透明度を下げてハッキリさせました
    
    const steps = 30;
    for (let i = 0; i < steps; i++) {
      let p1 = i / steps;
      let p2 = (i + 1) / steps;
      let y1 = bottom - (towerH * 0.65 * p1);
      let y2 = bottom - (towerH * 0.65 * p2);
      
      let w1 = baseW * Math.pow(1 - p1, 1.8);
      let w2 = baseW * Math.pow(1 - p2, 1.8);

      ctx.beginPath();
      
      // 🌟 ここがポイント：下(p1=0)ほど太く、上(p1=1)ほど細くする
      // 例: 一番下は太さ 3.5、一番上は太さ 0.5 になります
      ctx.lineWidth = 0.5 + (1 - p1) * 3.0; 

      ctx.moveTo(tx - w1 / 2, y1); ctx.lineTo(tx + w2 / 2, y2);
      ctx.moveTo(tx + w1 / 2, y1); ctx.lineTo(tx - w2 / 2, y2);
      ctx.moveTo(tx - w1 / 2, y1); ctx.lineTo(tx + w1 / 2, y1);
      
      ctx.stroke(); // ループの中で毎回太さを変えて描画する
    }

    // ==========================================
    // 部位2: 天望デッキ（第1展望台）
    // ==========================================
    const deck1H = towerH * 0.06;//下の柱は変わらない
    const deck1W = baseW * 0.7;
    
    // 中間部の芯
    const deck2Y = bottom - towerH * 0.7;//この数値が大きいほど、上の四角形が上の方へ
    ctx.shadowBlur = 15;
    ctx.shadowColor = col2;
    ctx.strokeStyle = `hsl(${hue2}, 100%, 85%)`;
    ctx.lineWidth = Math.max(9, w * 0.005);
    ctx.beginPath();
    ctx.moveTo(tx, deck1Y - deck1H);
    ctx.lineTo(tx, deck2Y);
    ctx.stroke();

    // デッキ本体（下から広がってすぼまるリアルな形）
    ctx.shadowBlur = 40;
    ctx.shadowColor = col2;
    ctx.fillStyle = `hsl(${hue2}, 90%, 50%)`; 
    ctx.beginPath();
    ctx.moveTo(tx - deck1W * 0.15, deck1Y);//←
    ctx.lineTo(tx + deck1W * 0.15, deck1Y);//→
    ctx.lineTo(tx + deck1W * 0.3, deck1Y - deck1H * 0.35); // 最大幅
    ctx.lineTo(tx + deck1W * 0.3, deck1Y - deck1H); // 上部
    ctx.lineTo(tx - deck1W * 0.35, deck1Y - deck1H);
    ctx.lineTo(tx - deck1W * 0.4, deck1Y - deck1H * 0.45);
    ctx.closePath();
    ctx.fill();
    
    ctx.strokeStyle = col2;
    ctx.lineWidth = 10.7;//光沢
    ctx.stroke();

    // 窓の帯光
    ctx.fillStyle = `hsl(${hue2}, 100%, 75%)`;
    ctx.fillRect(tx - deck1W * 48, deck1Y - deck1H * 5, deck1W * 0.96, deck1H * 15);

    // ==========================================
    // 部位3: 天望回廊（第2展望台）〜ゲイン塔
    // ==========================================
    const deck2H = towerH * 0.05;//これも上の段の太さ
    const deck2W = baseW * 0.35;//これも上の段の長さ

    ctx.shadowBlur = 20;
    ctx.shadowColor = col3;

    // 天望回廊本体
    ctx.fillStyle = `hsl(${hue3}, 80%, 15%)`;
    ctx.beginPath();
    ctx.moveTo(tx - deck2W * 0.4, deck2Y);
    ctx.lineTo(tx + deck2W * 0.4, deck2Y);//こちら上段(上の方の四角形)
    ctx.lineTo(tx + deck2W * 0.4, deck2Y - deck2H);//こちら下段
    ctx.lineTo(tx - deck2W * 0.4, deck2Y - deck2H);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = col3;
    ctx.stroke();

    // 回廊の特徴的な「斜めの螺旋スロープ」の光
    ctx.strokeStyle = `hsl(${hue3}, 100%, 80%)`;
    ctx.lineWidth = 5;
    ctx.beginPath();
    ctx.moveTo(tx - deck2W * 0.3, deck2Y - deck2H * 0.8);
    ctx.lineTo(tx + deck2W * 0.3, deck2Y - deck2H * 0.8);//0.45は横線の長さ 0.8は斜めかどうか？
    ctx.stroke();

    // ゲイン塔（頂上アンテナ）
    ctx.strokeStyle = `hsl(${hue3}, 60%, 50%)`;
    ctx.lineWidth = Math.max(0.3, w * 0.005);
    ctx.beginPath();
    ctx.moveTo(tx, deck2Y - deck2H);
    ctx.lineTo(tx, top);
    ctx.stroke();

    // アンテナの細かい段々
    ctx.lineWidth = 2;
    for (let i = 1; i <= 5; i++) {
      let gy = top + (deck2Y - deck2H - top) * (i / 6);
      let gw = deck2W * 0.3 * (i / 6);//上段の横の線
      ctx.beginPath();
      ctx.moveTo(tx - gw, gy);
      ctx.lineTo(tx + gw, gy);
      ctx.stroke();
    }

    ctx.restore();
  }

  // ---- 5. 回向院（右側のシルエット） ----
  function drawEkoin() {
    const baseY = h * 0.55;
    ctx.save();
    ctx.fillStyle = '#0a0812';

    const cx = w * 0.85;
    const roofW = w * 0.25;
    const roofH = h * 0.08;
    
    ctx.beginPath();
    ctx.moveTo(cx - roofW / 2, baseY);
    ctx.quadraticCurveTo(cx - roofW / 2 - w * 0.02, baseY - roofH * 0.55, cx - roofW * 0.32, baseY - roofH);
    ctx.quadraticCurveTo(cx, baseY - roofH * 1.35, cx + roofW * 0.32, baseY - roofH);
    ctx.quadraticCurveTo(cx + roofW / 2 + w * 0.02, baseY - roofH * 0.55, cx + roofW / 2, baseY);
    ctx.closePath();
    ctx.fill();

    ctx.fillRect(cx - roofW * 0.34, baseY - roofH * 0.55, roofW * 0.68, roofH * 0.6);
    ctx.fillStyle = 'rgba(255,190,110,0.55)';
    for (let i = 0; i < 6; i++) {
      const wx = cx - roofW * 0.30 + i * (roofW * 0.6 / 5);
      ctx.fillRect(wx, baseY - roofH * 0.45, roofW * 0.04, roofH * 0.3);
    }
    ctx.restore();
  }

  // ---- 6. 隅田川 ----
  function drawRiver() {
    const riverY = h * 0.55; 
    const grad = ctx.createLinearGradient(0, riverY, 0, h);
    grad.addColorStop(0, 'rgba(16, 12, 28, 0.95)');
    grad.addColorStop(1, 'rgba(5, 3, 8, 0.98)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, riverY, w, h - riverY);

    ctx.strokeStyle = 'rgba(180, 150, 255, 0.08)';
    ctx.lineWidth = 1;
    for (let y = riverY + 2; y < h; y += 6) {
      const depth = (y - riverY) / (h - riverY);
      const amp = 1.5 + depth * 5;
      ctx.beginPath();
      for (let x = 0; x <= w; x += 20) {
        const yy = y + Math.sin(x * 0.02 + t * 1.2 + depth * 5) * amp;
        if (x === 0) ctx.moveTo(x, yy);
        else ctx.lineTo(x, yy);
      }
      ctx.stroke();
    }
  }

  // ---- 7. 屋形船 ----
  function drawBoats() {
    boats.forEach(b => {
      const x = ((b.baseX + t * 12 * b.speed) % (w + 200)) - 100;
      const bobY = Math.sin(t * 1.5 + b.bob) * 2 * b.depth;
      const y = b.y + bobY;
      const scale = 0.5 + b.depth * 0.8;

      ctx.save();
      ctx.translate(x, y);
      ctx.scale(scale, scale);

      ctx.fillStyle = '#050308';
      ctx.beginPath();
      ctx.moveTo(-26, 0);
      ctx.quadraticCurveTo(-30, 8, -20, 10);
      ctx.lineTo(20, 10);
      ctx.quadraticCurveTo(30, 8, 26, 0);
      ctx.closePath();
      ctx.fill();

      ctx.fillRect(-16, -10, 32, 10);

      ctx.save();
      ctx.shadowBlur = 12;
      ctx.shadowColor = '#ffb347';
      ctx.fillStyle = '#ffcf8a';
      ctx.beginPath();
      ctx.arc(0, -14, 3.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      ctx.globalAlpha = 0.3;
      ctx.fillStyle = '#ffb347';
      ctx.beginPath();
      ctx.ellipse(0, 16, 10, 3, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;

      ctx.restore();
    });
  }

  // ---- 8. 元柳橋（手前） ----
  function drawBridge() {
    const bridgeY = h * 0.65;
    const leftX = w * -0.05; 
    const rightX = w * 0.65;
    const archTop = bridgeY - h * 0.12;

    ctx.save();
    ctx.strokeStyle = '#120a06';
    ctx.fillStyle = '#120a06';
    
    ctx.lineWidth = h * 0.03;
    ctx.beginPath();
    ctx.moveTo(leftX, bridgeY + h * 0.05);
    ctx.quadraticCurveTo((leftX + rightX) / 2, archTop, rightX, bridgeY + h * 0.05);
    ctx.stroke();

    ctx.lineWidth = h * 0.007;
    ctx.beginPath();
    ctx.moveTo(leftX, bridgeY - h * 0.02);
    ctx.quadraticCurveTo((leftX + rightX) / 2, archTop - h * 0.03, rightX, bridgeY - h * 0.02);
    ctx.stroke();

    for (let i = 0; i <= 10; i++) {
      const p = i / 10;
      const x = leftX + (rightX - leftX) * p;
      const archY = bridgeY - Math.sin(p * Math.PI) * (bridgeY - archTop) * 0.55;
      ctx.beginPath();
      ctx.moveTo(x, archY - h * 0.03);
      ctx.lineTo(x, archY + h * 0.02);
      ctx.stroke();
    }

    ctx.fillStyle = '#050308';
    [0.2, 0.4, 0.7, 0.85].forEach((p, i) => {
      if (p > 1 || p < 0) return;
      const x = leftX + (rightX - leftX) * p;
      const archY = bridgeY - Math.sin(p * Math.PI) * (bridgeY - archTop) * 0.55;
      const bob = Math.sin(t * 3 + i) * 1.5;
      ctx.beginPath();
      ctx.ellipse(x, archY - h * 0.04 + bob, h * 0.007, h * 0.016, 0, 0, Math.PI * 2);
      ctx.fill();
    });
    ctx.restore();

    lanterns.forEach((l) => {
      const actualP = l.p * 1.2 - 0.1;
      if (actualP < -0.1 || actualP > 1.1) return;
      const x = leftX + (rightX - leftX) * actualP;
      const archY = bridgeY - Math.sin(actualP * Math.PI) * (bridgeY - archTop) * 0.55;
      const flick = 0.8 + Math.sin(t * 8 + l.flicker) * 0.2;
      
      ctx.save();
      ctx.globalAlpha = flick;
      ctx.shadowBlur = 20;
      ctx.shadowColor = '#ff8833';
      ctx.fillStyle = '#ffdfaa';
      ctx.beginPath();
      ctx.ellipse(x, archY - h * 0.05, h * 0.01, h * 0.015, 0, 0, Math.PI * 2);
      ctx.fill();
      
      ctx.globalAlpha = flick * 0.4;
      ctx.beginPath();
      ctx.ellipse(x, archY - h * 0.01, h * 0.02, h * 0.005, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    });
  }

  // ---- 9. UI装飾 ----
  function drawUI() {
    ctx.save();
    ctx.font = `bold italic ${h * 0.04}px "Arial Black", Impact, sans-serif`;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';
    
    ctx.shadowBlur = 10;
    ctx.shadowColor = '#05d5e7';
    ctx.fillStyle = '#ffffff';
    ctx.fillText("SMD-07", w * 0.96, h * 0.98);
    
    ctx.shadowBlur = 0;
    ctx.fillStyle = '#05d5e7';
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
    
    drawSkyAndMoon();
    drawCityscape();
    drawFireworks();
    drawSkytree();
    drawEkoin();
    drawRiver();
    drawBoats();
    drawBridge();
    drawUI();

    raf = requestAnimationFrame(draw);
  }
  draw();

  return function stop() {
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', resize);
  };
}