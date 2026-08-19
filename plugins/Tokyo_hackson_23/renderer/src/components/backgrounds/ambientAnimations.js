// ============================================================
// ward effects registry
// 元の <script>WardEffects = {...}</script> をESモジュール化したもの。
// window.WardEffects の代わりに、このファイルが唯一のレジストリになる。
// ============================================================

const registry = {};

/**
 * Canvas描画型の演出を登録する（星空・桜吹雪・橋がかかる、など requestAnimationFrame でループするもの）。
 * @param {string} key   - 演出を選ぶためのキー
 * @param {object} def   - { label: string, run: (canvas) => stopFn }
 */
export function registerCanvasEffect(key, def) {
  registry[key] = { type: 'canvas', ...def };
}

// 後方互換のエイリアス（今までの registerEffect('chuo', {...}) をそのまま使える）
export const registerEffect = registerCanvasEffect;

/**
 * JSXコンポーネント型の演出を登録する（DOM/Tailwindで組み立てる街並みなど、
 * canvasのアニメーションループに乗らないもの）。
 * @param {string} key         - 演出を選ぶためのキー
 * @param {object} def         - { label: string, Component: React.ComponentType }
 */
export function registerComponentEffect(key, def) {
  registry[key] = { type: 'component', ...def };
}

/**
 * 指定キーの演出を取得。無ければ 'default' にフォールバック。
 */
export function getEffect(key) {
  return registry[key] || registry.default;
}

export function listEffects() {
  return Object.entries(registry).map(([key, def]) => ({ key, label: def.label, type: def.type }));
}

// ============================================================
// 共通ユーティリティ: 視点操作（マウス/指の位置 + 矢印キー）
// 演出側は camera.update() を毎フレーム呼ぶと {x, y}(-1〜1) が返る
// ============================================================
export function createCamera(canvas) {
  let tx = 0, ty = 0;   // ポインタ由来の目標値
  let kx = 0, ky = 0;   // 矢印キーで蓄積される値
  let cx = 0, cy = 0;   // 実際に使う、なめらかに追従した値
  const keys = { ArrowUp: false, ArrowDown: false, ArrowLeft: false, ArrowRight: false };

  function onMove(clientX, clientY) {
    const rect = canvas.getBoundingClientRect();
    tx = ((clientX - rect.left) / rect.width - 0.5) * 2;
    ty = ((clientY - rect.top) / rect.height - 0.5) * 2;
  }
  const mouseHandler = (e) => onMove(e.clientX, e.clientY);
  const touchHandler = (e) => { if (e.touches[0]) onMove(e.touches[0].clientX, e.touches[0].clientY); };
  const keyDown = (e) => { if (e.key in keys) { keys[e.key] = true; e.preventDefault(); } };
  const keyUp = (e) => { if (e.key in keys) { keys[e.key] = false; } };

  canvas.addEventListener('mousemove', mouseHandler);
  canvas.addEventListener('touchmove', touchHandler, { passive: true });
  window.addEventListener('keydown', keyDown);
  window.addEventListener('keyup', keyUp);

  return {
    update() {
      if (keys.ArrowLeft) kx -= 0.025;
      if (keys.ArrowRight) kx += 0.025;
      if (keys.ArrowUp) ky -= 0.025;
      if (keys.ArrowDown) ky += 0.025;
      kx = Math.max(-1, Math.min(1, kx));
      ky = Math.max(-1, Math.min(1, ky));
      const targetX = Math.max(-1, Math.min(1, tx + kx));
      const targetY = Math.max(-1, Math.min(1, ty + ky));
      cx += (targetX - cx) * 0.08;
      cy += (targetY - cy) * 0.08;
      return { x: cx, y: cy };
    },
    dispose() {
      canvas.removeEventListener('mousemove', mouseHandler);
      canvas.removeEventListener('touchmove', touchHandler);
      window.removeEventListener('keydown', keyDown);
      window.removeEventListener('keyup', keyUp);
    },
  };
}

// ============================================================
// 共通ユーティリティ: ヘリコプター視点のHUD（ビネット＋ローター＋照準）
// 将来「上空から街を見下ろす」系の演出で使う想定。今の default/chuo では未使用。
// ============================================================
export function drawHelicopterHUD(ctx, w, h, cam, t) {
  const grad = ctx.createRadialGradient(w / 2, h / 2, h * 0.2, w / 2, h / 2, h * 0.75);
  grad.addColorStop(0, 'rgba(0,0,0,0)');
  grad.addColorStop(1, 'rgba(0,0,0,0.55)');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, w, h);

  ctx.save();
  ctx.translate(50, 50);
  ctx.rotate(t * 30);
  ctx.strokeStyle = 'rgba(255,255,255,0.25)';
  ctx.lineWidth = 3;
  for (let i = 0; i < 3; i++) {
    ctx.save();
    ctx.rotate((Math.PI * 2 / 3) * i);
    ctx.beginPath();
    ctx.ellipse(0, 0, 34, 4, 0, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  }
  ctx.restore();

  ctx.strokeStyle = 'rgba(255,255,255,0.3)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(w / 2 - 10, h / 2); ctx.lineTo(w / 2 + 10, h / 2);
  ctx.moveTo(w / 2, h / 2 - 10); ctx.lineTo(w / 2, h / 2 + 10);
  ctx.stroke();
}

