// ota.js
export const key = 'ota';
export const label = '大田区：水止舞の雨音と輝く大森麦わら細工';

export function run(canvas) {
  const ctx = canvas.getContext('2d');
  let w, h, raf, t = 0;

  const resize = () => {
    w = canvas.width = canvas.clientWidth;
    h = canvas.height = canvas.clientHeight;
  };
  window.addEventListener('resize', resize);
  resize();

  // ---- 寺社仏閣（水止舞の舞台）と町並みの生成 ----
  function generateStructures(count, depth) {
    const items = [];
    for (let i = 0; i < count; i++) {
      const isShrine = Math.random() > 0.7; // 3割が寺社や鳥居
      items.push({
        x: Math.random(),
        w: isShrine ? 0.12 + Math.random() * 0.08 : 0.08 + Math.random() * 0.06,
        h: isShrine ? 0.3 + Math.random() * 0.2 : 0.15 + Math.random() * 0.15,
        isShrine
      });
    }
    return items.sort((a, b) => a.x - b.x);
  }

  const farStructures = generateStructures(20, 'far'); 
  const nearStructures = generateStructures(12, 'near');

  // ---- 大森麦わら細工（幾何学的な黄金の模様） ----
  const strawCrafts = Array.from({ length: 15 }, () => ({
    x: Math.random(),
    y: Math.random() * 0.6 + 0.1, // 空中を漂う
    size: 0.03 + Math.random() * 0.05,
    angle: Math.random() * Math.PI * 2,
    spinSpeed: (Math.random() - 0.5) * 0.02,
    driftSpeed: 0.0005 + Math.random() * 0.001,
    type: Math.floor(Math.random() * 3) // 模様のタイプ
  }));

  // ---- 水止舞の雨と波紋 ----
  const raindrops = Array.from({ length: 80 }, () => ({
    x: Math.random(),
    y: Math.random(),
    speed: 0.02 + Math.random() * 0.03,
    len: 0.03 + Math.random() * 0.05
  }));

  const ripples = Array.from({ length: 20 }, () => ({
    x: Math.random(),
    life: Math.random(), // 0〜1で波紋の広がりを管理
    speed: 0.01 + Math.random() * 0.01
  }));

  function drawSky() {
    // 雨乞い・雨止めの神秘的な雰囲気を表す、深みのある青緑（ティール）のグラデーション
    const grad = ctx.createLinearGradient(0, 0, 0, h * 0.9);
    grad.addColorStop(0, '#0a1520');
    grad.addColorStop(0.5, '#1a3040');
    grad.addColorStop(1, '#2a4d5e');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);
  }

  function drawStructures(items, depth, scrollSpeed) {
    const scroll = (t * scrollSpeed) % 1;
    const baseY = h * 0.92;

    items.forEach((item) => {
      const bx = ((item.x - scroll) % 1 + 1) % 1 * w;
      const bw = item.w * w;
      const bh = item.h * h;
      const by = baseY - bh;

      ctx.fillStyle = depth === 'far' ? '#111a22' : '#0a0f15';

      if (item.isShrine) {
        // ⛩ 寺社仏閣のシルエット（反り屋根）
        ctx.fillRect(bx + bw * 0.1, by, bw * 0.8, bh); // 本堂
        
        // 大きな屋根
        ctx.beginPath();
        ctx.moveTo(bx - bw * 0.2, by);
        ctx.quadraticCurveTo(bx + bw * 0.5, by - bh * 0.3, bx + bw * 1.2, by);
        ctx.lineTo(bx + bw * 0.8, by + bh * 0.1);
        ctx.lineTo(bx + bw * 0.2, by + bh * 0.1);
        ctx.fill();
      } else {
        // 🏘 一般的な町屋・建物
        ctx.fillRect(bx, by, bw, bh);
      }
    });
  }

  function drawStrawCrafts() {
    // 麦わら細工の黄金色の輝き
    ctx.strokeStyle = 'rgba(218, 165, 32, 0.85)'; // ゴールデンロッド
    ctx.shadowBlur = 15;
    ctx.shadowColor = 'rgba(255, 215, 0, 0.6)';

    strawCrafts.forEach((craft) => {
      craft.x -= craft.driftSpeed; // ゆっくり左へ
      if (craft.x < -craft.size) craft.x = 1 + craft.size;
      craft.angle += craft.spinSpeed;

      const cx = craft.x * w;
      const cy = craft.y * h;
      const cs = craft.size * h;

      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(craft.angle);
      ctx.lineWidth = 2;

      ctx.beginPath();
      if (craft.type === 0) {
        // 菱形の編み込み模様
        for (let i = 0; i < 4; i++) {
          ctx.rect(-cs/2, -cs/2, cs, cs);
          ctx.rotate(Math.PI / 4);
        }
      } else if (craft.type === 1) {
        // 星・麻の葉のような放射状の模様
        for (let i = 0; i < 8; i++) {
          ctx.moveTo(0, 0);
          ctx.lineTo(0, cs);
          ctx.lineTo(cs * 0.3, cs * 0.3);
          ctx.rotate(Math.PI / 4);
        }
      } else {
        // 多角形の重なり
        for (let i = 0; i < 6; i++) {
          ctx.moveTo(0, cs);
          ctx.lineTo(cs * 0.866, cs * 0.5);
          ctx.lineTo(cs * 0.866, -cs * 0.5);
          ctx.rotate(Math.PI / 3);
        }
      }
      ctx.stroke();
      ctx.restore();
    });
    ctx.shadowBlur = 0; // リセット
  }

  function drawRainAndRipples() {
    const baseY = h * 0.92;

    // 雨粒の描画
    ctx.strokeStyle = 'rgba(150, 200, 220, 0.3)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    raindrops.forEach((drop) => {
      drop.y += drop.speed;
      if (drop.y > 1) {
        drop.y = -0.1;
        drop.x = Math.random();
      }
      const px = drop.x * w;
      const py = drop.y * h;
      ctx.moveTo(px, py);
      ctx.lineTo(px - h * drop.len * 0.1, py + h * drop.len);
    });
    ctx.stroke();

    // 水面（地面）の波紋の描画
    ripples.forEach((ripple) => {
      ripple.life += ripple.speed;
      if (ripple.life > 1) {
        ripple.life = 0;
        ripple.x = Math.random();
      }

      const rx = ripple.x * w;
      const maxRadius = w * 0.05;
      const radius = ripple.life * maxRadius;
      const alpha = 1 - ripple.life; // 広がるほど透明に

      ctx.strokeStyle = `rgba(150, 200, 255, ${alpha * 0.5})`;
      ctx.beginPath();
      // 奥行きを出すために楕円で波紋を描画
      ctx.ellipse(rx, baseY + (ripple.life * h * 0.05), radius, radius * 0.2, 0, 0, Math.PI * 2);
      ctx.stroke();
    });
  }

  function drawGround() {
    const baseY = h * 0.92;
    
    // 🟦 1. 水と歴史を感じさせる深い藍色の地面
    const grad = ctx.createLinearGradient(0, baseY, 0, h);
    grad.addColorStop(0, '#102a3a');
    grad.addColorStop(1, '#051015');
    ctx.fillStyle = grad;
    ctx.fillRect(0, baseY, w, h - baseY);

    // 🟨 2. 麦わら細工を思わせるゴールドの文字で「11」（大田区のJISコード）
    ctx.save();
    ctx.font = `bold italic ${h * 0.05}px "Arial Black", Impact, sans-serif`;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';
    
    ctx.shadowBlur = 10;
    ctx.shadowColor = 'rgba(218, 165, 32, 0.8)';
    ctx.fillStyle = '#FFD700';
    
    ctx.fillText("11", w * 0.96, h * 0.99);
    
    ctx.shadowBlur = 0;
    ctx.fillStyle = '#DAA520'; 
    ctx.fillRect(w * 0.965, h * 0.93, w * 0.015, h * 0.06);
    ctx.restore();
  }

  function draw() {
    t += 0.016;
    ctx.clearRect(0, 0, w, h);
    
    drawSky();
    drawStructures(farStructures, 'far', 0.002);
    drawStrawCrafts(); // 建物と雨の間に、輝く麦わら細工を配置
    drawStructures(nearStructures, 'near', 0.008);
    drawGround();
    drawRainAndRipples(); // 水止舞を表現する雨と波紋

    raf = requestAnimationFrame(draw);
  }
  draw();

  return function stop() {
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', resize);
  };
}