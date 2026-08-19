// shibuya.js
export const key = 'shibuya';
export const label = '渋谷区：ネオン交差点と幻影の巨大魚';

/**
 * 渋谷区の演出（Canvas型）。
 * スクランブル交差点のネオンと群衆の上空を、自作PNGの巨大魚がシュールに泳ぎます。
 * 手前には同じく自作PNGのハチ公が佇む、サイバーパンク×超現実的な景観です。
 * ※画像がない場合は自動的にスキップされ、通常のネオン交差点が表示されます。
 */
export function run(canvas) {
  const ctx = canvas.getContext('2d');
  let w, h, raf, t = 0;

  // 🐟 魚の画像を読み込む（パスは実際の環境に合わせて変更してください）
  const fishImg = new Image();
  fishImg.src = '/assets/fish.png'; // ⚠️ 自作の魚PNGのパス
  let isFishLoaded = false;
  fishImg.onload = () => { isFishLoaded = true; };

  // 🐕 ハチ公の画像を読み込む（パスは実際の環境に合わせて変更してください）
  const hachikoImg = new Image();
  hachikoImg.src = '/assets/hachiko.png'; // ⚠️ 自作のハチ公PNGのパス
  let isHachikoLoaded = false;
  hachikoImg.onload = () => { isHachikoLoaded = true; };

  const resize = () => {
    w = canvas.width = canvas.clientWidth;
    h = canvas.height = canvas.clientHeight;
  };
  window.addEventListener('resize', resize);
  resize();

  // ---- 群衆（パーティクル）の生成 ----
  const crowd = Array.from({ length: 350 }, () => createPerson());

  function createPerson() {
    const startZone = Math.floor(Math.random() * 4);
    const angle = (startZone * 90 + 135 + (Math.random() - 0.5) * 45) * (Math.PI / 180);
    
    let x, y;
    const offset = 0.6; 
    if (startZone === 0) { x = -offset; y = -offset; }
    else if (startZone === 1) { x = 1 + offset; y = -offset; }
    else if (startZone === 2) { x = 1 + offset; y = 1 + offset; }
    else { x = -offset; y = 1 + offset; }

    return {
      x, y,
      vx: Math.cos(angle) * (0.001 + Math.random() * 0.002),
      vy: Math.sin(angle) * (0.001 + Math.random() * 0.002),
      color: `hsl(${Math.random() * 360}, 80%, 70%)`,
      size: 0.003 + Math.random() * 0.002,
    };
  }

  // ---- 1. スクランブル交差点 ----
  function drawCrossing() {
    ctx.fillStyle = '#0a0b10'; // 暗いアスファルト
    ctx.fillRect(0, 0, w, h);

    ctx.save();
    ctx.translate(w / 2, h / 2);
    ctx.rotate(0.35); 
    ctx.scale(1, 0.7); 

    ctx.fillStyle = 'rgba(255, 255, 255, 0.15)';
    const stripeWidth = w * 0.03;
    const gap = w * 0.04;
    const crossSize = w * 0.45;

    for (let x = -crossSize; x <= crossSize; x += gap) {
      ctx.fillRect(x, -crossSize * 1.2, stripeWidth, crossSize * 2.4);
    }
    for (let y = -crossSize; y <= crossSize; y += gap) {
      ctx.fillRect(-crossSize * 1.2, y, crossSize * 2.4, stripeWidth);
    }
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
    ctx.lineWidth = 4;
    ctx.strokeRect(-crossSize * 1.2, -crossSize * 1.2, crossSize * 2.4, crossSize * 2.4);

    ctx.restore();
  }

  // ---- 2. 交差点を行き交う群衆 ----
  function drawCrowd() {
    ctx.save();
    ctx.translate(w / 2, h / 2);
    ctx.rotate(0.35);
    ctx.scale(1, 0.7);

    crowd.forEach((p) => {
      p.x += p.vx;
      p.y += p.vy;

      if (p.x < -1 || p.x > 1 || p.y < -1 || p.y > 1) {
        Object.assign(p, createPerson());
      }

      ctx.beginPath();
      ctx.arc(p.x * w, p.y * w, p.size * w, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.shadowBlur = 8;
      ctx.shadowColor = p.color;
      ctx.fill();
    });

    ctx.restore();
  }

  // ---- 3. 街頭の巨大ネオンビジョン ----
  function drawGiantScreens() {
    const flicker1 = 0.5 + Math.sin(t * 10) * 0.3;
    const flicker2 = 0.5 + Math.cos(t * 8) * 0.3;
    const flicker3 = 0.5 + Math.sin(t * 12 + 2) * 0.3;

    ctx.globalCompositeOperation = 'screen';

    const grad1 = ctx.createRadialGradient(0, 0, 0, 0, 0, w * 0.6);
    grad1.addColorStop(0, `rgba(0, 255, 200, ${flicker1 * 0.2})`);
    grad1.addColorStop(1, 'rgba(0, 255, 200, 0)');
    ctx.fillStyle = grad1;
    ctx.fillRect(0, 0, w, h);

    const grad2 = ctx.createRadialGradient(w, 0, 0, w, 0, w * 0.7);
    grad2.addColorStop(0, `rgba(255, 50, 150, ${flicker2 * 0.2})`);
    grad2.addColorStop(1, 'rgba(255, 50, 150, 0)');
    ctx.fillStyle = grad2;
    ctx.fillRect(0, 0, w, h);
    
    ctx.globalCompositeOperation = 'source-over';
  }

  // ---- 4. シュールな巨大魚（浮世絵風） ----
  function drawSurrealFish() {
    if (!isFishLoaded) return;

    ctx.save();
    const imgW = fishImg.width;
    const imgH = fishImg.height;
    
    // 画面幅の70%程度の巨大サイズに調整
    const scale = (w * 0.7) / imgW;
    const drawW = imgW * scale;
    const drawH = imgH * scale;

    // 空中をゆっくり回遊するような動き（サイン波で揺らす）
    const swayX = Math.cos(t * 0.8) * (w * 0.1);
    const bobY = Math.sin(t * 1.2) * (h * 0.05);

    // 画面中央より少し上を定位置とする
    const x = (w - drawW) / 2 + swayX;
    const y = h * 0.15 + bobY;

    // サイバーパンクな街に溶け込むように、少しだけネオンの照り返し（影）をつける
    ctx.shadowBlur = 40;
    ctx.shadowColor = 'rgba(0, 255, 255, 0.4)';
    ctx.globalAlpha = 0.85; // 幻影のように少し透かす
    
    ctx.drawImage(fishImg, x, y, drawW, drawH);
    ctx.restore();
  }

  // ---- 5. 忠犬ハチ公 ----
  function drawHachikoImage() {
    if (!isHachikoLoaded) return;

    ctx.save();
    const imgW = hachikoImg.width;
    const imgH = hachikoImg.height;
    
    // 画面の高さの30%程度のサイズ
    const scale = (h * 0.3) / imgH; 
    const drawW = imgW * scale;
    const drawH = imgH * scale;

    // 左下（UIに被らない位置）に鎮座させる
    const x = w * 0.05;
    const y = h - drawH - h * 0.05;

    // ネオンの光を受けるシルエット効果
    ctx.shadowBlur = 20;
    ctx.shadowColor = 'rgba(255, 50, 150, 0.5)';
    
    ctx.drawImage(hachikoImg, x, y, drawW, drawH);
    ctx.restore();
  }

  // ---- 6. UI装飾 ----
  function drawUI() {
    ctx.save();
    ctx.font = `bold italic ${h * 0.04}px "Arial Black", Impact, sans-serif`;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';
    
    ctx.shadowBlur = 10;
    ctx.shadowColor = '#00ffcc';
    ctx.fillStyle = '#ffffff';
    ctx.fillText("SHB-13", w * 0.96, h * 0.98);
    
    ctx.shadowBlur = 0;
    ctx.fillStyle = '#00ffcc'; 
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
    
    drawCrossing();
    drawCrowd();
    drawGiantScreens();
    
    // PNG画像の描画（読み込まれていない場合は内部でスキップ）
    drawSurrealFish();
    drawHachikoImage();
    
    drawUI();

    raf = requestAnimationFrame(draw);
  }
  draw();

  return function stop() {
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', resize);
  };
}

/**
 * @param {object} ward - wardManifestのエントリ
 * @param {object} ctx  - 呼び出し側が渡す共通API
 */
export function onReveal(ward, ctx) {
  ctx.unlockBadge?.(`${ward.code}_first_visit`);
  ctx.playSound?.('reveal_common');
  ctx.showToast?.(`${ward.ward}「${ward.motif}」を引き当てました`);
}