// ============================================================
// 演出: デフォルト（浮世絵・金箔・桜）
// ============================================================
registerEffect('default', {
  label: '共通デフォルト：浮世絵・金箔・桜',
  run(canvas) {
    const ctx = canvas.getContext('2d');
    let w, h, raf;
    const petals = [];
    const resize = () => { w = canvas.width = canvas.clientWidth; h = canvas.height = canvas.clientHeight; };
    window.addEventListener('resize', resize);
    resize();

    for (let i = 0; i < 60; i++) {
      petals.push({
        x: Math.random() * w,
        y: Math.random() * h,
        r: 4 + Math.random() * 6,
        vy: 0.4 + Math.random() * 0.8,
        vx: Math.sin(i) * 0.6,
        sway: Math.random() * Math.PI * 2,
        gold: Math.random() < 0.25,
      });
    }

    function draw() {
      ctx.fillStyle = '#0a0603';
      ctx.fillRect(0, 0, w, h);
      ctx.strokeStyle = 'rgba(212,175,55,0.15)';
      for (let i = -h; i < w; i += 60) {
        ctx.beginPath();
        ctx.moveTo(i, h);
        ctx.lineTo(i + h, 0);
        ctx.stroke();
      }
      petals.forEach((p) => {
        p.sway += 0.02;
        p.x += p.vx + Math.sin(p.sway) * 0.5;
        p.y += p.vy;
        if (p.y > h + 10) { p.y = -10; p.x = Math.random() * w; }
        ctx.fillStyle = p.gold ? 'rgba(212,175,55,0.9)' : 'rgba(255,183,197,0.85)';
        ctx.beginPath();
        ctx.ellipse(p.x, p.y, p.r, p.r * 0.6, p.sway, 0, Math.PI * 2);
        ctx.fill();
      });
      raf = requestAnimationFrame(draw);
    }
    draw();

    return function stop() {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
    };
  },
});

// ============================================================
// 演出: 中央区（橋がかかる演出）
// ============================================================
registerEffect('chuo', {
  label: '中央区：橋がかかる演出',
  run(canvas) {
    const ctx = canvas.getContext('2d');
    let w, h, raf, t = 0;
    const resize = () => { w = canvas.width = canvas.clientWidth; h = canvas.height = canvas.clientHeight; };
    window.addEventListener('resize', resize);
    resize();

    function draw() {
      t += 0.02;
      ctx.fillStyle = '#020814';
      ctx.fillRect(0, 0, w, h);

      ctx.fillStyle = 'rgba(5,120,213,0.25)';
      ctx.fillRect(0, h * 0.6, w, h * 0.4);

      const progress = Math.min(1, (Math.sin(t) + 1) / 2 + 0.001);
      const midY = h * 0.55;
      const span = w * 0.8;
      const startX = w * 0.1;

      ctx.strokeStyle = '#05d5e7';
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(startX, midY + 20);
      const cx = startX + span * progress * 0.5;
      const cy = midY - 60 * Math.sin(Math.PI * progress);
      ctx.quadraticCurveTo(cx, cy, startX + span * progress, midY + 20);
      ctx.stroke();

      for (let i = 0; i <= progress; i += 0.1) {
        const x = startX + span * i;
        const y = midY + 20 - 40 * Math.sin(Math.PI * i);
        ctx.fillStyle = '#ffae19';
        ctx.beginPath();
        ctx.arc(x, y, 2.5, 0, Math.PI * 2);
        ctx.fill();
      }
      raf = requestAnimationFrame(draw);
    }
    draw();

    return function stop() {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
    };
  },
});

// ============================================================
// 演出: 葛飾区（柴又帝釈天参道が組み上がる） ※component型
// ============================================================
import Model_Katsushika from './Model_Katsushika';
import WardDivination from './WardDivination';

registerComponentEffect('katsushika', {
  label: '葛飾区：柴又帝釈天参道が組み上がる演出',
  Component: Model_Katsushika,
});

registerComponentEffect('wardDivination', {
  label: 'クリックで運だめし：23区モチーフ占い（PNG対応）',
  Component: WardDivination,
});

// 今後の演出はこのファイルに registerCanvasEffect(...) / registerComponentEffect(...)
// を足していくだけでOK。港区=waterTaxi、新宿区=melonpan、荒川区/江東区=speechBubbles 等、
// メモにある構想もこの形式でここに追加していく想定。