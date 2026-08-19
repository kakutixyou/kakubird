export const key = 'toshima';
export const label = '豊島区：サンシャインシティ 池袋夜景演出';

/**
 * @param {object} ward - wardManifestのエントリ
 * @param {object} ctx  - 呼び出し側が渡す共通API
 */
export function onReveal(ward, ctx) {
  ctx.unlockBadge?.(`${ward.code}_first_visit`);
  ctx.playSound?.('reveal_common');
  ctx.showToast?.(
    `${ward.ward}「${ward.motif}」を引き当てました`
  );
}

/**
 * 豊島区の演出（Canvas型）
 *
 * モチーフ：
 * - サンシャイン60と池袋の高層ビル群
 * - 水族館（カワウソ、イルカ、ホオジロザメ）
 *
 * 新規演出構成：
 * 1. 画面全体が深い水族館の青に包まれる
 * 2. イルカが跳ね上がり、ホオジロザメやカワウソが飛び出すように横切る
 * 3. 水族館の青い空間が縮小し、サンシャイン60の根本へと収束する
 * 4. 水の収束を合図に、周囲のビルと池袋の夜景が展開される
 */
export function run(canvas) {
  const ctx = canvas.getContext('2d');

  let w;
  let h;
  let raf;
  let t = 0;

  const startTime = performance.now();
  
  // アニメーションのフェーズ時間を延長し、水族館→都市の２段構成にする
  const AQUARIUM_MS = 2200; // 水族館が全画面のフェーズ
  const SHRINK_MS = 1000;   // 水が縮小する時間
  const CITY_MS = 2500;     // 街が現れる時間

  const buildings = [];
  const windows = [];
  const particles = [];

  // --------------------------------
  // サイズ変更
  // --------------------------------
  const resize = () => {
    const dpr = window.devicePixelRatio || 1;

    w = canvas.clientWidth;
    h = canvas.clientHeight;

    canvas.width = w * dpr;
    canvas.height = h * dpr;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    createBuildings();
    createWindows();
    createParticles();
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

  function easeInOutCubic(x) {
    return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
  }

  function easeOutBack(x) {
    const c1 = 1.70158;
    const c3 = c1 + 1;
    return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2);
  }

  // --------------------------------
  // 初期化関数群（ビル・窓・粒子）
  // --------------------------------
  function createBuildings() {
    buildings.length = 0;
    const count = 15;
    for (let i = 0; i < count; i++) {
      buildings.push({
        x: random(-0.05, 0.95),
        width: random(0.035, 0.09),
        height: random(0.12, 0.42),
        depth: random(0.65, 1.0),
        alpha: random(0.35, 0.75)
      });
    }
    buildings.sort((a, b) => a.height - b.height);
  }

  function createWindows() {
    windows.length = 0;
    for (let i = 0; i < 70; i++) {
      windows.push({
        x: random(0, 1),
        y: random(0.2, 0.8),
        size: random(1, 2.5),
        phase: random(0, Math.PI * 2),
        blue: Math.random() > 0.65
      });
    }
  }

  function createParticles() {
    particles.length = 0;
    for (let i = 0; i < 35; i++) {
      particles.push({
        x: random(0, w),
        y: random(0, h),
        size: random(1, 3),
        speed: random(0.1, 0.5),
        phase: random(0, Math.PI * 2)
      });
    }
  }

  // --------------------------------
  // 水棲生物の描画（パス）
  // --------------------------------
  function drawShark(ctx, x, y, scale) {
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(scale, scale);
    ctx.fillStyle = 'rgba(160, 210, 240, 0.9)'; // 海中のシルエット
    
    // サメの体（口を閉じたスマートなフォルム）
    ctx.beginPath();
    ctx.moveTo(35, 0); // 鼻先
    ctx.quadraticCurveTo(15, -12, 0, -12); // 頭の上
    ctx.lineTo(-8, -30); // 背びれ上
    ctx.lineTo(-15, -12); // 背びれ下
    ctx.quadraticCurveTo(-35, -8, -50, -5); // 背中〜尾の付け根
    ctx.lineTo(-65, -20); // 尾びれ上
    ctx.quadraticCurveTo(-55, 0, -65, 20); // 尾びれ下
    ctx.lineTo(-50, 5); // 尾びれ下〜付け根
    ctx.quadraticCurveTo(-20, 15, 0, 10); // 腹
    ctx.lineTo(-10, 25); // 胸びれ先
    ctx.lineTo(5, 10); // 胸びれ前
    ctx.quadraticCurveTo(20, 5, 35, 0); // 鼻先へ戻る
    ctx.fill();

    // 閉じた口のライン
    ctx.strokeStyle = 'rgba(20, 50, 80, 0.5)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(25, 3);
    ctx.lineTo(10, 5);
    ctx.stroke();

    ctx.restore();
  }

  function drawDolphin(ctx, x, y, scale, angle) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(angle);
    ctx.scale(scale, scale);
    ctx.fillStyle = 'rgba(220, 240, 255, 0.95)';
    
    // イルカの体
    ctx.beginPath();
    ctx.moveTo(25, 0); // おでこ
    ctx.lineTo(35, 2); // くちばし（吻）
    ctx.lineTo(35, 5);
    ctx.lineTo(23, 6);
    ctx.quadraticCurveTo(10, 15, -10, 15); // 腹
    ctx.lineTo(-5, 25); // 胸びれ
    ctx.lineTo(5, 12);
    ctx.quadraticCurveTo(-20, 10, -40, 5); // 尾の付け根
    ctx.lineTo(-55, 15); // 尾びれ
    ctx.quadraticCurveTo(-48, 0, -55, -15);
    ctx.lineTo(-40, -5);
    ctx.quadraticCurveTo(-20, -15, -15, -18); // 背中
    ctx.lineTo(-25, -35); // 背びれ
    ctx.lineTo(-10, -18);
    ctx.quadraticCurveTo(10, -15, 25, 0);
    ctx.fill();
    ctx.restore();
  }

  function drawOtter(ctx, x, y, scale, angle) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(angle);
    ctx.scale(scale, scale);
    ctx.fillStyle = 'rgba(255, 225, 200, 0.9)';
    
    // カワウソの体
    ctx.beginPath();
    ctx.moveTo(20, 0); // 鼻
    ctx.quadraticCurveTo(20, -10, 10, -12); // 頭
    ctx.lineTo(8, -18); // 耳
    ctx.lineTo(4, -12);
    ctx.quadraticCurveTo(-15, -15, -30, -5); // 長い背中
    ctx.lineTo(-50, -5); // しっぽ
    ctx.lineTo(-30, 5);
    ctx.quadraticCurveTo(-15, 15, 0, 12); // 腹
    ctx.lineTo(-5, 22); // 手足
    ctx.lineTo(5, 12);
    ctx.quadraticCurveTo(15, 10, 20, 0);
    ctx.fill();
    ctx.restore();
  }

  // --------------------------------
  // 水族館フェーズ ＆ 収束アニメーション
  // --------------------------------
  function drawAquariumPhase(elapsed, cityProgress) {
    const centerX = w * 0.5;
    const glowY = h * 0.69;

    const fullRadius = Math.max(w, h) * 1.5;
    const finalRadius = w * 0.12;

    let currentRadius = fullRadius;
    let shrinkProgress = 0;

    // 水族館の縮小計算
    if (elapsed > AQUARIUM_MS) {
      shrinkProgress = Math.min(1, (elapsed - AQUARIUM_MS) / SHRINK_MS);
      const ease = easeInOutCubic(shrinkProgress);
      currentRadius = fullRadius - (fullRadius - finalRadius) * ease;
    }
    // 完全に縮小した後の微細な揺らぎ（元のdrawAquariumGlowの動き）
    if (shrinkProgress >= 1) {
      currentRadius = finalRadius + Math.sin(t * 0.7) * 0.015 * w;
    }

    ctx.save();
    
    // 水の世界をクリッピングマスクでくり抜く
    ctx.beginPath();
    ctx.arc(centerX, glowY, currentRadius, 0, Math.PI * 2);
    ctx.clip();

    // 水族館の背景色（全画面時は深い青、縮小時は光のグラデーション）
    const gradient = ctx.createRadialGradient(centerX, glowY, 0, centerX, glowY, currentRadius);
    if (shrinkProgress < 1) {
      gradient.addColorStop(0, '#00b4db'); // 明るい水色
      gradient.addColorStop(1, '#001b3a'); // 深海の色
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, w, h);
    } else {
      // 縮小完了後は元の水族館の光の演出へシームレスに移行
      gradient.addColorStop(0, `rgba(40,190,240,${0.14 * cityProgress})`);
      gradient.addColorStop(0.45, `rgba(30,140,210,${0.08 * cityProgress})`);
      gradient.addColorStop(1, 'rgba(0,100,180,0)');
      ctx.fillStyle = gradient;
      ctx.fillRect(centerX - currentRadius, glowY - currentRadius, currentRadius * 2, currentRadius * 2);
    }

    // 縮小完了に合わせて生物をフェードアウト
    ctx.globalAlpha = Math.max(0, 1 - shrinkProgress * 1.5);

    if (ctx.globalAlpha > 0) {
      const baseScale = Math.min(w, h) * 0.0018;

      // 1. サメ（画面奥をゆっくり横切る）
      const sharkX = centerX - w * 0.3 + (elapsed / (AQUARIUM_MS + SHRINK_MS)) * w * 0.7;
      const sharkY = glowY - h * 0.05;
      drawShark(ctx, sharkX, sharkY, baseScale * 0.8);

      // 2. イルカ（下から弧を描いて飛び出してくる）
      const dProg = Math.min(1, elapsed / AQUARIUM_MS);
      const dolphinX = centerX - w * 0.2 + dProg * w * 0.4;
      const dolphinY = glowY + h * 0.1 - Math.sin(dProg * Math.PI) * (h * 0.25);
      const dolphinAngle = (Math.PI / 4) - (dProg * Math.PI / 2);
      drawDolphin(ctx, dolphinX, dolphinY, baseScale * 0.9, dolphinAngle);

      // 3. カワウソ（波打つように泳ぐ）
      const oProg = Math.min(1, elapsed / (AQUARIUM_MS * 1.2));
      const otterX = centerX + w * 0.35 - oProg * w * 0.7;
      const otterY = glowY + Math.sin(elapsed / 150) * 15;
      drawOtter(ctx, otterX, otterY, baseScale * 0.7, Math.sin(elapsed / 150) * 0.1);
    }

    // 元の演出にあった「水中の光をイメージした波」を縮小後に表示
    ctx.globalAlpha = shrinkProgress;
    if (shrinkProgress > 0) {
      ctx.strokeStyle = `rgba(80,210,240,${0.12 * cityProgress})`;
      ctx.lineWidth = 1;
      for (let i = 0; i < 4; i++) {
        ctx.beginPath();
        const waveY = glowY + i * 10;
        for (let x = centerX - w * 0.12; x < centerX + w * 0.12; x += 8) {
          const wave = Math.sin(x * 0.035 + t * 2 + i) * 3;
          if (x === centerX - w * 0.12) ctx.moveTo(x, waveY + wave);
          else ctx.lineTo(x, waveY + wave);
        }
        ctx.stroke();
      }
    }

    ctx.restore();
  }

  // --------------------------------
  // 以下、既存の都市描画機能群（進行度を cityProgress に変更）
  // --------------------------------

  function drawSky(progress) {
    const gradient = ctx.createLinearGradient(0, 0, 0, h);
    gradient.addColorStop(0, '#050817');
    gradient.addColorStop(0.45, '#10172c');
    gradient.addColorStop(1, '#241b32');
    ctx.fillStyle = gradient;
    ctx.globalAlpha = progress;
    ctx.fillRect(0, 0, w, h);
    ctx.globalAlpha = 1;
  }

  function drawBuildings(progress) {
    if (progress <= 0) return;
    const baseY = h * 0.78;

    buildings.forEach((building, index) => {
      const bx = w * building.x;
      const bw = w * building.width;
      const bh = h * building.height;
      const by = baseY - bh;

      ctx.fillStyle = `rgba(10,17,29,${building.alpha * progress})`;
      ctx.fillRect(bx, by, bw, bh);

      ctx.strokeStyle = `rgba(90,120,150,${0.25 * progress})`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(bx, by);
      ctx.lineTo(bx + bw, by);
      ctx.stroke();

      for (let wy = by + 10; wy < baseY - 8; wy += 12) {
        for (let wx = bx + 7; wx < bx + bw - 4; wx += 11) {
          const flicker = 0.12 + Math.sin(t * 1.5 + index * 2 + wy) * 0.04;
          ctx.fillStyle = `rgba(255,210,150,${Math.max(0.04, flicker) * progress})`;
          ctx.fillRect(wx, wy, 3, 4);
        }
      }
    });
  }

  function drawSunshine60(progress) {
    if (progress <= 0) return;
    const centerX = w * 0.5;
    const baseY = h * 0.78;
    const buildingWidth = w * 0.20;
    const fullHeight = h * 0.63;

    const buildingProgress = easeOutBack(Math.min(1, progress * 1.18));
    const bh = fullHeight * Math.min(1.08, buildingProgress);
    const topY = baseY - bh;
    const left = centerX - buildingWidth / 2;

    const gradient = ctx.createLinearGradient(left, topY, left + buildingWidth, topY);
    gradient.addColorStop(0, '#17253a');
    gradient.addColorStop(0.5, '#263952');
    gradient.addColorStop(1, '#101b2d');
    ctx.fillStyle = gradient;
    ctx.fillRect(left, topY, buildingWidth, bh);

    ctx.strokeStyle = 'rgba(100,150,185,0.5)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(left, topY); ctx.lineTo(left, baseY);
    ctx.moveTo(left + buildingWidth, topY); ctx.lineTo(left + buildingWidth, baseY);
    ctx.stroke();

    const floors = 18;
    for (let i = 0; i < floors; i++) {
      const fy = topY + (bh / floors) * i;
      ctx.strokeStyle = `rgba(100,140,175,${0.15 + Math.sin(t + i) * 0.03})`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(left, fy); ctx.lineTo(left + buildingWidth, fy);
      ctx.stroke();
    }

    const glowY = baseY - ((Math.sin(t * 0.8) + 1) / 2) * bh;
    const glow = ctx.createLinearGradient(centerX, glowY - h * 0.08, centerX, glowY + h * 0.08);
    glow.addColorStop(0, 'rgba(80,220,255,0)');
    glow.addColorStop(0.5, 'rgba(120,235,255,0.9)');
    glow.addColorStop(1, 'rgba(80,220,255,0)');
    ctx.fillStyle = glow;
    ctx.fillRect(centerX - 2, glowY - h * 0.08, 4, h * 0.16);

    const obsY = topY + bh * 0.055;
    const obsWidth = buildingWidth * 1.18;
    const obsHeight = h * 0.035;
    const obsLeft = centerX - obsWidth / 2;

    const obsGlow = ctx.createRadialGradient(centerX, obsY, 0, centerX, obsY, w * 0.12);
    obsGlow.addColorStop(0, 'rgba(130,235,255,0.55)');
    obsGlow.addColorStop(1, 'rgba(80,180,255,0)');
    ctx.fillStyle = obsGlow;
    ctx.fillRect(centerX - w * 0.13, obsY - w * 0.06, w * 0.26, w * 0.12);

    ctx.fillStyle = 'rgba(95,175,205,0.9)';
    ctx.fillRect(obsLeft, obsY, obsWidth, obsHeight);

    ctx.strokeStyle = 'rgba(130,210,235,0.7)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(centerX, topY); ctx.lineTo(centerX, topY - h * 0.06);
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(centerX, topY - h * 0.06, 2.5, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(150,235,255,0.95)';
    ctx.fill();
  }

  function drawParticles(progress) {
    if (progress <= 0) return;
    particles.forEach((p) => {
      p.y -= p.speed;
      if (p.y < -10) p.y = h + 10;
      const alpha = 0.25 + Math.sin(t * 2 + p.phase) * 0.15;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(100,210,255,${Math.max(0, alpha) * progress})`;
      ctx.fill();
    });
  }

  function drawCityBeams(progress) {
    if (progress < 0.6) return;
    const centerX = w * 0.5;
    const originY = h * 0.23;

    const beamProgress = Math.min(1, (progress - 0.6) / 0.4);
    const beamAlpha = 0.12 * beamProgress;
    const directions = [-0.75, -0.38, 0, 0.38, 0.75];

    directions.forEach((angle, index) => {
      const length = w * 0.45;
      const bx = centerX + Math.sin(angle) * length;
      const by = originY - Math.cos(angle) * length;

      const gradient = ctx.createLinearGradient(centerX, originY, bx, by);
      gradient.addColorStop(0, `rgba(100,220,255,${beamAlpha})`);
      gradient.addColorStop(1, 'rgba(100,220,255,0)');

      ctx.strokeStyle = gradient;
      ctx.lineWidth = index === 2 ? 2 : 1;
      ctx.beginPath();
      ctx.moveTo(centerX, originY);
      ctx.lineTo(bx, by);
      ctx.stroke();
    });
  }

  // --------------------------------
  // メインループ
  // --------------------------------
  function draw() {
    t += 0.016;
    const elapsed = performance.now() - startTime;

    // 前半：水族館フェーズ、後半：都市フェーズ
    // elapsed が AQUARIUM_MS を超えてから都市の描画進捗をスタートする
    let cityProgress = 0;
    if (elapsed > AQUARIUM_MS) {
      cityProgress = easeOutCubic(Math.min(1, (elapsed - AQUARIUM_MS) / CITY_MS));
    }

    ctx.clearRect(0, 0, w, h);

    // 1. 夜空（都市フェーズ進行度）
    drawSky(cityProgress);

    // 2. 池袋の街
    drawBuildings(cityProgress);

    // 3. サンシャイン60
    drawSunshine60(cityProgress);

    // 4. 水族館フェーズ ＆ 収束して元の青い光へ
    drawAquariumPhase(elapsed, cityProgress);

    // 5. 都市の光粒子
    drawParticles(cityProgress);

    // 6. サンシャインから広がる光
    drawCityBeams(cityProgress);

    raf = requestAnimationFrame(draw);
  }

  resize();
  draw();

  // --------------------------------
  // 停止処理
  // --------------------------------
  return function stop() {
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', resize);
  };
}