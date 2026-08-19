export const key = 'taito';
export const label = '台東区：歴史と伝統の下町、舞い散る桜';

/**
 * @param {object} ward - wardManifestのエントリ
 * @param {object} ctx  - 共通API
 */
export function onReveal(ward, ctx) {
  ctx.unlockBadge?.(`${ward.code}_first_visit`);
  ctx.playSound?.('reveal_common');
  ctx.showToast?.(`${ward.ward}「${ward.motif || '歴史と伝統の下町'}」を引き当てました`);
}

/**
 * 台東区の演出（Canvas型）
 *
 * モチーフ：
 * - 浅草や上野の伝統建築（瓦屋根、五重塔）
 * - 舞い散る桜の花びら
 * - 障子の温かい光と赤提灯
 * - 雷門を思わせる朱色とゴールドのコントラスト
 */
export function run(canvas) {
  const ctx = canvas.getContext('2d');

  let w;
  let h;
  let raf;
  let t = 0;
  const startTime = performance.now();
  const REVEAL_MS = 2200;

  const farStructures = [];
  const nearStructures = [];
  const sakuraPetals = [];

  // --------------------------------
  // サイズ変更と初期化
  // --------------------------------
  const resize = () => {
    const dpr = window.devicePixelRatio || 1;

    w = canvas.clientWidth;
    h = canvas.clientHeight;

    // 高解像度ディスプレイ（Retina等）をサポートするためのスケーリング
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    createStructures();
    createSakura();
  };

  window.addEventListener('resize', resize);

  // --------------------------------
  // 共通関数
  // --------------------------------
  function random(min, max) {
    return min + Math.random() * (max - min);
  }

  function easeOutCubic(x) {
    return 1 - Math.pow(1 - x, 3);
  }

  // --------------------------------
  // オブジェクトの生成
  // --------------------------------
  function createStructures() {
    farStructures.length = 0;
    nearStructures.length = 0;

    // 奥の建物（小さめ）
    for (let i = 0; i < 25; i++) {
      farStructures.push(generateStructure('far'));
    }
    farStructures.sort((a, b) => a.x - b.x);

    // 手前の建物（大きめ、五重塔や提灯あり）
    for (let i = 0; i < 12; i++) {
      nearStructures.push(generateStructure('near'));
    }
    nearStructures.sort((a, b) => a.x - b.x);
  }

  function generateStructure(depth) {
    const isPagoda = depth === 'near' && Math.random() > 0.85;
    return {
      x: random(0, 1),
      w: isPagoda ? 0.08 : random(0.1, 0.25),
      h: isPagoda ? random(0.7, 0.8) : random(0.15, 0.35) * (depth === 'near' ? 1.5 : 1),
      isPagoda: isPagoda,
      hasLantern: !isPagoda && depth === 'near' && Math.random() > 0.4,
      lanternPos: random(0.1, 0.8),
      shojiLight: Math.random() > 0.3
    };
  }

  function createSakura() {
    sakuraPetals.length = 0;
    const count = Math.max(40, Math.floor(w / 10)); // 画面幅に応じて枚数を調整
    
    for (let i = 0; i < count; i++) {
      sakuraPetals.push({
        x: random(0, 1),
        y: random(-1, 1),
        size: random(0.004, 0.008),
        speedY: random(0.002, 0.004),
        speedX: random(-0.001, 0.001),
        angleOffset: random(0, Math.PI * 2),
        spin: random(1, 4),
        alpha: random(0.6, 0.95)
      });
    }
  }

  // --------------------------------
  // 描画：背景（空）
  // --------------------------------
  function drawSky(progress) {
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    // 宵闇をイメージした、深い紫から紅へのグラデーション
    grad.addColorStop(0, '#100515');
    grad.addColorStop(0.5, '#200815');
    grad.addColorStop(1, '#3a1020');
    
    ctx.fillStyle = grad;
    ctx.globalAlpha = progress;
    ctx.fillRect(0, 0, w, h);
    ctx.globalAlpha = 1;
  }

  // --------------------------------
  // 描画：和風建築の町並み
  // --------------------------------
  function drawTownscape(structures, depth, scrollSpeed, progress) {
    if (progress <= 0) return;
    const scroll = (t * scrollSpeed) % 1;
    const baseY = h * 0.92;

    structures.forEach((s) => {
      // 多重スクロールによるループ座標の計算
      const bx = ((s.x - scroll) % 1 + 1) % 1 * w;
      const bw = s.w * w;
      const bh = s.h * h * progress; // 登場時に下からせり上がる演出
      const by = baseY - bh;

      ctx.fillStyle = depth === 'far' ? '#1a0a10' : '#221115';

      // 建物の土台を描画
      ctx.fillRect(bx, by, bw, bh);

      if (s.isPagoda) {
        // 🏯 五重塔の描画
        const tiers = 5;
        const tierHeight = bh / tiers;
        for (let i = 0; i < tiers; i++) {
          const ty = by + i * tierHeight;
          const roofW = bw * (1.2 - i * 0.08); // 上に行くほど少し屋根を狭く
          const roofOverhang = (roofW - bw) / 2;
          
          ctx.beginPath();
          ctx.moveTo(bx - roofOverhang, ty);
          ctx.lineTo(bx + bw + roofOverhang, ty);
          ctx.lineTo(bx + bw, ty - tierHeight * 0.2);
          ctx.lineTo(bx, ty - tierHeight * 0.2);
          ctx.fill();
        }
      } else {
        // 🏮 一般的な和風建築（瓦屋根のシルエット）
        ctx.beginPath();
        ctx.moveTo(bx - bw * 0.1, by);
        ctx.lineTo(bx + bw * 1.1, by);
        ctx.lineTo(bx + bw * 0.9, by - bh * 0.25);
        ctx.lineTo(bx + bw * 0.1, by - bh * 0.25);
        ctx.fill();

        // 障子の温かい光（手前のみ）
        if (depth === 'near' && s.shojiLight) {
          ctx.fillStyle = `rgba(255, 180, 80, ${0.4 * progress})`;
          ctx.fillRect(bx + bw * 0.2, by + bh * 0.3, bw * 0.6, bh * 0.4);
          
          // 障子の桟（さん）
          ctx.fillStyle = '#221115';
          ctx.fillRect(bx + bw * 0.45, by + bh * 0.3, bw * 0.1, bh * 0.4);
          ctx.fillRect(bx + bw * 0.2, by + bh * 0.45, bw * 0.6, bh * 0.1);
        }

        // 赤提灯（手前のみ）
        if (s.hasLantern && depth === 'near') {
          const lx = bx + bw * s.lanternPos;
          const ly = by + bh * 0.1;
          const lw = Math.max(10, bw * 0.15);
          const lh = lw * 1.2;
          
          const flicker = 0.8 + Math.sin(t * 5 + s.lanternPos * 10) * 0.2;

          ctx.shadowBlur = 15;
          ctx.shadowColor = `rgba(255, 50, 0, ${0.8 * progress})`;
          ctx.fillStyle = `rgba(220, 40, 20, ${flicker * progress})`;
          
          ctx.beginPath();
          ctx.ellipse(lx, ly, lw / 2, lh / 2, 0, 0, Math.PI * 2);
          ctx.fill();
          
          ctx.shadowBlur = 0;
          
          // 提灯の黒い帯
          ctx.fillStyle = '#110505';
          ctx.fillRect(lx - lw * 0.3, ly - lh * 0.2, lw * 0.6, lh * 0.05);
          ctx.fillRect(lx - lw * 0.4, ly,           lw * 0.8, lh * 0.05);
          ctx.fillRect(lx - lw * 0.3, ly + lh * 0.2, lw * 0.6, lh * 0.05);
        }
      }
    });
  }

  // --------------------------------
  // 描画：桜の花びら
  // --------------------------------
  function drawSakura(progress) {
    if (progress <= 0.3) return; // 街が現れてから舞い始める
    const sakuraProgress = easeOutCubic(Math.min(1, (progress - 0.3) / 0.7));

    sakuraPetals.forEach((p) => {
      const sway = Math.sin(t * p.spin + p.angleOffset) * 0.003;
      p.y += p.speedY;
      p.x += sway + p.speedX;

      // 画面下部に消えたら上から再配置
      if (p.y > 1) {
        p.y = -0.1;
        p.x = Math.random();
      }

      const px = ((p.x % 1) + 1) % 1 * w;
      const py = p.y * h;
      const sizeH = h * p.size;
      const sizeW = sizeH * 0.6; // 花びらを楕円に

      ctx.save();
      ctx.translate(px, py);
      ctx.rotate(sway * 10);
      
      ctx.fillStyle = `rgba(255, 183, 197, ${p.alpha * sakuraProgress})`;
      ctx.beginPath();
      ctx.ellipse(0, 0, sizeW, sizeH, 0, 0, Math.PI * 2);
      ctx.fill();
      
      ctx.restore();
    });
  }

  // --------------------------------
  // 描画：地面とUI要素
  // --------------------------------
  function drawGround(progress) {
    const baseY = h * 0.92;
    
    // 🟥 雷門のような朱色の地面
    const grad = ctx.createLinearGradient(0, baseY, 0, h);
    grad.addColorStop(0, 'rgba(180, 30, 20, 1)');
    grad.addColorStop(1, 'rgba(80, 10, 10, 1)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, baseY, w, h - baseY);

    if (progress < 0.8) return; // 文字は最後にフェードイン
    const textAlpha = (progress - 0.8) / 0.2;

    // 🟨 ゴールドの文字で「06」（台東区のJISコード）
    ctx.save();
    ctx.font = `bold italic ${h * 0.05}px "Arial Black", Impact, sans-serif`;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';
    
    ctx.shadowBlur = 8;
    ctx.shadowColor = `rgba(255, 200, 0, ${0.6 * textAlpha})`;
    ctx.fillStyle = `rgba(255, 215, 0, ${textAlpha})`;
    ctx.fillText("06", w * 0.96, h * 0.99);
    
    // 和とサイバー感を両立させる横のブロックライン
    ctx.shadowBlur = 0;
    ctx.fillStyle = `rgba(255, 215, 0, ${textAlpha})`;
    ctx.fillRect(w * 0.965, h * 0.93, w * 0.015, h * 0.06);
    ctx.restore();
  }

  // --------------------------------
  // メインループ
  // --------------------------------
  function draw() {
    t += 0.016;
    const elapsed = performance.now() - startTime;
    const progress = easeOutCubic(Math.min(1, elapsed / REVEAL_MS));

    ctx.clearRect(0, 0, w, h);
    
    drawSky(progress);
    drawTownscape(farStructures, 'far', 0.003, progress); 
    drawTownscape(nearStructures, 'near', 0.01, progress);
    drawGround(progress);
    drawSakura(progress);

    raf = requestAnimationFrame(draw);
  }

  // ⚠️【重要】初回描画前に必ずリサイズを実行して縦横サイズ(w, h)を取得する
  resize();
  draw();

  // --------------------------------
  // 停止・クリーンアップ処理
  // --------------------------------
  return function stop() {
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', resize);
  };
}