// katsushika.js
export const key = 'katsushika';
export const label =
  '葛飾区：堀切菖蒲園 - 水辺に咲く江戸の花菖蒲';

/**
 * 葛飾区・堀切菖蒲園をモチーフにしたCanvas演出。
 *
 * 他区の「都市景観」「ビル」「夜景」「花火」とは構造を分離し、
 * 画面全体を初夏の菖蒲園として表現する。
 *
 * 表現要素
 * ・紫、白、藤色、桃色の花菖蒲
 * ・細長い菖蒲の葉
 * ・水を含んだ花菖蒲田
 * ・園内の木道
 * ・水面の波紋
 * ・舞い落ちる花びら
 * ・トンボ
 * ・奥に見える庭園の緑
 */
export function run(canvas) {
  const ctx = canvas.getContext('2d');

  let w = 0;
  let h = 0;
  let raf = null;
  let t = 0;

  let irises = [];
  let leaves = [];
  let petals = [];
  let ripples = [];
  let dragonflies = [];
  let backgroundPlants = [];

  // =========================================================
  // 色
  // =========================================================

  const IRIS_COLORS = [
    {
      main: '#6d4aa2',
      light: '#a78bd4',
      dark: '#47306f',
    },
    {
      main: '#8050b5',
      light: '#c1a4e3',
      dark: '#53347d',
    },
    {
      main: '#efeaf6',
      light: '#ffffff',
      dark: '#b8adca',
    },
    {
      main: '#b59aca',
      light: '#ddd0eb',
      dark: '#79688c',
    },
    {
      main: '#d69bb6',
      light: '#f1cadc',
      dark: '#945c79',
    },
    {
      main: '#51438f',
      light: '#8879c0',
      dark: '#342b64',
    },
  ];

  // =========================================================
  // 初期生成
  // =========================================================

  function generateScene() {
    irises = [];
    leaves = [];
    petals = [];
    ripples = [];
    dragonflies = [];
    backgroundPlants = [];

    // -------------------------------------------------------
    // 背景の植物
    // -------------------------------------------------------

    for (let i = 0; i < 100; i++) {
      backgroundPlants.push({
        x: Math.random() * w,
        y: h * (0.15 + Math.random() * 0.32),
        size: h * (0.018 + Math.random() * 0.04),
        phase: Math.random() * Math.PI * 2,
      });
    }

    // -------------------------------------------------------
    // 菖蒲の葉
    // -------------------------------------------------------

    for (let i = 0; i < 320; i++) {
      leaves.push({
        x: Math.random() * w,
        y: h * (0.48 + Math.random() * 0.5),

        height:
          h *
          (0.07 +
            Math.random() * 0.18),

        width:
          1.2 +
          Math.random() * 2,

        lean:
          -12 +
          Math.random() * 24,

        phase:
          Math.random() *
          Math.PI *
          2,

        depth:
          Math.random(),
      });
    }

    // -------------------------------------------------------
    // 花菖蒲
    // -------------------------------------------------------

    for (let i = 0; i < 95; i++) {
      const y =
        h *
        (0.42 +
          Math.random() * 0.5);

      const depth =
        (y - h * 0.42) /
        (h * 0.5);

      const color =
        IRIS_COLORS[
          Math.floor(
            Math.random() *
              IRIS_COLORS.length
          )
        ];

      irises.push({
        x: Math.random() * w,
        y,

        size:
          h *
          (0.018 +
            depth * 0.045),

        stemHeight:
          h *
          (0.055 +
            depth * 0.11),

        rotation:
          -0.15 +
          Math.random() * 0.3,

        phase:
          Math.random() *
          Math.PI *
          2,

        color,

        depth,
      });
    }

    // 奥 → 手前
    irises.sort(
      (a, b) =>
        a.y - b.y
    );

    // -------------------------------------------------------
    // 花びら
    // -------------------------------------------------------

    for (let i = 0; i < 16; i++) {
      petals.push(
        createPetal(true)
      );
    }

    // -------------------------------------------------------
    // 水面の波紋
    // -------------------------------------------------------

    for (let i = 0; i < 10; i++) {
      ripples.push({
        x: Math.random() * w,
        y:
          h *
          (0.7 +
            Math.random() * 0.25),

        life:
          Math.random(),

        speed:
          0.08 +
          Math.random() * 0.08,

        size:
          5 +
          Math.random() * 14,
      });
    }

    // -------------------------------------------------------
    // トンボ
    // -------------------------------------------------------

    dragonflies = [
      {
        x: w * 0.2,
        y: h * 0.28,
        phase: 0,
        speed: 0.8,
      },
      {
        x: w * 0.75,
        y: h * 0.35,
        phase: 2.5,
        speed: 0.55,
      },
    ];
  }

  function createPetal(initial = false) {
    return {
      x: Math.random() * w,

      y: initial
        ? Math.random() * h
        : -20,

      size:
        3 +
        Math.random() * 5,

      speed:
        8 +
        Math.random() * 15,

      drift:
        12 +
        Math.random() * 20,

      phase:
        Math.random() *
        Math.PI *
        2,

      rotation:
        Math.random() *
        Math.PI *
        2,

      rotateSpeed:
        -0.7 +
        Math.random() * 1.4,

      color:
        Math.random() > 0.45
          ? '#bda7df'
          : '#eee8f5',
    };
  }

  // =========================================================
  // Resize
  // =========================================================

  function resize() {
    w =
      canvas.width =
      canvas.clientWidth;

    h =
      canvas.height =
      canvas.clientHeight;

    if (w > 0 && h > 0) {
      generateScene();
    }
  }

  window.addEventListener(
    'resize',
    resize
  );

  resize();

  // =========================================================
  // 背景
  // =========================================================

  function drawBackground() {
    // 雨上がりの淡い空
    const sky =
      ctx.createLinearGradient(
        0,
        0,
        0,
        h
      );

    sky.addColorStop(
      0,
      '#dce9e9'
    );

    sky.addColorStop(
      0.35,
      '#cdded8'
    );

    sky.addColorStop(
      0.58,
      '#819a78'
    );

    sky.addColorStop(
      1,
      '#304b3c'
    );

    ctx.fillStyle = sky;

    ctx.fillRect(
      0,
      0,
      w,
      h
    );

    // -------------------------------------------------------
    // 遠景の木々
    // -------------------------------------------------------

    const treeGrad =
      ctx.createLinearGradient(
        0,
        h * 0.15,
        0,
        h * 0.5
      );

    treeGrad.addColorStop(
      0,
      '#68806a'
    );

    treeGrad.addColorStop(
      1,
      '#39543f'
    );

    ctx.fillStyle = treeGrad;

    ctx.beginPath();

    ctx.moveTo(
      0,
      h * 0.42
    );

    for (
      let x = 0;
      x <= w;
      x += w / 20
    ) {
      const y =
        h *
        (
          0.31 +
          Math.sin(
            x * 0.018
          ) *
            0.025 +
          Math.random() *
            0.025
        );

      ctx.lineTo(
        x,
        y
      );
    }

    ctx.lineTo(
      w,
      h * 0.55
    );

    ctx.lineTo(
      0,
      h * 0.55
    );

    ctx.closePath();

    ctx.fill();

    // -------------------------------------------------------
    // 木々の細かな葉
    // -------------------------------------------------------

    backgroundPlants.forEach(
      (p) => {
        const sway =
          Math.sin(
            t * 0.8 +
            p.phase
          ) *
          2;

        ctx.fillStyle =
          'rgba(105,140,90,0.28)';

        ctx.beginPath();

        ctx.arc(
          p.x + sway,
          p.y,
          p.size,
          0,
          Math.PI * 2
        );

        ctx.fill();
      }
    );
  }

  // =========================================================
  // 菖蒲田
  // =========================================================

  function drawIrisField() {
    // 土・浅い水
    const field =
      ctx.createLinearGradient(
        0,
        h * 0.43,
        0,
        h
      );

    field.addColorStop(
      0,
      '#607b5a'
    );

    field.addColorStop(
      0.35,
      '#536f50'
    );

    field.addColorStop(
      0.65,
      '#4b6250'
    );

    field.addColorStop(
      1,
      '#30473c'
    );

    ctx.fillStyle = field;

    ctx.fillRect(
      0,
      h * 0.42,
      w,
      h * 0.58
    );

    // -------------------------------------------------------
    // 水の小さな反射
    // -------------------------------------------------------

    for (
      let i = 0;
      i < 24;
      i++
    ) {
      const x =
        (
          i * 79 +
          t * 5
        ) %
        w;

      const y =
        h *
        (
          0.58 +
          (
            i % 7
          ) *
            0.055
        );

      ctx.strokeStyle =
        'rgba(210,230,220,0.12)';

      ctx.lineWidth = 1;

      ctx.beginPath();

      ctx.moveTo(
        x,
        y
      );

      ctx.lineTo(
        x + 18,
        y
      );

      ctx.stroke();
    }
  }

  // =========================================================
  // 木道
  // =========================================================

  function drawBoardwalk() {
    /*
     * 一点透視。
     * 奥は細く、手前に向かって広がる。
     *
     * これによって「菖蒲園を歩いている」感覚を作る。
     */

    const topY =
      h * 0.46;

    const bottomY =
      h;

    const topLeft =
      w * 0.48;

    const topRight =
      w * 0.54;

    const bottomLeft =
      w * 0.28;

    const bottomRight =
      w * 0.64;

    // -------------------------------------------------------
    // 木道本体
    // -------------------------------------------------------

    const wood =
      ctx.createLinearGradient(
        0,
        topY,
        0,
        bottomY
      );

    wood.addColorStop(
      0,
      '#9b886b'
    );

    wood.addColorStop(
      1,
      '#665642'
    );

    ctx.fillStyle = wood;

    ctx.beginPath();

    ctx.moveTo(
      topLeft,
      topY
    );

    ctx.lineTo(
      topRight,
      topY
    );

    ctx.lineTo(
      bottomRight,
      bottomY
    );

    ctx.lineTo(
      bottomLeft,
      bottomY
    );

    ctx.closePath();

    ctx.fill();

    // -------------------------------------------------------
    // 板の境目
    // -------------------------------------------------------

    for (
      let i = 0;
      i < 18;
      i++
    ) {
      const p =
        i / 18;

      // 遠近法的に間隔を広げる
      const pp =
        p * p;

      const y =
        topY +
        (
          bottomY -
          topY
        ) *
          pp;

      const left =
        topLeft +
        (
          bottomLeft -
          topLeft
        ) *
          pp;

      const right =
        topRight +
        (
          bottomRight -
          topRight
        ) *
          pp;

      ctx.strokeStyle =
        'rgba(55,45,35,0.32)';

      ctx.lineWidth =
        0.7 +
        p * 1.2;

      ctx.beginPath();

      ctx.moveTo(
        left,
        y
      );

      ctx.lineTo(
        right,
        y
      );

      ctx.stroke();
    }

    // -------------------------------------------------------
    // 雨に濡れた光沢
    // -------------------------------------------------------

    ctx.strokeStyle =
      'rgba(240,250,245,0.13)';

    ctx.lineWidth = 2;

    ctx.beginPath();

    ctx.moveTo(
      w * 0.51,
      topY
    );

    ctx.lineTo(
      w * 0.46,
      bottomY
    );

    ctx.stroke();
  }

  // =========================================================
  // 葉
  // =========================================================

  function drawLeaves() {
    leaves
      .slice()
      .sort(
        (a, b) =>
          a.depth -
          b.depth
      )
      .forEach(
        (leaf) => {
          const sway =
            Math.sin(
              t * 1.4 +
              leaf.phase
            ) *
            3;

          ctx.strokeStyle =
            leaf.depth > 0.55
              ? '#436742'
              : 'rgba(75,110,67,0.72)';

          ctx.lineWidth =
            leaf.width *
            (
              0.65 +
              leaf.depth *
                0.7
            );

          ctx.beginPath();

          ctx.moveTo(
            leaf.x,
            leaf.y
          );

          ctx.quadraticCurveTo(
            leaf.x +
              leaf.lean *
                0.35,

            leaf.y -
              leaf.height *
                0.55,

            leaf.x +
              leaf.lean +
              sway,

            leaf.y -
              leaf.height
          );

          ctx.stroke();
        }
      );
  }

  // =========================================================
  // 花菖蒲
  // =========================================================

  function drawIris(flower) {
    const sway =
      Math.sin(
        t * 1.2 +
        flower.phase
      ) *
      flower.size *
      0.09;

    ctx.save();

    ctx.translate(
      flower.x + sway,
      flower.y
    );

    ctx.rotate(
      flower.rotation
    );

    // -------------------------------------------------------
    // 茎
    // -------------------------------------------------------

    ctx.strokeStyle =
      '#42693f';

    ctx.lineWidth =
      Math.max(
        1.2,
        flower.size * 0.07
      );

    ctx.beginPath();

    ctx.moveTo(
      0,
      0
    );

    ctx.quadraticCurveTo(
      -sway * 0.2,
      -flower.stemHeight *
        0.5,

      sway * 0.1,
      -flower.stemHeight
    );

    ctx.stroke();

    ctx.translate(
      sway * 0.1,
      -flower.stemHeight
    );

    drawIrisBloom(
      flower.size,
      flower.color
    );

    ctx.restore();
  }

  // =========================================================
  // 花そのもの
  // =========================================================

  function drawIrisBloom(
    size,
    color
  ) {
    /*
     * 花菖蒲を「ただの丸い花」にしないため、
     *
     * 1. 外側の垂れた花弁
     * 2. 上向きの内花被
     * 3. 黄色い筋
     *
     * の三層に分ける。
     */

    // -------------------------------------------------------
    // 外側の3枚
    // -------------------------------------------------------

    for (
      let i = 0;
      i < 3;
      i++
    ) {
      const angle =
        i *
          (
            Math.PI *
            2 /
            3
          ) +
        Math.PI / 2;

      ctx.save();

      ctx.rotate(
        angle
      );

      const petalGradient =
        ctx.createLinearGradient(
          0,
          0,
          0,
          size
        );

      petalGradient.addColorStop(
        0,
        color.light
      );

      petalGradient.addColorStop(
        0.55,
        color.main
      );

      petalGradient.addColorStop(
        1,
        color.dark
      );

      ctx.fillStyle =
        petalGradient;

      ctx.beginPath();

      ctx.moveTo(
        0,
        0
      );

      ctx.bezierCurveTo(
        -size * 0.38,
        size * 0.14,

        -size * 0.48,
        size * 0.55,

        0,
        size * 0.75
      );

      ctx.bezierCurveTo(
        size * 0.48,
        size * 0.55,

        size * 0.38,
        size * 0.14,

        0,
        0
      );

      ctx.fill();

      // 黄色い筋
      ctx.strokeStyle =
        'rgba(245,200,70,0.85)';

      ctx.lineWidth =
        Math.max(
          0.8,
          size * 0.035
        );

      ctx.beginPath();

      ctx.moveTo(
        0,
        size * 0.08
      );

      ctx.lineTo(
        0,
        size * 0.45
      );

      ctx.stroke();

      ctx.restore();
    }

    // -------------------------------------------------------
    // 内側の3枚
    // -------------------------------------------------------

    for (
      let i = 0;
      i < 3;
      i++
    ) {
      const angle =
        i *
        (
          Math.PI *
          2 /
          3
        );

      ctx.save();

      ctx.rotate(
        angle
      );

      ctx.fillStyle =
        color.light;

      ctx.beginPath();

      ctx.moveTo(
        0,
        0
      );

      ctx.bezierCurveTo(
        -size * 0.23,
        -size * 0.12,

        -size * 0.20,
        -size * 0.42,

        0,
        -size * 0.48
      );

      ctx.bezierCurveTo(
        size * 0.20,
        -size * 0.42,

        size * 0.23,
        -size * 0.12,

        0,
        0
      );

      ctx.fill();

      ctx.restore();
    }

    // -------------------------------------------------------
    // 花芯
    // -------------------------------------------------------

    ctx.fillStyle =
      '#e5c754';

    ctx.beginPath();

    ctx.arc(
      0,
      0,
      size * 0.09,
      0,
      Math.PI * 2
    );

    ctx.fill();
  }

  function drawIrises() {
    irises.forEach(
      drawIris
    );
  }

  // =========================================================
  // 波紋
  // =========================================================

  function drawRipples() {
    ripples.forEach(
      (r) => {
        r.life +=
          r.speed *
          0.016;

        if (
          r.life > 1
        ) {
          r.life = 0;

          r.x =
            Math.random() *
            w;

          r.y =
            h *
            (
              0.65 +
              Math.random() *
                0.3
            );
        }

        const radius =
          r.size *
          (
            0.3 +
            r.life * 2.4
          );

        const alpha =
          1 -
          r.life;

        ctx.strokeStyle =
          `rgba(
            210,
            230,
            225,
            ${alpha * 0.28}
          )`;

        ctx.lineWidth = 1;

        ctx.beginPath();

        ctx.ellipse(
          r.x,
          r.y,
          radius,
          radius * 0.35,
          0,
          0,
          Math.PI * 2
        );

        ctx.stroke();
      }
    );
  }

  // =========================================================
  // 舞う花びら
  // =========================================================

  function drawPetals() {
    petals.forEach(
      (petal, index) => {
        petal.y +=
          petal.speed *
          0.016;

        petal.x +=
          Math.sin(
            t +
            petal.phase
          ) *
          petal.drift *
          0.016;

        petal.rotation +=
          petal.rotateSpeed *
          0.016;

        if (
          petal.y >
          h + 20
        ) {
          petals[index] =
            createPetal(false);

          return;
        }

        ctx.save();

        ctx.translate(
          petal.x,
          petal.y
        );

        ctx.rotate(
          petal.rotation
        );

        ctx.fillStyle =
          petal.color;

        ctx.globalAlpha =
          0.45;

        ctx.beginPath();

        ctx.ellipse(
          0,
          0,
          petal.size,
          petal.size * 0.42,
          0,
          0,
          Math.PI * 2
        );

        ctx.fill();

        ctx.restore();
      }
    );

    ctx.globalAlpha = 1;
  }

  // =========================================================
  // トンボ
  // =========================================================

  function drawDragonflies() {
    dragonflies.forEach(
      (d) => {
        const x =
          d.x +
          Math.sin(
            t *
              d.speed +
            d.phase
          ) *
            w *
            0.07;

        const y =
          d.y +
          Math.sin(
            t *
              d.speed *
              1.7 +
            d.phase
          ) *
            h *
            0.025;

        const wing =
          Math.sin(
            t * 20
          ) *
          0.35;

        ctx.save();

        ctx.translate(
          x,
          y
        );

        // 胴体
        ctx.strokeStyle =
          'rgba(50,55,45,0.75)';

        ctx.lineWidth = 1.5;

        ctx.beginPath();

        ctx.moveTo(
          -8,
          0
        );

        ctx.lineTo(
          8,
          0
        );

        ctx.stroke();

        // 頭
        ctx.fillStyle =
          '#4c5146';

        ctx.beginPath();

        ctx.arc(
          9,
          0,
          2,
          0,
          Math.PI * 2
        );

        ctx.fill();

        // 羽
        ctx.strokeStyle =
          'rgba(220,235,235,0.48)';

        ctx.lineWidth = 1;

        ctx.beginPath();

        ctx.moveTo(
          -1,
          0
        );

        ctx.lineTo(
          -8,
          -7 - wing * 4
        );

        ctx.moveTo(
          -1,
          0
        );

        ctx.lineTo(
          -8,
          7 + wing * 4
        );

        ctx.moveTo(
          2,
          0
        );

        ctx.lineTo(
          8,
          -6 + wing * 3
        );

        ctx.moveTo(
          2,
          0
        );

        ctx.lineTo(
          8,
          6 - wing * 3
        );

        ctx.stroke();

        ctx.restore();
      }
    );
  }

  // =========================================================
  // 光
  // =========================================================

  function drawAtmosphere() {
    /*
     * 晴天ではなく「雨上がりの初夏」。
     * 上から柔らかい光だけを落とす。
     */

    const light =
      ctx.createRadialGradient(
        w * 0.45,
        h * 0.05,
        0,

        w * 0.45,
        h * 0.05,
        h * 0.85
      );

    light.addColorStop(
      0,
      'rgba(255,255,245,0.20)'
    );

    light.addColorStop(
      0.5,
      'rgba(230,245,230,0.05)'
    );

    light.addColorStop(
      1,
      'rgba(20,40,30,0.12)'
    );

    ctx.fillStyle = light;

    ctx.fillRect(
      0,
      0,
      w,
      h
    );
  }

  // =========================================================
  // UI
  // =========================================================

  function drawUI() {
    ctx.save();

    ctx.textAlign =
      'left';

    ctx.textBaseline =
      'bottom';

    // 小さな縦線
    ctx.fillStyle =
      'rgba(220,205,235,0.88)';

    ctx.fillRect(
      w * 0.035,
      h * 0.905,
      2,
      h * 0.055
    );

    ctx.fillStyle =
      'rgba(255,255,255,0.90)';

    ctx.font =
      `${Math.max(
        10,
        h * 0.018
      )}px serif`;

    ctx.fillText(
      'HORIKIRI',
      w * 0.05,
      h * 0.93
    );

    ctx.font =
      `bold ${Math.max(
        12,
        h * 0.027
      )}px serif`;

    ctx.fillText(
      '花菖蒲',
      w * 0.05,
      h * 0.965
    );

    ctx.restore();
  }

  // =========================================================
  // 描画ループ
  // =========================================================

  function draw() {
    t += 0.016;

    if (
      w <= 0 ||
      h <= 0
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

    // 奥
    drawBackground();

    // 菖蒲田
    drawIrisField();

    // 水面
    drawRipples();

    // 葉
    drawLeaves();

    // 木道
    drawBoardwalk();

    // 花
    drawIrises();

    // 小さな生き物
    drawDragonflies();

    // 空気感
    drawPetals();

    drawAtmosphere();

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
    if (raf) {
      cancelAnimationFrame(
        raf
      );
    }

    window.removeEventListener(
      'resize',
      resize
    );
  };
}