import React, { useState, useRef, useEffect, useCallback } from 'react';

// ============================================================
// Claude Design(DC形式)で書かれていたコードを、素のReactに変換したもの。
// <x-dc>/<sc-for>/<sc-if>/{{...}}/DCLogic はClaude Design専用のランタイム
// (support.js) がないと動かないため、useState/useRef/canvasの
// 素朴な組み合わせに書き換えている。
//
// 画像対応: 各区の WARDS エントリに image を追加。区が確定した瞬間に
// public/assets/ward-motifs/<code>.png を読み込んで表示する。
// ファイルが無い場合は onError で静かに非表示にする（崩れ表示を防ぐ）。
// ============================================================

const THEMES = [
  ['park', '公園'], ['aed', 'AED'], ['disaster', '防災・避難所'], ['sports', 'スポーツ施設'],
  ['library', '図書館'], ['shopping', '買い物・スーパー'], ['downtown', '繁華街'], ['entertainment', '娯楽施設'],
];

// code: public/assets/ward-motifs/<code>.png に置く画像ファイル名と対応させる
const WARDS = [
  { code: 'chiyoda',    range: [1, 4],    ward: '千代田区', motif: '神田明神曙之景',             x: 50, y: 45, hue: 28 },
  { code: 'minato',     range: [5, 8],    ward: '港区',     motif: '高輪うしまち',               x: 48, y: 52, hue: 205 },
  { code: 'shinjuku',   range: [9, 13],   ward: '新宿区',   motif: '四ツ谷内藤新宿',             x: 38, y: 42, hue: 280 },
  { code: 'bunkyo',     range: [14, 17],  ward: '文京区',   motif: '湯しま天神坂上眺望',         x: 46, y: 35, hue: 140 },
  { code: 'taito',      range: [18, 21],  ward: '台東区',   motif: '浅草金龍山',                 x: 54, y: 35, hue: 15 },
  { code: 'sumida',     range: [22, 25],  ward: '墨田区',   motif: '両ごく回向院元柳橋',         x: 60, y: 38, hue: 190 },
  { code: 'koto',       range: [26, 29],  ward: '江東区',   motif: '大はしあたけの夕立',         x: 62, y: 48, hue: 220 },
  { code: 'chuo',       range: [30, 35],  ward: '中央区',   motif: '日本橋南詰盛況乃図',         x: 55, y: 42, hue: 40 },
  { code: 'shinagawa',  range: [36, 39],  ward: '品川区',   motif: '品川すさき',                 x: 44, y: 62, hue: 195 },
  { code: 'meguro',     range: [40, 43],  ward: '目黒区',   motif: '目黒新富士',                 x: 38, y: 58, hue: 160 },
  { code: 'ota',        range: [44, 48],  ward: '大田区',   motif: '蒲田の梅園',                 x: 36, y: 72, hue: 330 },
  { code: 'setagaya',   range: [49, 52],  ward: '世田谷区', motif: '玉川秋月',                   x: 26, y: 58, hue: 250 },
  { code: 'shibuya',    range: [53, 56],  ward: '渋谷区',   motif: '太田記念美術館',             x: 36, y: 48, hue: 300 },
  { code: 'nakano',     range: [57, 60],  ward: '中野区',   motif: '中野ブロードウェイ',         x: 26, y: 42, hue: 320 },
  { code: 'suginami',   range: [61, 65],  ward: '杉並区',   motif: '杉並アニメーションミュージアム', x: 18, y: 48, hue: 265 },
  { code: 'toshima',    range: [66, 69],  ward: '豊島区',   motif: '高田姿見のはし俤の橋砂利場', x: 36, y: 32, hue: 100 },
  { code: 'kita',       range: [70, 73],  ward: '北区',     motif: '王子瀧の川',                 x: 42, y: 20, hue: 175 },
  { code: 'arakawa',    range: [74, 77],  ward: '荒川区',   motif: '日暮里諏訪の台',             x: 52, y: 26, hue: 20 },
  { code: 'itabashi',   range: [78, 82],  ward: '板橋区',   motif: '東京大仏(乗蓮寺)',           x: 30, y: 20, hue: 45 },
  { code: 'nerima',     range: [83, 86],  ward: '練馬区',   motif: '東映動画発祥の地',           x: 18, y: 28, hue: 310 },
  { code: 'adachi',     range: [87, 90],  ward: '足立区',   motif: '千住之大橋',                 x: 56, y: 15, hue: 210 },
  { code: 'katsushika', range: [91, 95],  ward: '葛飾区',   motif: '堀切の花菖蒲',               x: 66, y: 20, hue: 270 },
  { code: 'edogawa',    range: [96, 100], ward: '江戸川区', motif: '地下鉄博物館',               x: 70, y: 35, hue: 230 },
].map((w) => ({ ...w, image: `/assets/ward-motifs/${w.code}.png` }));

