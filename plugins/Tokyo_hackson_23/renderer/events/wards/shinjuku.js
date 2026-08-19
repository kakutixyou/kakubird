// shinjuku.js
export const key = 'shinjuku';
export const label = '新宿区：密集する摩天楼とイエローグラウンド';

export function run(canvas) {
  const ctx = canvas.getContext('2d');
  let w, h, raf, t = 0;

  const resize = () => {
    w = canvas.width = canvas.clientWidth;
    h = canvas.height = canvas.clientHeight;
  };
  window.addEventListener('resize', resize);
  resize();

  const neonColors = ['#ff2a6d', '#05d5e7', '#d300c5', '#ffff00', '#00ff9f'];

  // ---- ビル群と「窓の照明パターン」の生成 ----
  function generateBuildings(count, depth) {
    const buildings = [];
    for (let i = 0; i < count; i++) {
      const neons = [];
      if (depth === 'near' && Math.random() > 0.3) {
        const neonCount = Math.floor(Math.random() * 4) + 1;
        for (let j = 0; j < neonCount; j++) {
          neons.push({
            y: Math.random() * 0.6,
            h: 0.05 + Math.random() * 0.1,
            color: neonColors[Math.floor(Math.random() * neonColors.length)],
            flicker: Math.random() * 0.1,
          });
        }
      }
      
      // 🏙️ ビルの窓（照明）の点灯パターンを事前計算
      const pattern = [];
      const lightingDensity = depth === 'far' ? 0.6 : 0.2; // 奥は少し暗め、手前は明るく
      for (let r = 0; r < 120; r++) {
        const row = [];
        for (let c = 0; c < 40; c++) {
          if (Math.random() > lightingDensity) {
            const rand = Math.random();
            let color = 'rgba(255, 245, 210, 0.85)'; // 温かみのある白
            if (rand > 0.8) color = 'rgba(200, 230, 255, 0.9)'; // 青白いオフィス光
            else if (rand > 0.6) color = 'rgba(255, 220, 100, 0.9)'; // 黄色い光
            row.push(color);
          } else {
            row.push(null); // 消灯
          }
        }
        pattern.push(row);
      }

      buildings.push({
        x: Math.random(),
        w: (0.1 + Math.random() * 0.15) * (depth === 'near' ? 1.5 : 1),
        // 高さを増やして海感をなくす
        h: (0.5 + Math.random() * 0.6) * (depth === 'near' ? 1.2 : 1.0), 
        neons,
        pattern
      });
    }
    return buildings.sort((a, b) => a.x - b.x);
  }

  // ビルの数を大幅に増やして密集させる
  const farBuildings = generateBuildings(25, 'far'); 
  const nearBuildings = generateBuildings(15, 'near');

  const rainDrops = Array.from({ length: 150 }, () => ({
    x: Math.random(),
    y: Math.random(),
    speed: 0.015 + Math.random() * 0.02,
    len: 0.02 + Math.random() * 0.04,
  }));

  function drawSky() {
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, '#05050a');
    grad.addColorStop(1, '#151020');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);
  }

  function drawBuildings(buildings, depth, scrollSpeed) {
    const scroll = (t * scrollSpeed) % 1;
    const baseY = h * 0.92; // 地面を画面の極端に下へ押し下げて空きスペースを消す

    buildings.forEach((b) => {
      const bx = ((b.x - scroll) % 1 + 1) % 1 * w;
      const bw = b.w * w;
      const bh = b.h * h;
      const by = baseY - bh;

      // ビル本体
      ctx.fillStyle = depth === 'far' ? '#0a0a0f' : '#111118';
      ctx.fillRect(bx, by, bw, bh);

      // 💡 窓の照明を描画
      const winW = Math.max(1.5, bw * 0.035);
      const winH = Math.max(3, bh * 0.012);
      const gapX = winW * 2.5;
      const gapY = winH * 2.5;
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

      // ネオン看板（手前のみ）
      if (depth === 'near') {
        b.neons.forEach((neon) => {
          const ny = by + bh * neon.y;
          const nh = bh * neon.h;
          const nw = bw * 0.12;
          
          const flicker = 0.7 + Math.sin(t * 15 + neon.flicker * 100) * 0.3;
          
          ctx.shadowBlur = 20;
          ctx.shadowColor = neon.color;
          ctx.fillStyle = neon.color;
          ctx.globalAlpha = flicker;
          
          const isLeft = neon.y > 0.5;
          ctx.fillRect(isLeft ? bx - nw/2 : bx + bw - nw/2, ny, nw, nh);
          
          ctx.globalAlpha = 1.0;
          ctx.shadowBlur = 0;
        });
      }
    });
  }

  function drawRain() {
    ctx.strokeStyle = 'rgba(180, 220, 255, 0.4)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    rainDrops.forEach((drop) => {
      drop.y += drop.speed;
      if (drop.y > 1) {
        drop.y = -0.1;
        drop.x = Math.random();
      }
      const px = drop.x * w;
      const py = drop.y * h;
      ctx.moveTo(px, py);
      ctx.lineTo(px - h * drop.len * 0.2, py + h * drop.len);
    });
    ctx.stroke();
  }

  function drawGround() {
    const baseY = h * 0.92;
    
    // 🟨 1. 地面をイエローに変更
    const grad = ctx.createLinearGradient(0, baseY, 0, h);
    grad.addColorStop(0, 'rgba(255, 215, 0, 1)');   // 鮮やかなイエロー
    grad.addColorStop(1, 'rgba(160, 120, 0, 1)');     // 奥行き用の少し暗いイエロー
    ctx.fillStyle = grad;
    ctx.fillRect(0, baseY, w, h - baseY);

    // 🟪 2. 紫色の文字で「02」と表示
    ctx.save();
    ctx.font = `bold italic ${h * 0.05}px "Arial Black", Impact, sans-serif`;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';
    
    // 文字の装飾（紫色の光沢と影）
    ctx.shadowBlur = 8;
    ctx.shadowColor = 'rgba(100, 0, 100, 0.8)';
    ctx.fillStyle = '#8a2be2'; // ブルーバイオレット（紫）
    
    // 右下に配置
    ctx.fillText("02", w * 0.96, h * 0.99);
    
    // 横にSFっぽいブロックラインを添えてUI感を出す
    ctx.shadowBlur = 0;
    ctx.fillStyle = '#8a2be2';
    ctx.fillRect(w * 0.965, h * 0.93, w * 0.015, h * 0.06);
    ctx.restore();
  }

  function draw() {
    t += 0.016;
    ctx.clearRect(0, 0, w, h);
    
    drawSky();
    drawBuildings(farBuildings, 'far', 0.005); // 奥はゆっくりスクロール
    drawBuildings(nearBuildings, 'near', 0.015); // 手前は少し早くスクロール
    drawGround();
    drawRain();

    raf = requestAnimationFrame(draw);
  }
  draw();

  return function stop() {
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', resize);
  };
}