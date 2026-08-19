// adachi.js
export const key = 'adachi';
export const label = '足立区：荒川の夕景と千住の灯り - 水辺に映る光のまち';

/**
 * 足立区の演出（Canvas型）。
 *
 * ・荒川の広い水辺
 * ・千住エリアの街並み
 * ・足立の花火をイメージした赤・青の花火
 * ・街と土手をつなぐ大小の樹木
 * ・東京上空を横切る旅客機
 *
 * 足立区らしい「河川・住宅地・にぎわい・緑」を
 * 一枚の夕景として表現します。
 *
 * ※ 羽田空港自体は大田区にあるため、
 *    ここでは「東京上空を飛ぶ旅客機」として遠景演出にしています。
 */
export function run(canvas) {
  const ctx = canvas.getContext('2d');

  let w, h, raf, t = 0;

  let cloudBands = [];
  let riverWaves = [];
  let cityBlocks = [];
  let windowLights = [];
  let grassBlades = [];
  let fireworks = [];
  let fireflyLights = [];
  let trees = [];
  let airplanes = [];

  // =========================================================
  // Scene Generation
  // =========================================================

  const generateScene = () => {
    const horizon = h * 0.52;
    const riverY = h * 0.62;

    // ---------------------------------------------------------
    // 雲
    // ---------------------------------------------------------

    cloudBands = [];

    for (let i = 0; i < 5; i++) {
      cloudBands.push({
        y: h * (0.08 + i * 0.08),
        speed: 2 + Math.random() * 3,
        offset: Math.random() * w,
        alpha: 0.08 + Math.random() * 0.08,
        width: w * (0.25 + Math.random() * 0.25),
        height: h * (0.035 + Math.random() * 0.02),
      });
    }

    // ---------------------------------------------------------
    // 川面
    // ---------------------------------------------------------

    riverWaves = [];

    for (let i = 0; i < 12; i++) {
      riverWaves.push({
        y: riverY + i * h * 0.022,
        amp: 3 + Math.random() * 4,
        freq: 0.010 + Math.random() * 0.01,
        phase: Math.random() * Math.PI * 2,
        alpha: 0.10 + i * 0.01,
      });
    }

    // ---------------------------------------------------------
    // 千住の街並み
    // ---------------------------------------------------------

    cityBlocks = [];

    let x = -20;

    while (x < w + 20) {
      const bw = w * (0.018 + Math.random() * 0.04);
      const bh = h * (0.05 + Math.random() * 0.18);

      cityBlocks.push({
        x,
        w: bw,
        h: bh,
      });

      x += bw + Math.random() * 5;
    }

    // ---------------------------------------------------------
    // ビルの窓
    // ---------------------------------------------------------

    windowLights = [];

    cityBlocks.forEach((b) => {
      const cols = Math.max(1, Math.floor(b.w / 8));
      const rows = Math.max(1, Math.floor(b.h / 10));

      for (let c = 0; c < cols; c++) {
        for (let r = 0; r < rows; r++) {
          if (Math.random() > 0.82) {
            windowLights.push({
              x: b.x + 4 + c * 8,
              y:
                horizon +
                h * 0.02 -
                b.h +
                5 +
                r * 10,
              phase: Math.random() * Math.PI * 2,
            });
          }
        }
      }
    });

    // ---------------------------------------------------------
    // 土手の草
    // ---------------------------------------------------------

    grassBlades = [];

    for (let i = 0; i < 180; i++) {
      grassBlades.push({
        x: Math.random() * w,
        y: h * (0.78 + Math.random() * 0.2),
        len: 10 + Math.random() * 18,
        lean: -0.6 + Math.random() * 1.2,
        phase: Math.random() * Math.PI * 2,
      });
    }

    // ---------------------------------------------------------
    // 花火
    // ---------------------------------------------------------

    fireworks = [];

    for (let i = 0; i < 6; i++) {
      fireworks.push(spawnFirework(true));
    }

    // ---------------------------------------------------------
    // 水辺の小光
    // ---------------------------------------------------------

    fireflyLights = [];

    for (let i = 0; i < 24; i++) {
      fireflyLights.push({
        x: Math.random() * w,
        y: h * (0.68 + Math.random() * 0.2),
        phase: Math.random() * Math.PI * 2,
        drift: 8 + Math.random() * 14,
      });
    }

    // ---------------------------------------------------------
    // 木
    // ---------------------------------------------------------

    trees = [
      // 左側：大きな木
      {
        x: w * 0.13,
        y: h * 0.82,
        size: h * 0.14,
        type: 'large',
        phase: Math.random() * Math.PI * 2,
      },

      // ビルの近く：大きな木
      {
        x: w * 0.30,
        y: h * 0.80,
        size: h * 0.10,
        type: 'large',
        phase: Math.random() * Math.PI * 2,
      },

      // 小さな木
      {
        x: w * 0.39,
        y: h * 0.81,
        size: h * 0.065,
        type: 'small',
        phase: Math.random() * Math.PI * 2,
      },

      {
        x: w * 0.46,
        y: h * 0.82,
        size: h * 0.052,
        type: 'small',
        phase: Math.random() * Math.PI * 2,
      },

      // 右側
      {
        x: w * 0.83,
        y: h * 0.81,
        size: h * 0.085,
        type: 'large',
        phase: Math.random() * Math.PI * 2,
      },

      {
        x: w * 0.90,
        y: h * 0.82,
        size: h * 0.05,
        type: 'small',
        phase: Math.random() * Math.PI * 2,
      },
    ];

    // ---------------------------------------------------------
    // 飛行機
    // ---------------------------------------------------------

    airplanes = [
      {
        x: -w * 0.15,
        y: h * 0.18,
        speed: w * 0.012,
        scale: Math.max(0.5, Math.min(w, h) / 700),
        phase: 0,
      },
    ];
  };

  // =========================================================
  // Firework
  // =========================================================

  function spawnFirework(initial = false) {
    const colors = [
      {
        hue: 0,
        saturation: 95,
        light: 65,
      }, // 赤

      {
        hue: 210,
        saturation: 95,
        light: 68,
      }, // 青

      {
        hue: 42,
        saturation: 95,
        light: 70,
      }, // 金

      {
        hue: 330,
        saturation: 85,
        light: 72,
      }, // 桃
    ];

    const color =
      colors[Math.floor(Math.random() * colors.length)];

    return {
      x: w * (0.34 + Math.random() * 0.58),
      y: h * (0.15 + Math.random() * 0.24),

      r: 14 + Math.random() * 26,

      life: initial
        ? Math.random() * 1.1
        : 0,

      speed: 0.18 + Math.random() * 0.16,

      hue: color.hue,
      saturation: color.saturation,
      light: color.light,

      rays: 18 + Math.floor(Math.random() * 12),
    };
  }

  // =========================================================
  // Resize
  // =========================================================

  const resize = () => {
    w = canvas.width = canvas.clientWidth;
    h = canvas.height = canvas.clientHeight;

    if (w > 0 && h > 0) {
      generateScene();
    }
  };

  window.addEventListener('resize', resize);

  resize();

  // =========================================================
  // Sky
  // =========================================================

  function drawSky() {
    const horizon = h * 0.52;

    const grad =
      ctx.createLinearGradient(
        0,
        0,
        0,
        horizon
      );

    grad.addColorStop(0, '#17284f');
    grad.addColorStop(0.35, '#355c8c');
    grad.addColorStop(0.68, '#f08a5d');
    grad.addColorStop(1, '#ffd3a1');

    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, horizon);

    // ---------------------------------------------------------
    // 夕日
    // ---------------------------------------------------------

    const sx = w * 0.68;
    const sy = horizon - h * 0.03;
    const sr = Math.min(w, h) * 0.06;

    ctx.save();

    ctx.shadowBlur =
      55 + Math.sin(t * 1.4) * 8;

    ctx.shadowColor =
      'rgba(255,190,120,0.8)';

    ctx.fillStyle = '#ffe9c9';

    ctx.beginPath();
    ctx.arc(
      sx,
      sy,
      sr,
      0,
      Math.PI * 2
    );

    ctx.fill();

    ctx.restore();

    // ---------------------------------------------------------
    // 雲
    // ---------------------------------------------------------

    cloudBands.forEach((c) => {
      const x =
        (c.offset +
          t * c.speed * 8) %
          (w + c.width) -
        c.width;

      const g =
        ctx.createLinearGradient(
          x,
          c.y,
          x + c.width,
          c.y
        );

      g.addColorStop(
        0,
        'rgba(255,230,210,0)'
      );

      g.addColorStop(
        0.5,
        `rgba(255,230,210,${c.alpha})`
      );

      g.addColorStop(
        1,
        'rgba(255,230,210,0)'
      );

      ctx.fillStyle = g;

      ctx.fillRect(
        x,
        c.y,
        c.width,
        c.height
      );
    });
  }

  // =========================================================
  // Airplane
  // =========================================================

  function drawAirplanes() {
    airplanes.forEach((plane) => {
      plane.x += plane.speed * 0.016 * 60;

      if (plane.x > w + 100) {
        plane.x = -120;
        plane.y =
          h * (0.10 + Math.random() * 0.15);
      }

      const bob =
        Math.sin(t * 1.2 + plane.phase) * 2;

      ctx.save();

      ctx.translate(
        plane.x,
        plane.y + bob
      );

      ctx.scale(
        plane.scale,
        plane.scale
      );

      ctx.rotate(-0.06);

      // 機体
      ctx.fillStyle =
        'rgba(238,244,255,0.82)';

      ctx.beginPath();

      ctx.moveTo(-24, 0);
      ctx.lineTo(20, -3);
      ctx.lineTo(31, 0);
      ctx.lineTo(20, 3);
      ctx.lineTo(-24, 3);

      ctx.closePath();
      ctx.fill();

      // -------------------------------------------------------
      // 主翼
      // -------------------------------------------------------

      ctx.fillStyle =
        'rgba(210,220,235,0.80)';

      ctx.beginPath();

      ctx.moveTo(0, 0);
      ctx.lineTo(-11, -15);
      ctx.lineTo(7, -2);

      ctx.closePath();
      ctx.fill();

      ctx.beginPath();

      ctx.moveTo(0, 2);
      ctx.lineTo(-10, 14);
      ctx.lineTo(8, 3);

      ctx.closePath();
      ctx.fill();

      // -------------------------------------------------------
      // 尾翼
      // -------------------------------------------------------

      ctx.beginPath();

      ctx.moveTo(-18, 0);
      ctx.lineTo(-23, -9);
      ctx.lineTo(-10, 0);

      ctx.closePath();
      ctx.fill();

      // -------------------------------------------------------
      // 航空灯
      // -------------------------------------------------------

      const blink =
        Math.sin(t * 8) > 0
          ? 0.9
          : 0.15;

      ctx.fillStyle =
        `rgba(255,60,60,${blink})`;

      ctx.beginPath();

      ctx.arc(
        -5,
        -13,
        1.5,
        0,
        Math.PI * 2
      );

      ctx.fill();

      ctx.restore();
    });
  }

  // =========================================================
  // City + River
  // =========================================================

  function drawCityAndRiver() {
    const horizon = h * 0.52;
    const riverY = h * 0.62;

    // ---------------------------------------------------------
    // 街
    // ---------------------------------------------------------

    ctx.fillStyle =
      'rgba(28,24,36,0.58)';

    cityBlocks.forEach((b) => {
      ctx.fillRect(
        b.x,
        horizon +
          h * 0.02 -
          b.h,
        b.w,
        b.h
      );
    });

    // ---------------------------------------------------------
    // 窓
    // ---------------------------------------------------------

    windowLights.forEach((l) => {
      const a =
        0.35 +
        (
          Math.sin(
            t * 2.8 +
            l.phase
          ) *
            0.35 +
          0.35
        );

      ctx.fillStyle =
        `rgba(255,215,150,${a})`;

      ctx.fillRect(
        l.x,
        l.y,
        3,
        4
      );
    });

    // ---------------------------------------------------------
    // 川
    // ---------------------------------------------------------

    const rg =
      ctx.createLinearGradient(
        0,
        riverY,
        0,
        h
      );

    rg.addColorStop(
      0,
      '#4f6b8d'
    );

    rg.addColorStop(
      0.45,
      '#385673'
    );

    rg.addColorStop(
      1,
      '#263f57'
    );

    ctx.fillStyle = rg;

    ctx.fillRect(
      0,
      riverY,
      w,
      h - riverY
    );

    // ---------------------------------------------------------
    // 夕日の反射
    // ---------------------------------------------------------

    const reflectGrad =
      ctx.createLinearGradient(
        w * 0.68,
        riverY,
        w * 0.68,
        h
      );

    reflectGrad.addColorStop(
      0,
      'rgba(255,220,170,0.30)'
    );

    reflectGrad.addColorStop(
      1,
      'rgba(255,220,170,0)'
    );

    ctx.fillStyle = reflectGrad;

    ctx.fillRect(
      w * 0.58,
      riverY,
      w * 0.2,
      h - riverY
    );

    // ---------------------------------------------------------
    // 波
    // ---------------------------------------------------------

    riverWaves.forEach((wv) => {
      ctx.strokeStyle =
        `rgba(220,235,255,${wv.alpha})`;

      ctx.lineWidth = 1;

      ctx.beginPath();

      for (
        let x = 0;
        x <= w;
        x += 8
      ) {
        const yy =
          wv.y +
          Math.sin(
            x * wv.freq +
            t * 2 +
            wv.phase
          ) *
            wv.amp;

        if (x === 0) {
          ctx.moveTo(x, yy);
        } else {
          ctx.lineTo(x, yy);
        }
      }

      ctx.stroke();
    });
  }

  // =========================================================
  // Trees
  // =========================================================

  function drawTree(tree) {
    const sway =
      Math.sin(
        t * 1.5 +
        tree.phase
      ) *
      tree.size *
      0.018;

    const trunkHeight =
      tree.size * 0.48;

    const trunkWidth =
      tree.size * 0.10;

    ctx.save();

    ctx.translate(
      tree.x,
      tree.y
    );

    // ---------------------------------------------------------
    // 幹
    // ---------------------------------------------------------

    ctx.fillStyle = '#4c3527';

    ctx.beginPath();

    ctx.moveTo(
      -trunkWidth / 2,
      0
    );

    ctx.lineTo(
      -trunkWidth * 0.28 +
        sway,
      -trunkHeight
    );

    ctx.lineTo(
      trunkWidth * 0.28 +
        sway,
      -trunkHeight
    );

    ctx.lineTo(
      trunkWidth / 2,
      0
    );

    ctx.closePath();
    ctx.fill();

    // ---------------------------------------------------------
    // 木の葉
    // ---------------------------------------------------------

    const canopyY =
      -trunkHeight;

    const canopyR =
      tree.size * 0.30;

    const leafGradient =
      ctx.createRadialGradient(
        sway,
        canopyY -
          canopyR * 0.2,
        canopyR * 0.1,

        sway,
        canopyY,
        canopyR
      );

    leafGradient.addColorStop(
      0,
      '#78935b'
    );

    leafGradient.addColorStop(
      0.55,
      '#4f713e'
    );

    leafGradient.addColorStop(
      1,
      '#29472c'
    );

    ctx.fillStyle =
      leafGradient;

    const leaves = [
      [-0.28, 0.05, 0.72],
      [0.28, 0.03, 0.68],
      [0, -0.26, 0.82],
      [-0.12, -0.45, 0.58],
      [0.18, -0.42, 0.55],
    ];

    leaves.forEach(
      ([ox, oy, scale]) => {
        ctx.beginPath();

        ctx.arc(
          sway +
            canopyR * ox,

          canopyY +
            canopyR * oy,

          canopyR * scale,

          0,
          Math.PI * 2
        );

        ctx.fill();
      }
    );

    ctx.restore();
  }

  function drawTrees() {
    trees
      .slice()
      .sort(
        (a, b) =>
          a.size - b.size
      )
      .forEach(drawTree);
  }

  // =========================================================
  // Levee
  // =========================================================

  function drawLeveeAndGrass() {
    ctx.fillStyle = '#2f4a2f';

    ctx.beginPath();

    ctx.moveTo(0, h);
    ctx.lineTo(0, h * 0.82);

    ctx.quadraticCurveTo(
      w * 0.35,
      h * 0.74,
      w * 0.65,
      h * 0.81
    );

    ctx.quadraticCurveTo(
      w * 0.84,
      h * 0.86,
      w,
      h * 0.80
    );

    ctx.lineTo(w, h);

    ctx.closePath();

    ctx.fill();

    // ---------------------------------------------------------
    // 草
    // ---------------------------------------------------------

    grassBlades.forEach((g) => {
      const sway =
        Math.sin(
          t * 2 +
          g.phase
        ) * 4;

      ctx.strokeStyle =
        'rgba(120,175,110,0.55)';

      ctx.lineWidth = 1.2;

      ctx.beginPath();

      ctx.moveTo(
        g.x,
        g.y
      );

      ctx.quadraticCurveTo(
        g.x +
          g.lean * 4 +
          sway,

        g.y -
          g.len * 0.6,

        g.x +
          g.lean * 8 +
          sway,

        g.y -
          g.len
      );

      ctx.stroke();
    });
  }

  // =========================================================
  // Fireworks
  // =========================================================

  function drawFireworksAndLights() {
    fireworks.forEach(
      (f, idx) => {
        f.life +=
          f.speed *
          0.016 *
          60;

        const progress =
          Math.min(
            f.life / 1.15,
            1
          );

        const expansion =
          Math.sin(
            progress *
            Math.PI
          );

        const r =
          f.r *
          (
            0.4 +
            expansion *
            1.2
          );

        const alpha =
          Math.max(
            0,
            1 -
              progress
          );

        ctx.save();

        ctx.translate(
          f.x,
          f.y
        );

        ctx.shadowBlur =
          10 +
          expansion * 10;

        ctx.shadowColor =
          `hsla(
            ${f.hue},
            ${f.saturation}%,
            ${f.light}%,
            ${alpha}
          )`;

        // -----------------------------------------------------
        // 放射状の花火
        // -----------------------------------------------------

        for (
          let i = 0;
          i < f.rays;
          i++
        ) {
          const ang =
            (i / f.rays) *
              Math.PI *
              2 +
            f.life * 0.15;

          const inner =
            r * 0.25;

          const outer =
            r *
            (
              0.78 +
              Math.random() *
                0.22
            );

          const sx =
            Math.cos(ang) *
            inner;

          const sy =
            Math.sin(ang) *
            inner;

          const ex =
            Math.cos(ang) *
            outer;

          const ey =
            Math.sin(ang) *
              outer +
            progress *
              progress *
              6;

          ctx.strokeStyle =
            `hsla(
              ${f.hue},
              ${f.saturation}%,
              ${f.light}%,
              ${alpha * 0.65}
            )`;

          ctx.lineWidth = 1.5;

          ctx.beginPath();

          ctx.moveTo(
            sx,
            sy
          );

          ctx.lineTo(
            ex,
            ey
          );

          ctx.stroke();

          // 花火の先端
          ctx.fillStyle =
            `hsla(
              ${f.hue},
              100%,
              82%,
              ${alpha * 0.8}
            )`;

          ctx.beginPath();

          ctx.arc(
            ex,
            ey,
            1.3,
            0,
            Math.PI * 2
          );

          ctx.fill();
        }

        ctx.restore();

        if (f.life > 1.15) {
          fireworks[idx] =
            spawnFirework(false);
        }
      }
    );

    // ---------------------------------------------------------
    // 水辺の小光
    // ---------------------------------------------------------

    fireflyLights.forEach((fl) => {
      const y =
        fl.y +
        Math.sin(
          t * 0.9 +
          fl.phase
        ) *
          3;

      const x =
        fl.x +
        Math.cos(
          t * 0.7 +
          fl.phase
        ) *
          fl.drift *
          0.2;

      const a =
        0.25 +
        (
          Math.sin(
            t * 2.2 +
            fl.phase
          ) *
            0.25 +
          0.25
        );

      ctx.fillStyle =
        `rgba(
          255,
          225,
          170,
          ${a}
        )`;

      ctx.beginPath();

      ctx.arc(
        x,
        y,
        1.8,
        0,
        Math.PI * 2
      );

      ctx.fill();
    });
  }

  // =========================================================
  // UI
  // =========================================================

  function drawUI() {
    ctx.save();

    ctx.font =
      `bold italic ${
        h * 0.04
      }px "Arial Black", Impact, sans-serif`;

    ctx.textAlign =
      'right';

    ctx.textBaseline =
      'bottom';

    ctx.shadowBlur = 10;

    ctx.shadowColor =
      '#ffd8a8';

    ctx.fillStyle =
      '#ffffff';

    ctx.fillText(
      'ADC-01',
      w * 0.96,
      h * 0.98
    );

    ctx.shadowBlur = 0;

    ctx.fillStyle =
      '#ffd8a8';

    ctx.fillRect(
      w * 0.965,
      h * 0.94,
      w * 0.015,
      h * 0.04
    );

    ctx.restore();
  }

  // =========================================================
  // Main loop
  // =========================================================

  function draw() {
    t += 0.016;

    if (
      w === 0 ||
      h === 0
    ) {
      raf =
        requestAnimationFrame(
          draw
        );

      return;
    }

    ctx.clearRect(
      0,
      0,
      w,
      h
    );

    // 奥 → 手前の順
    drawSky();

    // 空の遠景
    drawAirplanes();

    // 街と川
    drawCityAndRiver();

    // 花火
    drawFireworksAndLights();

    // 土手
    drawLeveeAndGrass();

    // 木は土手より手前
    drawTrees();

    // UI
    drawUI();

    raf =
      requestAnimationFrame(
        draw
      );
  }

  draw();

  // =========================================================
  // Cleanup
  // =========================================================

  return function stop() {
    cancelAnimationFrame(raf);

    window.removeEventListener(
      'resize',
      resize
    );
  };
}