const RANK_LEGEND = [
  { label: '高', color: 'rgb(34,211,190)' },
  { label: '中', color: 'rgb(250,204,120)' },
  { label: '低', color: 'rgb(99,102,180)' },
];

function hashScore(seed) {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) | 0;
  return (Math.abs(h) % 100) + 1;
}

function rollWard() {
  const n = 1 + Math.floor(Math.random() * 100);
  return WARDS.find((w) => n >= w.range[0] && n <= w.range[1]);
}

function getTimePalette(timeOverride) {
  const table = {
    dawn: { hue: 28, pulse: false },
    day: { hue: 195, pulse: false },
    dusk: { hue: 330, pulse: true },
    night: { hue: 265, pulse: false },
  };
  if (timeOverride && timeOverride !== 'auto') return table[timeOverride];
  const h = new Date().getHours();
  if (h >= 5 && h < 9) return table.dawn;
  if (h >= 9 && h < 17) return table.day;
  if (h >= 17 && h < 20) return table.dusk;
  return table.night;
}

// フォントは一度だけ差し込む（App.jsx側と同じ「動的にstyle/linkを足す」パターン）
function ensureFonts() {
  if (document.getElementById('ward-divination-fonts')) return;
  const link = document.createElement('link');
  link.id = 'ward-divination-fonts';
  link.rel = 'stylesheet';
  link.href = 'https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=Shippori+Mincho:wght@400;500&display=swap';
  document.head.appendChild(link);
}

