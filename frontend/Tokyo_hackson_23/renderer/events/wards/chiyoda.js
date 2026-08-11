export const key = 'chiyoda';
export const label = '千代田区：歴史の記憶とモダンアート、カメラの眼';

export function run(canvas) {
  const ctx = canvas.getContext('2d');
  let w, h, raf, t = 0;

  const resize = () => {
    w = canvas.width = canvas.clientWidth;
    h = canvas.height = canvas.clientHeight;
  };
  window.addEventListener('resize', resize);
  resize();

  // ---- モダンアート(MOMAT) ＆ 公文書(Archives) のパーティクル ----
  const particles = Array.from({ length: 45 }, () => {
    const isArt = Math.random() > 0.4;
    return {
      x: Math.random(),
      y: Math.random(),
      vy: -(0.001 + Math.random() * 0.002), // 下から上へ漂う
      rot: Math.random() * Math.PI * 2,
      rotSpeed: (Math.random() - 0.5) * 0.015,
      size: 0.02 + Math.random() * 0.05,
      type: isArt ? (Math.random() > 0.5 ? 'circle' : 'triangle') : 'document',
      // アートは原色系、公文書は古い紙（羊皮紙）のような淡い色
      color: isArt 
        ? ['rgba(255, 70, 100, 0.4)', 'rgba(50, 150, 255, 0.4)', 'rgba(255, 210, 50, 0.4)'][Math.floor(Math.random() * 3)]
        : 'rgba(245, 235, 210, 0.25)' 
    };
  });

  // 1. 背景のグラデーション
  function drawBackground() {
    const grad = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, Math.max(w, h));
    grad.addColorStop(0, '#1a1f2b'); // 知的な深いネイビー
    grad.addColorStop(1, '#080a0f');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);
  }

  // 2. 中央の巨大なカメラの絞り（日本カメラ博物館）
  function drawCameraAperture() {
    const cx = w / 2;
    const cy = h / 2;
    const radius = Math.min(w, h) * 0.4;
    const blades = 8;
    
    // 呼吸するように絞りが開閉する
    const opening = 0.2 + Math.sin(t * 0.8) * 0.1; 

    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(t * 0.05); // ゆっくり回転

    // レンズの外枠
    ctx.beginPath();
    ctx.arc(0, 0, radius, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    ctx.lineWidth = 2;
    ctx.stroke();

    // 絞り羽根の描画
    ctx.strokeStyle = 'rgba(150, 180, 220, 0.15)';
    ctx.fillStyle = 'rgba(20, 30, 45, 0.3)';
    ctx.lineWidth = 1.5;

    for (let i = 0; i < blades; i++) {
      ctx.save();
      ctx.rotate((Math.PI * 2 / blades) * i);
      ctx.beginPath();
      
      const innerR = radius * opening;
      ctx.moveTo(innerR, 0);
      ctx.lineTo(radius, radius * 0.4);
      ctx.lineTo(radius * 0.9, -radius * 0.1);
      ctx.closePath();
      
      ctx.fill();
      ctx.stroke();
      ctx.restore();
    }
    
    // レンズのガラス反射（ハイライト）
    const highlight = ctx.createLinearGradient(-radius, -radius, radius, radius);
    highlight.addColorStop(0, 'rgba(255, 255, 255, 0.0)');
    highlight.addColorStop(0.4, 'rgba(255, 255, 255, 0.05)');
    highlight.addColorStop(0.5, 'rgba(255, 255, 255, 0.0)');
    ctx.fillStyle = highlight;
    ctx.beginPath();
    ctx.arc(0, 0, radius, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }

  // 3. アートと文書のパーティクル描画（近代美術館＆公文書館）
  function drawParticles() {
    particles.forEach(p => {
      p.y += p.vy;
      p.rot += p.rotSpeed;
      if (p.y < -0.1) {
        p.y = 1.1; // 画面上に消えたら下から再登場
        p.x = Math.random();
      }

      const px = p.x * w;
      const py = p.y * h;
      const size = p.size * Math.min(w, h);

      ctx.save();
      ctx.translate(px, py);
      ctx.rotate(p.rot);
      ctx.fillStyle = p.color;

      if (p.type === 'document') {
        // 公文書（矩形と、その中のテキスト風の線）
        const docW = size * 0.8;
        const docH = size * 1.2;
        ctx.fillRect(-docW / 2, -docH / 2, docW, docH);
        
        ctx.fillStyle = 'rgba(255, 255, 255, 0.15)';
        ctx.fillRect(-docW * 0.3, -docH * 0.3, docW * 0.6, docH * 0.05);
        ctx.fillRect(-docW * 0.3, -docH * 0.1, docW * 0.6, docH * 0.05);
        ctx.fillRect(-docW * 0.3,  docH * 0.1, docW * 0.4, docH * 0.05);
      } else if (p.type === 'circle') {
        // モダンアート（円）
        ctx.beginPath();
        ctx.arc(0, 0, size / 2, 0, Math.PI * 2);
        ctx.fill();
      } else if (p.type === 'triangle') {
        // モダンアート（三角形）
        ctx.beginPath();
        ctx.moveTo(0, -size / 2);
        ctx.lineTo(size / 2, size / 2);
        ctx.lineTo(-size / 2, size / 2);
        ctx.closePath();
        ctx.fill();
      }
      ctx.restore();
    });
  }

  // 4. 両サイドのフィルム演出（日本カメラ博物館）
  function drawFilmStrip() {
    const stripW = Math.max(30, w * 0.05);
    const holeW = stripW * 0.4;
    const holeH = holeW * 0.7;
    const gap = holeH * 2.5;
    const offset = (t * 60) % gap; // スクロールアニメーション

    // フィルムの黒い帯
    ctx.fillStyle = 'rgba(5, 7, 10, 0.85)';
    ctx.fillRect(0, 0, stripW, h);
    ctx.fillRect(w - stripW, 0, stripW, h);

    // フィルムのパーフォレーション（穴）- 光が漏れているような演出
    ctx.fillStyle = 'rgba(220, 240, 255, 0.7)';
    ctx.shadowBlur = 15;
    ctx.shadowColor = 'rgba(150, 200, 255, 0.8)';

    for (let y = -gap; y < h + gap; y += gap) {
      // 左の穴
      ctx.fillRect(stripW / 2 - holeW / 2, y + offset, holeW, holeH);
      // 右の穴
      ctx.fillRect(w - stripW / 2 - holeW / 2, y + offset, holeW, holeH);
    }
    ctx.shadowBlur = 0; // シャドウをリセット
  }

  function draw() {
    t += 0.016;
    ctx.clearRect(0, 0, w, h);
    
    drawBackground();
    drawCameraAperture();
    drawParticles();
    drawFilmStrip();

    raf = requestAnimationFrame(draw);
  }
  draw();

  return function stop() {
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', resize);
  };
}