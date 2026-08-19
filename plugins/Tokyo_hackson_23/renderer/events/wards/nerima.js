// nerima.js
export const key = 'nerima';
export const label = '練馬区：緑豊かな住宅街とアニメの生まれる街';

export function run(canvas) {
  const ctx = canvas.getContext('2d');
  let w, h, raf, t = 0;

  const resize = () => {
    w = canvas.width = canvas.clientWidth;
    h = canvas.height = canvas.clientHeight;
  };
  window.addEventListener('resize', resize);
  resize();

  // ---- のどかな住宅街と木々の生成 ----
  function generateSuburbs(count, depth) {
    const items = [];
    for (let i = 0; i < count; i++) {
      const isTree = Math.random() > 0.6; // 4割が木（緑豊かな環境）
      items.push({
        x: Math.random(),
        w: isTree ? 0.04 + Math.random() * 0.03 : 0.08 + Math.random() * 0.05,
        h: isTree ? 0.2 + Math.random() * 0.15 : 0.15 + Math.random() * 0.1,
        isTree,
        roofType: Math.random() > 0.5 ? 'triangle' : 'flat',
        // 夕暮れ時なので、いくつかの家には温かい明かりを灯す
        lightOn: depth === 'near' && Math.random() > 0.5
      });
    }
    return items.sort((a, b) => a.x - b.x);
  }

  const farSuburbs = generateSuburbs(25, 'far'); 
  const nearSuburbs = generateSuburbs(15, 'near');

  // ---- アニメ調の背景雲 ----
  const clouds = Array.from({ length: 6 }, () => ({
    x: Math.random(),
    y: Math.random() * 0.4, // 画面上部
    w: 0.15 + Math.random() * 0.2,
    h: 0.05 + Math.random() * 0.04,
    speed: 0.0002 + Math.random() * 0.0003
  }));

  // ---- 漫画・アニメ的な「風のエフェクト線」 ----
  const windLines = Array.from({ length: 25 }, () => ({
    x: Math.random(),
    y: Math.random() * 0.8,
    len: 0.1 + Math.random() * 0.2,
    speed: 0.02 + Math.random() * 0.04,
    alpha: 0.1 + Math.random() * 0.3
  }));

  function drawSky() {
    // アニメでよくある「エモーショナルな夕暮れ（マジックアワー）」のグラデーション
    const grad = ctx.createLinearGradient(0, 0, 0, h * 0.8);
    grad.addColorStop(0, '#1a1040'); // 上空は夜の深い青
    grad.addColorStop(0.3, '#502060'); // 紫
    grad.addColorStop(0.6, '#e06050'); // 燃えるような赤
    grad.addColorStop(1, '#ffb070'); // 地平線はオレンジ・ピーチ
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);

    // 雲の描画（ゆっくり右から左へ）
    clouds.forEach(c => {
      c.x -= c.speed;
      if (c.x < -c.w) c.x = 1 + c.w;

      const cx = c.x * w;
      const cy = c.y * h;
      const cw = c.w * w;
      const ch = c.h * h;

      ctx.fillStyle = 'rgba(255, 200, 200, 0.15)'; // 夕日を反射する淡いピンクの雲
      ctx.beginPath();
      ctx.ellipse(cx, cy, cw, ch, 0, 0, Math.PI * 2);
      ctx.ellipse(cx + cw * 0.4, cy - ch * 0.4, cw * 0.6, ch * 0.8, 0, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  function drawLandscape(items, depth, scrollSpeed) {
    const scroll = (t * scrollSpeed) % 1;
    const baseY = h * 0.92;

    items.forEach((item) => {
      const bx = ((item.x - scroll) % 1 + 1) % 1 * w;
      const bw = item.w * w;
      const bh = item.h * h;
      const by = baseY - bh;

      // 遠景は空の色に馴染ませ、近景はシルエットをはっきりさせる
      const baseColor = depth === 'far' ? '#301530' : '#1a0b15';

      if (item.isTree) {
        // 🌳 木のシルエット描画
        ctx.fillStyle = depth === 'far' ? '#251a25' : '#101a15';
        // 幹
        ctx.fillRect(bx + bw * 0.4, by + bh * 0.5, bw * 0.2, bh * 0.5);
        // 葉（丸みのあるアニメ的な表現）
        ctx.beginPath();
        ctx.ellipse(bx + bw * 0.5, by + bh * 0.3, bw * 0.6, bh * 0.4, 0, 0, Math.PI * 2);
        ctx.fill();
      } else {
        // 🏠 住宅の描画
        ctx.fillStyle = baseColor;
        ctx.fillRect(bx, by, bw, bh);

        // 屋根
        ctx.beginPath();
        if (item.roofType === 'triangle') {
          ctx.moveTo(bx - bw * 0.1, by);
          ctx.lineTo(bx + bw * 0.5, by - bh * 0.4);
          ctx.lineTo(bx + bw * 1.1, by);
        } else {
          ctx.moveTo(bx - bw * 0.05, by);
          ctx.lineTo(bx + bw * 1.05, by);
          ctx.lineTo(bx + bw * 1.05, by - bh * 0.15);
          ctx.lineTo(bx - bw * 0.05, by - bh * 0.15);
        }
        ctx.fill();

        // 💡 窓の明かり（帰宅時間の温かみ）
        if (!item.isTree && item.lightOn) {
          ctx.fillStyle = 'rgba(255, 220, 120, 0.9)'; // 温かいオレンジ色の光
          const winW = bw * 0.2;
          const winH = bh * 0.25;
          ctx.fillRect(bx + bw * 0.2, by + bh * 0.3, winW, winH);
          ctx.fillRect(bx + bw * 0.6, by + bh * 0.3, winW, winH);
        }
      }
    });
  }

  function drawWindEffects() {
    ctx.lineWidth = 1.5;
    windLines.forEach(wind => {
      wind.x -= wind.speed; // 右から左へ疾走感のある風
      if (wind.x < -wind.len) {
        wind.x = 1.5;
        wind.y = Math.random() * 0.8;
      }

      const px = wind.x * w;
      const py = wind.y * h;
      const plen = wind.len * w;

      // 線にグラデーションをかけて「効果線」っぽくする
      const grad = ctx.createLinearGradient(px, py, px + plen, py);
      grad.addColorStop(0, `rgba(255, 255, 255, 0)`);
      grad.addColorStop(0.5, `rgba(255, 255, 255, ${wind.alpha})`);
      grad.addColorStop(1, `rgba(255, 255, 255, 0)`);

      ctx.strokeStyle = grad;
      ctx.beginPath();
      ctx.moveTo(px, py);
      ctx.lineTo(px + plen, py);
      ctx.stroke();
    });
  }

  function drawGround() {
    const baseY = h * 0.92;
    
    // 🟩 1. 地面を農業や公園を思わせる「鮮やかな緑」に変更
    const grad = ctx.createLinearGradient(0, baseY, 0, h);
    grad.addColorStop(0, '#2e8b57'); // シーグリーン
    grad.addColorStop(1, '#006400'); // ダークグリーン
    ctx.fillStyle = grad;
    ctx.fillRect(0, baseY, w, h - baseY);

    // ⬜ 2. アニメタイトルロゴのような白抜きの「20」（練馬区のJISコード）
    ctx.save();
    ctx.font = `bold italic ${h * 0.05}px "Arial Black", Impact, sans-serif`;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';
    
    ctx.shadowBlur = 10;
    ctx.shadowColor = 'rgba(0, 255, 100, 0.6)';
    ctx.fillStyle = '#f0fff0'; // 爽やかなハニーデューホワイト
    
    ctx.fillText("20", w * 0.96, h * 0.99);
    
    // UIブロックラインもグリーン系で統一
    ctx.shadowBlur = 0;
    ctx.fillStyle = '#98fb98'; // パステルグリーン
    ctx.fillRect(w * 0.965, h * 0.93, w * 0.015, h * 0.06);
    ctx.restore();
  }

  function draw() {
    t += 0.016;
    ctx.clearRect(0, 0, w, h);
    
    drawSky(); // 夕暮れの空と雲
    drawLandscape(farSuburbs, 'far', 0.002);   // 奥の住宅や木々
    drawLandscape(nearSuburbs, 'near', 0.008); // 手前の住宅や木々
    drawGround(); // 緑の地面
    drawWindEffects(); // 漫画・アニメ的な風のエフェクト

    raf = requestAnimationFrame(draw);
  }
  draw();

  return function stop() {
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', resize);
  };
}