// shinagawa.js
export const key = 'shinagawa';
export const label = '品川区：八ツ山橋を駆ける光の矢と、交わる軌跡';

export function run(canvas) {
  const ctx = canvas.getContext('2d');
  let w, h, raf, t = 0;

  const resize = () => {
    w = canvas.width = canvas.clientWidth;
    h = canvas.height = canvas.clientHeight;
  };
  window.addEventListener('resize', resize);
  resize();

  // ---- 弓（研ぎ澄まされた直線・光の矢） ----
  const arrows = Array.from({ length: 5 }, () => ({
    x: Math.random() * 2, // 画面外からスタートさせるためのオフセット
    y: 0.2 + Math.random() * 0.5, // 空中を飛ぶ
    speed: 0.04 + Math.random() * 0.03, // かなり速い
    length: 0.15 + Math.random() * 0.1, // 矢（光）の長さ
    color: Math.random() > 0.5 ? '#00e5ff' : '#ffffff'
  }));

  // ---- ヨガ（呼吸）と手話（手の軌跡）を表す柔らかな波 ----
  const ribbons = [
    { color: 'rgba(255, 100, 150, 0.4)', freq: 1.5, amp: 0.1, speed: 0.005, offset: 0 },
    { color: 'rgba(100, 200, 255, 0.4)', freq: 2.0, amp: 0.15, speed: 0.007, offset: Math.PI / 2 },
    { color: 'rgba(150, 255, 150, 0.3)', freq: 1.0, amp: 0.08, speed: 0.004, offset: Math.PI }
  ];

  function drawSky() {
    // 精神を落ち着かせるヨガや弓道に通じる、夜明け前の静謐な空（品川の海辺も意識）
    const grad = ctx.createLinearGradient(0, 0, 0, h * 0.8);
    grad.addColorStop(0, '#0a0a2a');
    grad.addColorStop(0.5, '#1a1a4a');
    grad.addColorStop(1, '#2a3a6a');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);
  }

  function drawYatsuyamaBridge() {
    const baseY = h * 0.8;
    const bridgeHeight = h * 0.15;
    const trussWidth = w * 0.15; // トラス（三角形）の幅
    const scroll = (t * 0.002) % 1; // 鉄橋はゆっくりスクロール
    
    ctx.strokeStyle = '#050510'; // シルエットなので限りなく黒に近い色
    ctx.lineWidth = Math.max(3, h * 0.01);
    ctx.lineJoin = 'round';

    // 鉄橋の下部（土台・道部分）
    ctx.fillStyle = '#0a0a15';
    ctx.fillRect(0, baseY, w, h * 0.12);

    // トラス構造（三角の骨組み）を描画
    ctx.beginPath();
    // 画面外から描画を開始してループを自然に
    for (let x = -trussWidth - (scroll * trussWidth); x < w + trussWidth; x += trussWidth) {
      // 下部水平線
      ctx.moveTo(x, baseY);
      ctx.lineTo(x + trussWidth, baseY);
      
      // 上部水平線
      ctx.moveTo(x + trussWidth * 0.2, baseY - bridgeHeight);
      ctx.lineTo(x + trussWidth * 1.2, baseY - bridgeHeight);

      // 斜めの柱（ジグザグ）
      ctx.moveTo(x, baseY);
      ctx.lineTo(x + trussWidth * 0.5, baseY - bridgeHeight);
      ctx.lineTo(x + trussWidth, baseY);
      
      // 垂直の柱
      ctx.moveTo(x + trussWidth * 0.5, baseY);
      ctx.lineTo(x + trussWidth * 0.5, baseY - bridgeHeight);
    }
    ctx.stroke();
  }

  function drawYogaAndSignLanguageRibbons() {
    // 呼吸の波と、手話で空間に描かれる曲線を「交差するリボン」で表現
    ctx.globalCompositeOperation = 'screen'; // 光の重なりを美しく

    ribbons.forEach((ribbon) => {
      ctx.beginPath();
      for (let x = 0; x <= w; x += 10) {
        // x座標を正規化
        const nx = x / w;
        // 時間とx座標を使ったサイン波で、滑らかなうねりを作る
        const ny = h * 0.5 + Math.sin(nx * Math.PI * ribbon.freq + t * 5 * ribbon.speed + ribbon.offset) * (h * ribbon.amp)
                         + Math.cos(nx * Math.PI * 3 - t * 2) * (h * 0.05); // 複雑な揺らぎを追加
        
        if (x === 0) ctx.moveTo(x, ny);
        else ctx.lineTo(x, ny);
      }
      
      ctx.strokeStyle = ribbon.color;
      ctx.lineWidth = h * 0.04; // 太めの淡い線
      ctx.shadowBlur = 20;
      ctx.shadowColor = ribbon.color;
      ctx.stroke();
    });

    ctx.shadowBlur = 0;
    ctx.globalCompositeOperation = 'source-over'; // 元に戻す
  }

  function drawArrows() {
    // 弓の矢を表現する、一瞬で駆け抜ける鋭い光
    arrows.forEach((arrow) => {
      arrow.x -= arrow.speed; // 右から左へ放たれる
      if (arrow.x < -arrow.length) {
        // 画面外に出たらランダムなタイミングと高さでリロード
        if (Math.random() > 0.95) {
          arrow.x = 1 + arrow.length;
          arrow.y = 0.2 + Math.random() * 0.4;
          arrow.speed = 0.05 + Math.random() * 0.05;
        }
      }

      // 描画範囲内なら描画
      if (arrow.x < 1 + arrow.length && arrow.x > -arrow.length) {
        const px = arrow.x * w;
        const py = arrow.y * h;
        const plen = arrow.length * w;

        // 矢の軌跡（グラデーション）
        const grad = ctx.createLinearGradient(px, py, px + plen, py);
        grad.addColorStop(0, arrow.color);
        grad.addColorStop(1, 'rgba(255, 255, 255, 0)'); // 尻尾は透明に

        ctx.strokeStyle = grad;
        ctx.lineWidth = Math.max(2, h * 0.005);
        ctx.lineCap = 'round';
        ctx.shadowBlur = 10;
        ctx.shadowColor = arrow.color;

        ctx.beginPath();
        ctx.moveTo(px, py);
        ctx.lineTo(px + plen, py);
        ctx.stroke();
      }
    });
    ctx.shadowBlur = 0;
  }

  function drawGround() {
    const baseY = h * 0.92;
    
    // 🟦 1. 品川のウォーターフロントや新幹線などの「近代的・水辺」を思わせるブルーグレー
    const grad = ctx.createLinearGradient(0, baseY, 0, h);
    grad.addColorStop(0, '#1c3144');
    grad.addColorStop(1, '#0b1622');
    ctx.fillStyle = grad;
    ctx.fillRect(0, baseY, w, h - baseY);

    // 🤍 2. シャープな白銀色で「09」（品川区のJISコード）
    ctx.save();
    ctx.font = `bold italic ${h * 0.05}px "Arial Black", Impact, sans-serif`;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';
    
    ctx.shadowBlur = 10;
    ctx.shadowColor = 'rgba(0, 229, 255, 0.8)';
    ctx.fillStyle = '#e0f7fa'; // アイシーブルー
    
    ctx.fillText("09", w * 0.96, h * 0.99);
    
    ctx.shadowBlur = 0;
    ctx.fillStyle = '#00e5ff'; // サイバーなシアン
    ctx.fillRect(w * 0.965, h * 0.93, w * 0.015, h * 0.06);
    ctx.restore();
  }

  function draw() {
    t += 0.016;
    ctx.clearRect(0, 0, w, h);
    
    drawSky();
    drawYatsuyamaBridge(); // 背景にどっしり構える八ツ山橋
    drawYogaAndSignLanguageRibbons(); // ゆっくり流れるヨガと手話の波
    drawArrows(); // 波を切り裂くように飛ぶ弓の光
    drawGround();

    raf = requestAnimationFrame(draw);
  }
  draw();

  return function stop() {
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', resize);
  };
}