export default function WardDivination({ timeOverride = 'auto', particleDensity = 90 }) {
  const canvasRef = useRef(null);
  const projCanvasRef = useRef(null);
  const animFrameRef = useRef(null);
  const particlesRef = useRef([]);
  const mouseRef = useRef({ x: null, y: null });
  const biasTargetRef = useRef(null);
  const transitionStartRef = useRef(0);
  const projRef = useRef(null); // { motifQueue, motifActive, nextMotifAt, diamond, scan, wireframe }

  const [theme, setTheme] = useState(null);
  const [mode, setMode] = useState('ambient'); // ambient | converging | result | dissolving
  const [result, setResult] = useState(null);
  const [imageOk, setImageOk] = useState(true);

  // ---- 初期化 ----
  useEffect(() => {
    ensureFonts();

    const w = window.innerWidth, h = window.innerHeight;
    particlesRef.current = Array.from({ length: particleDensity }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      size: 1 + Math.random() * 2.2,
      phase: Math.random() * Math.PI * 2,
      freq: 0.2 + Math.random() * 0.3,
    }));

    projRef.current = {
      motifQueue: [],
      motifActive: null,
      nextMotifAt: performance.now() + 800,
      diamond: newDiamondCycle(),
      scan: newScanCycle(),
      wireframe: newWireframeCycle(),
    };

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      [canvasRef.current, projCanvasRef.current].forEach((c) => {
        if (!c) return;
        c.width = window.innerWidth * dpr;
        c.height = window.innerHeight * dpr;
        c.getContext('2d').setTransform(dpr, 0, 0, dpr, 0, 0);
      });
    };
    resize();
    window.addEventListener('resize', resize);

    const loop = () => {
      animFrameRef.current = requestAnimationFrame(loop);
      draw();
    };
    loop();

    return () => {
      cancelAnimationFrame(animFrameRef.current);
      window.removeEventListener('resize', resize);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function newScanCycle() {
    const w = window.innerWidth, h = window.innerHeight;
    return {
      angle: Math.random() * Math.PI,
      offset: -0.2,
      speed: 0.06 + Math.random() * 0.03,
      width: h * (0.12 + Math.random() * 0.08),
      diag: Math.hypot(w, h),
    };
  }

  function newWireframeCycle() {
    const w = window.innerWidth, h = window.innerHeight;
    const sides = 3 + Math.floor(Math.random() * 4);
    return {
      cx: w * (0.3 + Math.random() * 0.4), cy: h * (0.3 + Math.random() * 0.4),
      sides, rot: Math.random() * Math.PI * 2, spin: (Math.random() - 0.5) * 0.25,
      r0: Math.min(w, h) * 0.06, r1: Math.min(w, h) * (0.22 + Math.random() * 0.1),
      progress: 0, speed: 0.08 + Math.random() * 0.05,
      hue: 190 + Math.random() * 80,
    };
  }

  function newDiamondCycle() {
    const colors = ['#ffd54a', '#ff4d4d', '#4d9bff', '#d4af37', '#c9c9d6'];
    for (let i = colors.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [colors[i], colors[j]] = [colors[j], colors[i]];
    }
    const w = window.innerWidth, h = window.innerHeight;
    return {
      cx: w / 2 + (Math.random() - 0.5) * w * 0.1,
      cy: h / 2 + (Math.random() - 0.5) * h * 0.1,
      angle: Math.random() * Math.PI * 2,
      spin: (Math.random() - 0.5) * 0.35,
      driftAngle: Math.random() * Math.PI * 2,
      driftDist: Math.hypot(w, h) * 0.55,
      speed: 0.055 + Math.random() * 0.03,
      progress: 0,
      radius: Math.min(w, h) * (0.09 + Math.random() * 0.03),
      colors,
    };
  }

  function drawProjection(ctx, w, h, t) {
    const p = projRef.current;

    if (!p.motifActive && t * 1000 >= p.nextMotifAt) {
      if (!p.motifQueue.length) {
        p.motifQueue = WARDS.map((_, i) => i);
        for (let i = p.motifQueue.length - 1; i > 0; i--) {
          const j = Math.floor(Math.random() * (i + 1));
          [p.motifQueue[i], p.motifQueue[j]] = [p.motifQueue[j], p.motifQueue[i]];
        }
      }
      const idx = p.motifQueue.pop();
      p.motifActive = {
        ward: WARDS[idx], start: t * 1000, dur: 3200 + Math.random() * 900,
        x: w * (0.2 + Math.random() * 0.6), y: h * (0.2 + Math.random() * 0.6),
        petals: 4 + Math.floor(Math.random() * 5), rot: Math.random() * Math.PI * 2,
        scale: Math.min(w, h) * (0.05 + Math.random() * 0.035),
      };
    }
    if (p.motifActive) {
      const m = p.motifActive;
      const life = (t * 1000 - m.start) / m.dur;
      if (life >= 1) {
        p.motifActive = null;
        p.nextMotifAt = t * 1000 + 900 + Math.random() * 1400;
      } else {
        const fade = Math.sin(Math.PI * Math.min(1, Math.max(0, life)));
        ctx.save();
        ctx.translate(m.x, m.y);
        ctx.rotate(m.rot + life * 0.4);
        ctx.globalAlpha = fade * 0.55;
        ctx.strokeStyle = `hsla(${m.ward.hue},75%,72%,1)`;
        ctx.lineWidth = 1.4;
        ctx.shadowColor = `hsla(${m.ward.hue},80%,65%,0.8)`;
        ctx.shadowBlur = 14;
        for (let i = 0; i < m.petals; i++) {
          const a = (Math.PI * 2 / m.petals) * i;
          ctx.beginPath();
          ctx.moveTo(0, 0);
          ctx.quadraticCurveTo(Math.cos(a) * m.scale * 0.6, Math.sin(a) * m.scale * 0.6, Math.cos(a) * m.scale, Math.sin(a) * m.scale);
          ctx.stroke();
        }
        ctx.beginPath();
        ctx.arc(0, 0, m.scale * 0.32, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
      }
    }

    const sc = p.scan;
    sc.offset += sc.speed * 0.016;
    if (sc.offset > 1.3) {
      p.scan = newScanCycle();
    } else {
      const travel = -sc.diag * 0.65 + sc.offset * sc.diag * 1.3;
      ctx.save();
      ctx.translate(w / 2, h / 2);
      ctx.rotate(sc.angle);
      const grad = ctx.createLinearGradient(travel - sc.width / 2, 0, travel + sc.width / 2, 0);
      grad.addColorStop(0, 'rgba(180,220,255,0)');
      grad.addColorStop(0.5, 'rgba(200,230,255,0.16)');
      grad.addColorStop(1, 'rgba(180,220,255,0)');
      ctx.fillStyle = grad;
      ctx.fillRect(travel - sc.width / 2, -sc.diag, sc.width, sc.diag * 2);
      ctx.restore();
    }

    const wf = p.wireframe;
    wf.rot += wf.spin * 0.016;
    wf.progress += wf.speed * 0.016;
    if (wf.progress >= 1) {
      p.wireframe = newWireframeCycle();
    } else {
      const r = wf.r0 + (wf.r1 - wf.r0) * Math.min(1, wf.progress * 1.6);
      const alpha = Math.sin(Math.PI * Math.min(1, wf.progress)) * 0.4;
      ctx.save();
      ctx.translate(wf.cx, wf.cy);
      ctx.rotate(wf.rot);
      ctx.strokeStyle = `hsla(${wf.hue},70%,75%,${alpha})`;
      ctx.lineWidth = 1;
      ctx.shadowColor = `hsla(${wf.hue},80%,70%,0.7)`;
      ctx.shadowBlur = 10;
      ctx.beginPath();
      for (let i = 0; i <= wf.sides; i++) {
        const a = (Math.PI * 2 / wf.sides) * i;
        const px = Math.cos(a) * r, py = Math.sin(a) * r;
        if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
      }
      ctx.stroke();
      ctx.beginPath();
      for (let i = 0; i <= wf.sides; i++) {
        const a = (Math.PI * 2 / wf.sides) * i;
        const rr = r * 0.55;
        const px = Math.cos(a) * rr, py = Math.sin(a) * rr;
        if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
      }
      ctx.stroke();
      ctx.restore();
    }

    const d = p.diamond;
    d.angle += d.spin * 0.016;
    d.progress += d.speed * 0.016;
    if (d.progress >= 1) {
      p.diamond = newDiamondCycle();
      return;
    }
    const ease = d.progress;
    const cx = d.cx + Math.cos(d.driftAngle) * d.driftDist * ease;
    const cy = d.cy + Math.sin(d.driftAngle) * d.driftDist * ease;
    const alpha = Math.sin(Math.PI * Math.min(1, ease * 1.15)) * 0.85;
    const pts = [
      [cx, cy - d.radius], [cx + d.radius, cy], [cx, cy + d.radius], [cx - d.radius, cy], [cx, cy],
    ].map(([px, py]) => {
      const dx = px - cx, dy = py - cy;
      const cos = Math.cos(d.angle), sin = Math.sin(d.angle);
      return [cx + dx * cos - dy * sin, cy + dx * sin + dy * cos];
    });
    pts.forEach(([px, py], i) => {
      ctx.beginPath();
      ctx.fillStyle = d.colors[i];
      ctx.globalAlpha = alpha;
      ctx.shadowColor = d.colors[i];
      ctx.shadowBlur = 16;
      ctx.arc(px, py, i === 4 ? 4.5 : 3.5, 0, Math.PI * 2);
      ctx.fill();
    });
    ctx.globalAlpha = 1;
  }

  function updateBias(nextTheme) {
    if (!nextTheme) { biasTargetRef.current = null; return; }
    const scored = WARDS.map((w, i) => ({ w, score: hashScore(nextTheme + '-' + i) }));
    const high = scored.filter((s) => s.score >= 67);
    if (!high.length) { biasTargetRef.current = null; return; }
    let sx = 0, sy = 0;
    high.forEach((s) => { sx += s.w.x; sy += s.w.y; });
    sx /= high.length; sy /= high.length;
    biasTargetRef.current = { x: (sx / 100) * window.innerWidth, y: (sy / 100) * window.innerHeight };
  }

  const selectTheme = (key) => (e) => {
    e.stopPropagation();
    const next = theme === key ? null : key;
    setTheme(next);
    updateBias(next);
  };

  const handleStageClick = useCallback(() => {
    setMode((currentMode) => {
      if (currentMode === 'ambient') {
        const picked = rollWard();
        setImageOk(true);
        setResult(picked);
        transitionStartRef.current = performance.now();
        setTimeout(() => {
          setMode((m) => (m === 'converging' ? 'result' : m));
        }, 900);
        return 'converging';
      }
      if (currentMode === 'result') {
        transitionStartRef.current = performance.now();
        setTimeout(() => {
          setMode((m) => (m === 'dissolving' ? 'ambient' : m));
          setResult(null);
        }, 900);
        return 'dissolving';
      }
      return currentMode;
    });
  }, []);

  const handleMouseMove = (e) => { mouseRef.current = { x: e.clientX, y: e.clientY }; };
  const handleTouchMove = (e) => {
    const t = e.touches && e.touches[0];
    if (t) mouseRef.current = { x: t.clientX, y: t.clientY };
  };

  function draw() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = window.innerWidth, h = window.innerHeight;
    const t = performance.now() / 1000;

    ctx.fillStyle = 'rgba(4,5,10,0.16)';
    ctx.fillRect(0, 0, w, h);

    const projCanvas = projCanvasRef.current;
    if (projCanvas) {
      const pctx = projCanvas.getContext('2d');
      pctx.clearRect(0, 0, w, h);
      if (mode === 'ambient') drawProjection(pctx, w, h, t);
    }

    const pal = getTimePalette(timeOverride);
    const cx = w / 2, cy = h / 2;

    particlesRef.current.forEach((p) => {
      const dx0 = Math.sin(t * p.freq + p.phase) * 0.15;
      const dy0 = Math.cos(t * p.freq * 0.8 + p.phase) * 0.15;
      p.vx += dx0 * 0.02; p.vy += dy0 * 0.02;

      if (mode === 'converging') {
        const elapsed = (performance.now() - transitionStartRef.current) / 900;
        const k = Math.min(1, elapsed);
        const pull = k * 0.06;
        p.vx += (cx - p.x) * pull * 0.02;
        p.vy += (cy - p.y) * pull * 0.02;
      } else if (mode === 'dissolving') {
        const elapsed = (performance.now() - transitionStartRef.current) / 900;
        const k = Math.min(1, elapsed);
        const dx = p.x - cx, dy = p.y - cy, dist = Math.hypot(dx, dy) || 1;
        const push = k * 0.09;
        p.vx += (dx / dist) * push + (Math.random() - 0.5) * 0.4 * k;
        p.vy += (dy / dist) * push + (Math.random() - 0.5) * 0.4 * k;
      } else if (mode === 'ambient') {
        const mouse = mouseRef.current;
        if (mouse.x != null) {
          const dx = mouse.x - p.x, dy = mouse.y - p.y;
          const dist = Math.hypot(dx, dy);
          if (dist < 260 && dist > 0.01) {
            const f = (1 - dist / 260) * 0.035;
            p.vx += (dx / dist) * f; p.vy += (dy / dist) * f;
          }
        }
        if (biasTargetRef.current) {
          const dx = biasTargetRef.current.x - p.x, dy = biasTargetRef.current.y - p.y;
          const dist = Math.hypot(dx, dy) || 1;
          p.vx += (dx / dist) * 0.004; p.vy += (dy / dist) * 0.004;
        }
      } else if (mode === 'result') {
        const dx = cx - p.x, dy = cy - p.y, dist = Math.hypot(dx, dy) || 1;
        p.vx += (dx / dist) * 0.01 - (dy / dist) * 0.003;
        p.vy += (dy / dist) * 0.01 + (dx / dist) * 0.003;
      }

      p.vx *= 0.94; p.vy *= 0.94;
      p.x += p.vx; p.y += p.vy;
      if (p.x < -20) p.x = w + 20; if (p.x > w + 20) p.x = -20;
      if (p.y < -20) p.y = h + 20; if (p.y > h + 20) p.y = -20;

      let hue = pal.hue;
      let alpha = 0.55;
      if ((mode === 'result' || mode === 'converging') && result) {
        const blend = mode === 'converging' ? Math.min(1, (performance.now() - transitionStartRef.current) / 900) : 1;
        hue = pal.hue + (result.hue - pal.hue) * blend;
      }
      if (pal.pulse) alpha *= 0.7 + Math.sin(t * 1.6 + p.phase) * 0.3;
      const size = p.size * (mode === 'converging' || mode === 'dissolving' ? 1.4 : 1);

      ctx.beginPath();
      ctx.fillStyle = `hsla(${hue},80%,68%,${alpha})`;
      ctx.shadowBlur = 8;
      ctx.shadowColor = `hsla(${hue},90%,70%,0.9)`;
      ctx.arc(p.x, p.y, size, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  function wardStyle(ward, index) {
    let rank = 'none';
    if (theme) {
      const score = hashScore(theme + '-' + index);
      rank = score >= 67 ? 'high' : score >= 34 ? 'mid' : 'low';
    }
    const colors = { high: '34,211,190', mid: '250,204,120', low: '99,102,180', none: '150,160,200' };
    const c = colors[rank];
    const opacity = theme ? (rank === 'high' ? 0.85 : rank === 'mid' ? 0.5 : 0.28) : 0.26;
    return {
      position: 'absolute', left: ward.x + '%', top: ward.y + '%',
      width: '11vmin', height: '9vmin', transform: 'translate(-50%,-50%)',
      borderRadius: '46% 54% 60% 40% / 50% 45% 55% 50%',
      background: `radial-gradient(circle at 50% 50%, rgba(${c},${opacity}) 0%, rgba(${c},0) 72%)`,
      mixBlendMode: 'screen', filter: 'blur(1px)', transition: 'background 0.6s ease',
    };
  }

  const uiVisible = mode === 'ambient';
  const overlayOpacity = mode === 'result' ? 1 : 0;
  let overlayBg = 'transparent';
  let isNihonbashi = false, isNakano = false;
  if (result) {
    overlayBg = `radial-gradient(circle at 50% 45%, hsla(${result.hue},70%,32%,0.55) 0%, hsla(${result.hue},60%,12%,0.85) 55%, rgba(3,4,8,0.96) 100%)`;
    isNihonbashi = result.ward === '中央区';
    isNakano = result.ward === '中野区';
  }

  return (
    <div
      style={{
        position: 'fixed', inset: 0, overflow: 'hidden', background: '#04050a',
        cursor: 'pointer', fontFamily: "'Noto Sans JP',sans-serif", userSelect: 'none',
      }}
      onClick={handleStageClick}
      onMouseMove={handleMouseMove}
      onTouchMove={handleTouchMove}
      onTouchStart={handleTouchMove}
    >
      <canvas
        ref={projCanvasRef}
        style={{
          position: 'absolute', inset: 0, width: '100%', height: '100%', display: 'block',
          opacity: mode === 'ambient' ? 1 : 0, transition: 'opacity 1.1s ease', mixBlendMode: 'screen',
        }}
      />
      <canvas ref={canvasRef} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', display: 'block' }} />

      <div
        style={{
          position: 'absolute', inset: 0,
          opacity: uiVisible ? 1 : 0,
          transform: uiVisible ? 'translateY(0)' : 'translateY(-6px)',
          transition: 'opacity .7s ease, transform .7s ease',
          pointerEvents: uiVisible ? 'auto' : 'none',
        }}
      >
        <div
          style={{
            position: 'absolute', top: '5vh', left: '50%', transform: 'translateX(-50%)',
            color: 'rgba(255,255,255,0.68)', fontSize: '12px', letterSpacing: '3px', whiteSpace: 'nowrap',
            opacity: uiVisible ? 0.75 : 0, transition: 'opacity .7s ease',
          }}
        >
          CLICK TO DIVINE YOUR WARD　―　クリックで運だめし
        </div>

        <div style={{ position: 'absolute', top: '11vh', left: 0, right: 0, display: 'flex', justifyContent: 'center', flexWrap: 'wrap', gap: '10px', padding: '0 24px', boxSizing: 'border-box' }}>
          {THEMES.map(([key, label]) => (
            <div
              key={key}
              onClick={selectTheme(key)}
              style={{
                padding: '10px 18px', borderRadius: '999px', backdropFilter: 'blur(14px)',
                border: '1px solid rgba(255,255,255,0.25)', color: '#fff', fontSize: '13px',
                letterSpacing: '1px', cursor: 'pointer', transition: 'all .3s ease', whiteSpace: 'nowrap',
                background: theme === key ? 'rgba(255,255,255,0.24)' : 'rgba(255,255,255,0.08)',
              }}
            >
              {label}
            </div>
          ))}
        </div>

        <div style={{ position: 'absolute', left: '18px', top: '50%', transform: 'translateY(-50%)', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {RANK_LEGEND.map((item) => (
            <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
              <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: item.color, boxShadow: `0 0 10px ${item.color}` }} />
              <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: '10px', letterSpacing: '1.5px' }}>{item.label}</span>
            </div>
          ))}
        </div>

        <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
          {WARDS.map((ward, i) => (
            <div key={ward.code} style={wardStyle(ward, i)} />
          ))}
        </div>
      </div>

      <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', opacity: overlayOpacity, transition: 'opacity .9s ease', background: overlayBg }}>
        {isNihonbashi && (
          <>
            <div style={{ position: 'absolute', left: 0, right: 0, top: '58%', height: '2px', background: 'linear-gradient(90deg,transparent,rgba(255,214,140,0.55),transparent)', filter: 'blur(1px)' }} />
            <div style={{ position: 'absolute', left: '10%', right: '10%', top: '40%', height: '40%', background: 'radial-gradient(ellipse at 50% 100%,rgba(255,190,90,0.25),transparent 70%)' }} />
          </>
        )}
        {isNakano && (
          <>
            <div style={{ position: 'absolute', inset: 0, background: 'repeating-linear-gradient(90deg,rgba(255,60,200,0.08) 0 2px,transparent 2px 34px)' }} />
            <div style={{ position: 'absolute', left: 0, right: 0, top: 0, height: '100%', background: 'radial-gradient(circle at 50% 30%,rgba(120,80,255,0.25),transparent 60%)' }} />
          </>
        )}
      </div>

      {mode === 'result' && result && (
        <div style={{ position: 'absolute', right: '30px', bottom: '26px', textAlign: 'right', fontFamily: "'Shippori Mincho',serif", pointerEvents: 'none' }}>
          {/* 画像対応: public/assets/ward-motifs/<code>.png があればここに表示。無ければ静かに隠す */}
          {imageOk && (
            <img
              src={result.image}
              alt={result.motif}
              onError={() => setImageOk(false)}
              style={{
                width: '180px', maxWidth: '40vw', height: 'auto', display: 'block', marginLeft: 'auto',
                marginBottom: '14px', borderRadius: '6px', boxShadow: '0 8px 30px rgba(0,0,0,0.55)',
                border: '1px solid rgba(255,255,255,0.15)',
              }}
            />
          )}
          <div style={{ fontSize: '16px', color: 'rgba(255,250,240,0.9)', letterSpacing: '1.5px', lineHeight: 1.7 }}>
            {result.motif}、{result.ward}
          </div>
          <div style={{ fontSize: '10px', color: 'rgba(255,250,240,0.45)', letterSpacing: '2px', marginTop: '6px', fontFamily: "'Noto Sans JP',sans-serif" }}>
            もう一度クリックすると、ほどけて戻ります
          </div>
        </div>
      )}
    </div>
  );
}