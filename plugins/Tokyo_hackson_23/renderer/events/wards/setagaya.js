// setagaya.js
export const key = 'setagaya';
export const label = '世田谷区：玉川秋月 - 多摩川に昇る名月';

/**
 * 世田谷区の演出（Canvas型）。
 * 歌川広重「江戸近郊八景之内・玉川秋月」に着想を得た多摩川の秋の夜。
 * 右手に大きく枝垂れる柳、川面には昇る名月の光の道、
 * 棹をさす渡し舟と岸辺を行く人影、遠くには連なる山並みのシルエット。
 * 柳の枝・水面・舟・人影がそれぞれ違う周期で揺れ動くことで
 * 一枚の浮世絵に「風」と「時間」を与えています。
 */
export function run(canvas) {
  const ctx = canvas.getContext('2d');
  let w, h, raf, t = 0;

  let willowBranches = [];
  let ripples = [];
  let reeds = [];
  let birds = [];

  const generateScene = () => {
    const horizon = h * 0.42;

    // 柳の枝（右岸の根元から放射状に生える大枝、その先に小枝の房）
    willowBranches = [];
    const rootX = w * 0.78;
    const rootY = h * 0.30;
    const numBranches = 9;
    for (let i = 0; i < numBranches; i++) {
      const p = i / (numBranches - 1);
      willowBranches.push({
        angle: -Math.PI * 0.72 + p * Math.PI * 0.55, // 扇状に広がる角度
        length: h * (0.28 + Math.random() * 0.16),
        droop: 0.35 + Math.random() * 0.25,
        phase: Math.random() * Math.PI * 2,
        speed: 0.4 + Math.random() * 0.3,
        rootX, rootY,
      });
    }

    // 川面のさざ波（水平方向の帯）
    ripples = [];
    for (let y = horizon; y < h; y += 5) {
      ripples.push({ y, phase: Math.random() * Math.PI * 2 });
    }

    // 岸辺の葦（すすき/葦のシルエット）
    reeds = [];
    const numReeds = 24;
    for (let i = 0; i < numReeds; i++) {
      reeds.push({
        x: Math.random() * w * 0.3,
        baseY: h * (0.68 + Math.random() * 0.22),
        height: h * (0.06 + Math.random() * 0.07),
        phase: Math.random() * Math.PI * 2,
        speed: 0.6 + Math.random() * 0.4,
      });
    }

    // 遠くを渡る鳥
    birds = [];
    for (let i = 0; i < 4; i++) {
      birds.push({
        y: h * (0.12 + Math.random() * 0.1),
        speed: 6 + Math.random() * 6,
        offset: Math.random() * w,
        phase: Math.random() * Math.PI * 2,
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

  // ---- 1. 夜空と名月 ----
  function drawSky() {
    const horizon = h * 0.42;
    const grad = ctx.createLinearGradient(0, 0, 0, horizon);
    grad.addColorStop(0, '#152238');
    grad.addColorStop(0.5, '#2a3a52');
    grad.addColorStop(1, '#5c7a8c');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, horizon);

    // 名月（高く昇るまん丸の月、じんわり光る）
    const mx = w * 0.55;
    const my = h * 0.16;
    const mr = Math.min(w, h) * 0.05;
    ctx.save();
    ctx.shadowBlur = 45 + Math.sin(t * 1.2) * 6;
    ctx.shadowColor = 'rgba(255,250,220,0.75)';
    ctx.fillStyle = '#fffdf2';
    ctx.beginPath();
    ctx.arc(mx, my, mr, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // 鳥（V字のシルエットが横切る）
    ctx.strokeStyle = 'rgba(20,20,30,0.6)';
    ctx.lineWidth = 1.5;
    birds.forEach(b => {
      const x = (b.offset + t * b.speed * 10) % (w + 100) - 50;
      const flap = Math.sin(t * 8 + b.phase) * 3;
      ctx.beginPath();
      ctx.moveTo(x - 6, b.y - flap);
      ctx.lineTo(x, b.y);
      ctx.lineTo(x + 6, b.y - flap);
      ctx.stroke();
    });
  }

  // ---- 2. 遠くの山並み ----
  function drawMountains() {
    const horizon = h * 0.42;
    ctx.save();
    ctx.fillStyle = 'rgba(70,90,110,0.55)';
    ctx.beginPath();
    ctx.moveTo(0, horizon);
    for (let x = 0; x <= w; x += w / 20) {
      const y = horizon - h * 0.04 * Math.sin(x * 0.006 + 1) - h * 0.02 * Math.sin(x * 0.015);
      ctx.lineTo(x, y);
    }
    ctx.lineTo(w, horizon);
    ctx.closePath();
    ctx.fill();

    ctx.fillStyle = 'rgba(40,55,70,0.7)';
    ctx.beginPath();
    ctx.moveTo(0, horizon);
    for (let x = 0; x <= w; x += w / 24) {
      const y = horizon - h * 0.025 * Math.sin(x * 0.01 + 3) - h * 0.015;
      ctx.lineTo(x, y);
    }
    ctx.lineTo(w, horizon);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  // ---- 3. 多摩川の川面（月光の道） ----
  function drawRiver() {
    const horizon = h * 0.42;
    const grad = ctx.createLinearGradient(0, horizon, 0, h);
    grad.addColorStop(0, '#3d6e78');
    grad.addColorStop(0.5, '#2a5560');
    grad.addColorStop(1, '#173842');
    ctx.fillStyle = grad;
    ctx.fillRect(0, horizon, w, h - horizon);

    // 月光の反射（川面に伸びる縦の光の帯、波でゆらゆら）
    const mx = w * 0.55;
    ctx.save();
    for (let y = horizon; y < h; y += 4) {
      const depth = (y - horizon) / (h - horizon);
      const sway = Math.sin(y * 0.15 + t * 2) * 8 * depth;
      const width = (4 + depth * 22) * (0.7 + Math.sin(t * 3 + y * 0.1) * 0.3);
      ctx.globalAlpha = 0.25 * (1 - depth * 0.4);
      ctx.fillStyle = '#fff7d9';
      ctx.fillRect(mx + sway - width / 2, y, width, 3);
    }
    ctx.restore();
    ctx.globalAlpha = 1;

    // 水平方向のさざ波
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineWidth = 1;
    ripples.forEach(r => {
      const depth = (r.y - horizon) / (h - horizon);
      const amp = 1.5 + depth * 5;
      ctx.beginPath();
      for (let x = 0; x <= w; x += 22) {
        const yy = r.y + Math.sin(x * 0.025 + t * 1.4 + r.phase) * amp;
        if (x === 0) ctx.moveTo(x, yy);
        else ctx.lineTo(x, yy);
      }
      ctx.stroke();
    });
  }

  // ---- 4. 岸辺の葦（風に揺れる） ----
  function drawReeds() {
    reeds.forEach(r => {
      const sway = Math.sin(t * r.speed + r.phase) * 8;
      ctx.strokeStyle = 'rgba(15,15,10,0.75)';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(r.x, r.baseY);
      ctx.quadraticCurveTo(r.x + sway * 0.6, r.baseY - r.height * 0.6, r.x + sway, r.baseY - r.height);
      ctx.stroke();
    });
  }

  // ---- 5. 大きく枝垂れる柳 ----
  function drawWillow() {
    // 幹
    ctx.save();
    ctx.strokeStyle = '#1c1712';
    ctx.lineWidth = Math.min(w, h) * 0.022;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(willowBranches[0].rootX, h);
    ctx.lineTo(willowBranches[0].rootX, willowBranches[0].rootY);
    ctx.stroke();

    // 枝（風でしなる、先端に葉の房）
    willowBranches.forEach(b => {
      const sway = Math.sin(t * b.speed + b.phase) * 0.10;
      const angle = b.angle + sway;
      const endX = b.rootX + Math.cos(angle) * b.length * (1 - b.droop);
      const endY = b.rootY + Math.sin(angle) * b.length * (1 - b.droop) * 0.3 + b.length * b.droop;

      ctx.strokeStyle = 'rgba(20,25,15,0.85)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(b.rootX, b.rootY);
      ctx.quadraticCurveTo(
        b.rootX + Math.cos(angle) * b.length * 0.5,
        b.rootY + b.length * 0.15,
        endX, endY
      );
      ctx.stroke();

      // 葉の房（先端付近に淡い緑〜黄の点描）
      ctx.fillStyle = 'rgba(120,140,70,0.5)';
      for (let i = 0; i < 5; i++) {
        const leafSway = Math.sin(t * b.speed * 1.5 + b.phase + i) * 6;
        ctx.beginPath();
        ctx.ellipse(
          endX + leafSway,
          endY - i * 10 + Math.sin(t + i) * 3,
          10, 4, angle, 0, Math.PI * 2
        );
        ctx.fill();
      }
    });
    ctx.restore();
  }

  // ---- 6. 渡し舟（棹をさす船頭） ----
  function drawBoat() {
    const horizon = h * 0.42;
    const pathStart = w * 0.30;
    const pathEnd = w * 0.62;
    const progress = (Math.sin(t * 0.15) + 1) / 2; // ゆっくり往復
    const x = pathStart + (pathEnd - pathStart) * progress;
    const y = horizon + h * 0.30 + Math.sin(t * 2) * 2;
    const facingRight = Math.cos(t * 0.15) > 0;

    ctx.save();
    ctx.translate(x, y);
    if (!facingRight) ctx.scale(-1, 1);

    // 舟体
    ctx.fillStyle = '#100e0a';
    ctx.beginPath();
    ctx.moveTo(-30, 0);
    ctx.quadraticCurveTo(-34, 6, -22, 8);
    ctx.lineTo(24, 8);
    ctx.quadraticCurveTo(34, 5, 28, -2);
    ctx.closePath();
    ctx.fill();

    // 船頭（人影）
    ctx.fillStyle = '#0a0805';
    ctx.beginPath();
    ctx.ellipse(2, -14, 4, 12, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(2, -24, 3.5, 0, Math.PI * 2);
    ctx.fill();

    // 棹（水面に差しては上げる動き）
    const poleDip = (Math.sin(t * 2.2) + 1) / 2; // 0=上げた, 1=水中
    ctx.strokeStyle = '#2a2115';
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    ctx.moveTo(2, -22);
    ctx.lineTo(-14 - poleDip * 6, 10 + poleDip * 22);
    ctx.stroke();

    ctx.restore();

    // 水面への映り込み
    ctx.save();
    ctx.globalAlpha = 0.18;
    ctx.fillStyle = '#000000';
    ctx.beginPath();
    ctx.ellipse(x, y + 14, 26, 4, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  // ---- 7. 岸辺を歩く人影 ----
  function drawShoreWalker() {
    const horizon = h * 0.42;
    const x = w * 0.18 + Math.sin(t * 0.1) * w * 0.05;
    const y = h * 0.78;
    const step = Math.sin(t * 5);

    ctx.save();
    ctx.translate(x, y);
    ctx.fillStyle = '#0a0805';

    // 体
    ctx.beginPath();
    ctx.ellipse(0, -14, 3.5, 10, 0, 0, Math.PI * 2);
    ctx.fill();
    // 頭
    ctx.beginPath();
    ctx.arc(0, -26, 3, 0, Math.PI * 2);
    ctx.fill();
    // 足（交互に動く）
    ctx.strokeStyle = '#0a0805';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, -4);
    ctx.lineTo(-3 + step * 2, 6);
    ctx.moveTo(0, -4);
    ctx.lineTo(3 - step * 2, 6);
    ctx.stroke();

    ctx.restore();
  }

  // ---- 8. UI装飾 ----
  function drawUI() {
    ctx.save();
    ctx.font = `bold italic ${h * 0.04}px "Arial Black", Impact, sans-serif`;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';

    ctx.shadowBlur = 10;
    ctx.shadowColor = '#fff7d9';
    ctx.fillStyle = '#ffffff';
    ctx.fillText("STG-08", w * 0.96, h * 0.98);

    ctx.shadowBlur = 0;
    ctx.fillStyle = '#fff7d9';
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

    drawSky();
    drawMountains();
    drawRiver();
    drawReeds();
    drawShoreWalker();
    drawBoat();
    drawWillow();
    drawUI();

    raf = requestAnimationFrame(draw);
  }
  draw();

  return function stop() {
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', resize);
  };
}