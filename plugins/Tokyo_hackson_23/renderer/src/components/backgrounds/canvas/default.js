export const key = 'default';
export const label = '共通デフォルト：浮世絵・金箔・桜';

export function run(canvas) {
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
}
