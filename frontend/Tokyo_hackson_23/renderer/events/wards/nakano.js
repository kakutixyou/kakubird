// nakano.js
export const key = 'nakano';
export const label = '中野区：電脳ブロードウェイとラムネの泡';

/**
 * 中野区の演出（Canvas型）。
 * 背景色が 緑 → 紫 → 青 → ラムネ色 と不思議に移り変わり続ける。
 * 新宿の高層ビルとは対照的に、横に広く密集した「雑居ビル（ブロードウェイ）」を表現。
 * 無数のサブカルチックな極彩色ネオン看板が壁面を埋め尽くす。
 * 前景にはデジタルなラムネの気泡と、レトロゲーム風の3Dグリッド床を配置。
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

  // ---- 1. 背景カラーサイクル（元のアイデアを継承） ----
  const stops = [
    { r: 46,  g: 196, b: 133 },  // 緑（サブカルポップ）
    { r: 142, g: 68,  b: 173 },  // 紫（アングラ・ミステリアス）
    { r: 41,  g: 128, b: 185 },  // 青（サイバー）
    { r: 130, g: 215, b: 235 },  // ラムネ水色
  ];
  const STAGE_SEC = 7; 
  const CYCLE_SEC = STAGE_SEC * stops.length;

  function lerp(a, b, x) { return a + (b - a) * x; }
  function currentColor() {
    const cyclePos = (t % CYCLE_SEC) / STAGE_SEC;
    const i0 = Math.floor(cyclePos) % stops.length;
    const i1 = (i0 + 1) % stops.length;
    const localT = cyclePos - Math.floor(cyclePos);
    const eased = localT * localT * (3 - 2 * localT);
    const a = stops[i0];
    const b = stops[i1];
    return {
      r: lerp(a.r, b.r, eased),
      g: lerp(a.g, b.g, eased),
      b: lerp(a.b, b.b, eased),
      stageIndex: i0,
    };
  }

  // ---- 2. 雑居ビルと大量のネオン看板生成 ----
  const signColors = ['#00ff9f', '#ff2a6d', '#fff066', '#d300c5', '#05d5e7', '#ffae19'];
  
  function generateBroadwayBuildings(count, depth) {
    const buildings = [];
    for (let i = 0; i < count; i++) {
      // 中野は新宿より横幅が広く、高さが不揃いな雑居ビルのイメージ
      const width = 0.15 + Math.random() * 0.2; 
      const height = depth === 'far' 
        ? 0.4 + Math.random() * 0.3 
        : 0.3 + Math.random() * 0.45;

      // 壁面にひしめく看板（アニメショップ、時計屋、ゲーセンのイメージ）
      const signs = [];
      const signDensity = depth === 'far' ? 10 : 25;
      for (let j = 0; j < signDensity; j++) {
        signs.push({
          x: Math.random() * 0.9,      // ビル内の相対X
          y: Math.random() * 0.9,      // ビル内の相対Y
          w: 0.05 + Math.random() * 0.15,
          h: 0.03 + Math.random() * 0.08,
          color: signColors[Math.floor(Math.random() * signColors.length)],
          blinkRate: Math.random() * 0.05,
          isVertical: Math.random() > 0.6, // 縦長看板も混ぜる
        });
      }

      buildings.push({
        x: Math.random(), // 0.0 ~ 1.0の正規化座標
        w: width,
        h: height,
        signs
      });
    }
    return buildings.sort((a, b) => a.x - b.x);
  }

  const farBuildings = generateBroadwayBuildings(20, 'far');
  const nearBuildings = generateBroadwayBuildings(12, 'near');

  // ---- 3. デジタル・ラムネ気泡の生成 ----
  function makeBubble(startAtBottom) {
    return {
      x: Math.random(),
      y: startAtBottom ? 1.1 : Math.random(),
      r: 1.5 + Math.random() * (Math.random() > 0.9 ? 6 : 3), 
      speed: 0.1 + Math.random() * 0.15,
      wobbleAmp: 0.005 + Math.random() * 0.015,
      wobbleSpeed: 2 + Math.random() * 3,
      phase: Math.random() * Math.PI * 2,
      isMarble: Math.random() > 0.85,
    };
  }
  const bubbles = Array.from({ length: 45 }, () => makeBubble(false));

  // ==========================================
  // 描画ルーチン
  // ==========================================

  function drawSky(col) {
    const angle = t * 0.1;
    const cx = w / 2, cy = h / 2;
    const rad = Math.max(w, h);
    
    // 回転する不思議なグラデーション
    const grad = ctx.createLinearGradient(
      cx - Math.cos(angle) * rad, cy - Math.sin(angle) * rad,
      cx + Math.cos(angle) * rad, cy + Math.sin(angle) * rad
    );
    const baseColor = `${col.r|0}, ${col.g|0}, ${col.b|0}`;
    
    grad.addColorStop(0, `rgba(${baseColor}, 0.15)`);
    grad.addColorStop(0.5, `rgba(${baseColor}, 0.4)`);
    grad.addColorStop(1, `rgba(10, 15, 25, 1)`); // 足元は暗く
    
    ctx.fillStyle = '#05070a'; // ベースの暗闇
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);
  }

  function drawBuildings(buildings, depth, scrollSpeed) {
    const scroll = (t * scrollSpeed) % 1;
    const baseY = h * 0.85; // 床の高さを設定

    buildings.forEach((b) => {
      const bx = ((b.x - scroll) % 1 + 1) % 1 * w;
      const bw = b.w * w;
      const bh = b.h * h;
      const by = baseY - bh;

      // ビルのシルエット
      ctx.fillStyle = depth === 'far' ? '#080a12' : '#121520';
      ctx.fillRect(bx, by, bw, bh);
      // 輪郭線（サイバー感）
      ctx.strokeStyle = depth === 'far' ? 'rgba(50, 100, 150, 0.2)' : 'rgba(50, 150, 200, 0.4)';
      ctx.lineWidth = 1;
      ctx.strokeRect(bx, by, bw, bh);

      // 看板の描画
      b.signs.forEach((s) => {
        let sw = bw * s.w;
        let sh = bh * s.h;
        if (s.isVertical) {
          const tmp = sw; sw = sh * 0.3; sh = tmp * 3;
        }
        const sx = bx + bw * s.x;
        const sy = by + bh * s.y;

        // はみ出し防止
        if (sx + sw > bx + bw - 5) return; 

        // 点滅ロジック
        const flicker = Math.sin(t * 10 + s.phase) > 0.8 ? 0.3 : 1.0;
        const alpha = depth === 'far' ? 0.6 * flicker : 0.9 * flicker;

        ctx.fillStyle = s.color;
        
        // 手前のビルだけ光彩効果をつける（パフォーマンス考慮）
        if (depth === 'near') {
          ctx.shadowBlur = 10;
          ctx.shadowColor = s.color;
        }
        
        ctx.globalAlpha = alpha;
        ctx.fillRect(sx, sy, sw, sh);
        
        // 看板の中の文字っぽい模様（線）
        ctx.fillStyle = '#111';
        ctx.globalAlpha = alpha * 0.8;
        ctx.fillRect(sx + 2, sy + 2, sw - 4, sh - 4);
        
        ctx.globalAlpha = 1.0;
        ctx.shadowBlur = 0;
      });
    });
  }

  // レトロゲーム風のパースペクティブ・グリッド床
  function drawRetroGrid(col) {
    const baseY = h * 0.85;
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, baseY, w, h - baseY);
    ctx.clip();

    const speed = t * 200;
    const gridColor = `rgba(${col.r|0}, ${col.g|0}, ${col.b|0}, 0.5)`;
    
    ctx.strokeStyle = gridColor;
    ctx.lineWidth = 2;

    // 縦線（放射状）
    const fov = w * 0.8;
    for (let x = -w * 2; x <= w * 3; x += 100) {
      ctx.beginPath();
      ctx.moveTo(w / 2, baseY);
      ctx.lineTo(x, h);
      ctx.stroke();
    }

    // 横線（奥から手前へ迫ってくる）
    for (let y = 0; y < 20; y++) {
      // 0〜1の進行度を曲線にしてパースを表現
      const progress = ((y * 20 + speed) % 400) / 400; 
      const yPos = baseY + (h - baseY) * Math.pow(progress, 2.5);
      
      ctx.beginPath();
      ctx.moveTo(0, yPos);
      ctx.lineTo(w, yPos);
      ctx.globalAlpha = progress; // 手前に来るほど濃く
      ctx.stroke();
    }
    
    ctx.restore();
    ctx.globalAlpha = 1.0;
  }

  function drawBubbles() {
    bubbles.forEach((b) => {
      b.y -= b.speed * 0.01;
      if (b.y < -0.1) {
        Object.assign(b, makeBubble(true));
      }
      
      // ゆらゆら揺れる動き
      const bx = (b.x + Math.sin(t * b.wobbleSpeed + b.phase) * b.wobbleAmp) * w;
      const by = b.y * h;

      if (b.isMarble) {
        // ラムネのビー玉（ポップでサイバーな球体）
        const grad = ctx.createRadialGradient(bx - b.r*0.3, by - b.r*0.3, 0, bx, by, b.r);
        grad.addColorStop(0, 'rgba(255, 255, 255, 0.9)');
        grad.addColorStop(0.4, 'rgba(5, 213, 231, 0.8)'); // Tokyo_s_23_wardsの花火色にリンク
        grad.addColorStop(1, 'rgba(211, 0, 197, 0.3)');
        ctx.beginPath();
        ctx.arc(bx, by, b.r, 0, Math.PI * 2);
        ctx.fillStyle = grad;
        ctx.fill();
      } else {
        // 通常のデジタル気泡
        ctx.beginPath();
        ctx.arc(bx, by, b.r, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255, 255, 255, 0.2)';
        ctx.fill();
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    });
  }

  function drawUI() {
    ctx.save();
    ctx.font = `bold italic ${h * 0.04}px "Arial Black", Impact, sans-serif`;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';
    
    // 影と光彩
    ctx.shadowBlur = 10;
    ctx.shadowColor = '#05d5e7';
    ctx.fillStyle = '#ffffff'; 
    
    // 右下に配置 (中野区のコード14をあしらう)
    ctx.fillText("NKN-14", w * 0.96, h * 0.98);
    
    // UIのアクセントライン
    ctx.shadowBlur = 0;
    ctx.fillStyle = '#05d5e7';
    ctx.fillRect(w * 0.965, h * 0.94, w * 0.015, h * 0.04);
    ctx.restore();
  }

  function draw() {
    t += 0.016;
    const col = currentColor();
    
    ctx.clearRect(0, 0, w, h);
    
    drawSky(col);
    
    // 奥のビル群
    drawBuildings(farBuildings, 'far', 0.005);
    
    // 手前のビル群
    drawBuildings(nearBuildings, 'near', 0.015);
    
    // サイバーなレトログリッド床
    drawRetroGrid(col);
    
    // ラムネの泡
    drawBubbles();
    
    // 前景のUI
    drawUI();

    raf = requestAnimationFrame(draw);
  }
  draw();

  return function stop() {
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', resize);
  };
}