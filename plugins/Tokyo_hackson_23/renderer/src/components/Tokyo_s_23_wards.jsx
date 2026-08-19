// Tokyo_s_23_wards.jsx 
import React, { useEffect, useRef, useState, useMemo, forwardRef, useImperativeHandle } from 'react';
import { useWardLabels } from './wardnav/wardLabels';
import { useWardKeyboardNav } from './wardnav/useWardKeyboardNav';

const getFireworkColor = (code) => {
  const palette = [
    '#ff2a6d', '#ffae19', '#05d5e7', '#d300c5', '#00ff9f', '#ff5e00', '#fff066'
  ];
  const num = parseInt(code, 10) || 1;
  return palette[num % palette.length];
};

// ============================================================
// 決定論的な疑似乱数（区コードから生成 → 再レンダリングしても値がブレない）
// ============================================================
function hashSeed(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = (Math.imul(31, h) + str.charCodeAt(i)) | 0;
  }
  return h;
}

function mulberry32(seed) {
  let s = seed | 0;
  return function () {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);
const lerp = (a, b, t) => a + (b - a) * t;
const clamp01 = (v) => Math.min(Math.max(v, 0), 1);

// 🌟 全体のベースズーム倍率（10〜20%拡大の指定に合わせて1.15固定）
const BASE_SCALE = 1.0;
const HUMAN_VIEW_SCALE = 3.2;
const HUMAN_VIEW_TILT = 55; // 度。0=真上から、90=ほぼ水平

// =========================================================
// コンポーネント本体（App.jsxからrefを受け取れるようにforwardRefを使用）
// =========================================================
const Area23Map = forwardRef(function Area23Map({ 
  districts, 
  selectedCode, 
  selectedCategory, // 👈 追加: App.jsxから渡されるテーマ
  onSelectDistrict, 
  onSettleChange 
}, ref) {
  
  // アニメーションループ内で最新の選択状態を見るためのRef
  const selectedCodeRef = useRef(selectedCode);
  useEffect(() => {
    selectedCodeRef.current = selectedCode;
  }, [selectedCode]);

  const canvasRef = useRef(null);
  const containerRef = useRef(null); // scale/translate をかける対象（ズーム＆パン用）
  const outerRef = useRef(null);     // スクロール進捗の計測基準（sticky + 内部スクロール）

  // 手動ズーム（Ctrl/Cmd + ホイールで探索用）
  const [manualScale, setManualScale] = useState(BASE_SCALE);
  const [transformOrigin, setTransformOrigin] = useState('50% 50%');

  // スクロール進捗（0=まだ画面下、1=完全に収束済み）
  const [scrollProgress, setScrollProgress] = useState(0);

  // =========================================================
  // 🌟 親コンポーネント(App.jsx)から呼び出せる「一番上に戻る」メソッド
  // =========================================================
  useImperativeHandle(ref, () => ({
    scrollToTop: () => {
      const el = outerRef.current;
      if (el) {
        el.scrollTo({ top: 0, behavior: 'smooth' }); // なめらかに一番上へ戻る
      }
      setScrollProgress(0);
    }
  }));

  // =========================================================
  // 🌟 カテゴリが選択された時に一気に一番下までスクロールさせる
  // =========================================================
  useEffect(() => {
    if (!selectedCategory) return;
    
    // スクロール進捗ステートを即時 1 (100%収束) にする
    setScrollProgress(1);

    // DOMのスクロール位置を最下部に同期（非同期で確実に実行）
    const el = outerRef.current;
    if (el) {
      setTimeout(() => {
        el.scrollTop = el.scrollHeight - el.clientHeight;
      }, 0);
    }
  }, [selectedCategory]);

  // =========================================================
  // 1. 星空と演出の背景描画
  // =========================================================
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    let animationFrameId;

    let width, height;
    let stars = [];
    let particles = [];
    const MAX_STARS = 400;

    const resize = () => {
      width = canvas.parentElement.clientWidth;
      height = canvas.parentElement.clientHeight;
      canvas.width = width;
      canvas.height = height;
    };
    window.addEventListener('resize', resize);
    resize();

    class Star {
      constructor() {
        this.x = Math.random() * width;
        this.y = Math.random() * height;
        this.baseSize = Math.random() * 1.5 + 0.5;
        this.size = this.baseSize;
        this.maxSize = this.baseSize * 1.2;
        this.maxOpacity = Math.random() * 0.8 + 0.2;
        this.opacity = 0;
        this.fadeSpeed = Math.random() * 0.005 + 0.002;
        this.twinkleDir = 1;
      }
      update() {
        if (this.size < this.maxSize) {
          this.size += 0.002;
          if (this.size > this.maxSize) this.size = this.maxSize;
        }
        this.opacity += this.fadeSpeed * this.twinkleDir;
        if (this.opacity >= this.maxOpacity) {
          this.opacity = this.maxOpacity;
          this.twinkleDir = -1;
        } else if (this.opacity <= 0.1 && this.twinkleDir === -1) {
          this.twinkleDir = 1;
          if (Math.random() > 0.8) {
            this.x = Math.random() * width;
            this.y = Math.random() * height;
            this.size = this.baseSize;
          }
        }
      }
      draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${Math.max(0, this.opacity)})`;
        ctx.fill();
      }
    }

    class CrumbleParticle {
      constructor(x, y, color, isMagic) {
        this.x = x;
        this.y = y;
        this.vx = (Math.random() - 0.5) * 10;
        this.vy = (Math.random() - 1) * 8;
        this.life = 1.0;
        this.color = color;
        this.size = Math.random() * 4 + 2;
        this.isMagic = isMagic;
      }
      update() {
        this.x += this.vx;
        this.y += this.vy;
        this.vy += 0.4;
        this.life -= 0.02;
      }
      draw() {
        ctx.globalAlpha = Math.max(0, this.life);
        ctx.fillStyle = this.color;
        if (this.isMagic) {
          ctx.beginPath();
          ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
          ctx.fill();
        } else {
          ctx.fillRect(this.x, this.y, this.size, this.size);
        }
        ctx.globalAlpha = 1.0;
      }
    }

    const spawnParticles = (x, y, isToemoji) => {
      for (let i = 0; i < 30; i++) {
        const color = isToemoji ? '#222' : '#05d5e7';
        particles.push(new CrumbleParticle(x, y, color, !isToemoji));
      }
    };

    class RockEntity {
      constructor(points, rx, ry, emoji) {
        this.points = points;
        this.rx = rx;
        this.ry = ry;
        this.emoji = emoji;
        this.state = 'ROCK';
        this.timer = Math.floor(Math.random() * 300) + 200;
      }
      update() {
        this.timer--;
        if (this.timer <= 0) {
          const cx = this.rx * width;
          const cy = this.ry * height;
          if (this.state === 'ROCK') {
            this.state = 'emoji';
            this.timer = 250 + Math.random() * 150;
            spawnParticles(cx, cy, true);
          } else {
            this.state = 'ROCK';
            this.timer = 350 + Math.random() * 200;
            spawnParticles(cx, cy, false);
          }
        }
      }
      draw() {
        if (this.state === 'ROCK') {
          ctx.fillStyle = '#030610';
          ctx.strokeStyle = 'rgba(5, 213, 231, 0.2)';
          ctx.lineWidth = 1;
          ctx.beginPath();
          this.points.forEach((p, i) => {
            if (i === 0) ctx.moveTo(p[0] * width, p[1] * height);
            else ctx.lineTo(p[0] * width, p[1] * height);
          });
          ctx.fill();
          ctx.stroke();
        } else {
          const floatY = Math.sin(Date.now() / 300) * 5;
          ctx.font = '40px sans-serif';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(this.emoji, this.rx * width, this.ry * height + floatY);

          ctx.beginPath();
          ctx.arc(this.rx * width, this.ry * height + floatY, 30, 0, Math.PI * 2);
          ctx.fillStyle = 'rgba(5, 213, 231, 0.1)';
          ctx.fill();
        }
      }
    }

    const rockEntities = [
      new RockEntity([[-0.1, 1], [0.15, 0.65], [0.25, 0.75], [0.35, 1]], 0.15, 0.8, '⚽'),
      new RockEntity([[0.2, 1], [0.4, 0.88], [0.5, 0.85], [0.65, 0.92], [0.8, 1]], 0.5, 0.9, '💗'),
      new RockEntity([[1.1, 1], [0.85, 0.55], [0.7, 0.8], [0.55, 1]], 0.85, 0.7, '⚽'),
    ];

    const render = () => {
      // 🌟区が選択中なら星空を描かずにキャンバスをクリアし、奥のWardEffectCanvasを見せる
      if (selectedCodeRef.current) {
        ctx.clearRect(0, 0, width, height);
      } else {
        const gradient = ctx.createRadialGradient(width / 2, height, 0, width / 2, height, height);
        gradient.addColorStop(0, '#0a192f');
        gradient.addColorStop(1, '#02040a');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, width, height);
      }

      if (stars.length < MAX_STARS && Math.random() < 0.2) {
        stars.push(new Star());
      }
      
      stars.forEach((s) => { s.update(); s.draw(); });
      rockEntities.forEach((rock) => { rock.update(); rock.draw(); });

      particles = particles.filter((p) => p.life > 0);
      particles.forEach((p) => { p.update(); p.draw(); });

      animationFrameId = requestAnimationFrame(render);
    };
    render();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  // =========================================================
  // 2. ホイールイベント：Ctrl/Cmd+ホイールの時だけズーム
  // =========================================================
  useEffect(() => {
    const el = outerRef.current;
    if (!el) return;

    const wheelHandler = (e) => {
      if (!(e.ctrlKey || e.metaKey)) return; 

      e.preventDefault();
      const zoomSensitivity = 0.002;
      const delta = -e.deltaY * zoomSensitivity;

      const rect = el.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      setTransformOrigin(`${x}% ${y}%`);

      setManualScale((prev) => Math.min(Math.max(prev + delta, BASE_SCALE * 0.6), 2.6));
    };

    el.addEventListener('wheel', wheelHandler, { passive: false });
    return () => el.removeEventListener('wheel', wheelHandler);
  }, []);

  // =========================================================
  // 3. スクロール進捗の計測（0〜1）
  // =========================================================
  useEffect(() => {
    const el = outerRef.current;
    if (!el) return;

    const updateProgress = () => {
      const maxScroll = el.scrollHeight - el.clientHeight;
      const progress = maxScroll > 0 ? el.scrollTop / maxScroll : 0;
      setScrollProgress(clamp01(progress));
    };

    el.addEventListener('scroll', updateProgress, { passive: true });
    window.addEventListener('resize', updateProgress, { passive: true });
    updateProgress();

    return () => {
      el.removeEventListener('scroll', updateProgress);
      window.removeEventListener('resize', updateProgress);
    };
  }, []);

  // =========================================================
  // 4. 各区の「初期の散らばり位置・回転」
  // =========================================================
  const scatterMap = useMemo(() => {
    const map = {};
    districts.forEach((d) => {
      const rand = mulberry32(hashSeed(d.code));
      map[d.code] = {
        x: d.x + (rand() - 0.5) * 240,
        y: -50 - rand() * 70,
        rotateZ: (rand() - 0.5) * 320,
        rotateX: 55 + rand() * 70,
        delay: rand() * 0.18,
      };
    });
    return map;
  }, [districts]);

  // =========================================================
  // 5. クリックでフォーカス
  // =========================================================
  const isSettled = scrollProgress > 0.45;

  useEffect(() => {
    if (onSettleChange) {
      onSettleChange(isSettled);
    }
  }, [isSettled, onSettleChange]);

  const focusedDistrict = isSettled
    ? districts.find((d) => d.code === selectedCode) || null
    : null;
    
  const { showLabels } = useWardLabels();

  useWardKeyboardNav({
    active: !!focusedDistrict,
    currentDistrict: focusedDistrict,
    districts,
    onNavigate: (next) => onSelectDistrict(next),
  });

  const focusScale = focusedDistrict ? HUMAN_VIEW_SCALE : manualScale;
  const wrapperTransform = focusedDistrict
    ? `perspective(1200px) rotateX(${HUMAN_VIEW_TILT}deg) scale(${focusScale}) translate(${-(focusedDistrict.x - 50)}%, ${-(focusedDistrict.y - 50)}%)`
    : `scale(${focusScale})`;
  const wrapperOrigin = focusedDistrict ? '50% 50%' : transformOrigin;
  const wrapperTransition = focusedDistrict
    ? 'transform 0.8s cubic-bezier(0.22, 1, 0.36, 1)'
    : 'transform 0.15s ease-out';

  // =========================================================
  // 6. JSXの返却
  // =========================================================
  return (
    <div
      ref={outerRef}
      style={{
        position: 'relative',
        height: '100vh',
        overflowY: 'auto',
        overflowX: 'hidden',
      }}
    >
      <style>{` 
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-5px); }
        }

        .b-flower {
          position: absolute;
          display: flex;
          flex-direction: column;
          align-items: center;
          will-change: transform, left, top, opacity;
          pointer-events: none; 
        }

        .flower-core {
          display: flex;
          justify-content: center;
          align-items: center;
          border-radius: 50%;
          background: radial-gradient(circle at center, rgba(255,255,255,1) 0%, rgba(5,213,231,0.8) 40%, rgba(0,0,0,0) 80%);
          pointer-events: auto;
          cursor: pointer;
          position: relative;
        }

        .flower-core::after {
          content: '';
          position: absolute;
          top: -15px; left: -15px; right: -15px; bottom: -15px;
          border-radius: 50%;
        }

        .ward-label {
          pointer-events: auto;
          cursor: pointer;
        }
        
        @keyframes fireworkBurstRing {
          0% { transform: translate(-50%, -50%) scale(0.1); opacity: 1; border-width: 4px; }
          80% { opacity: 0.8; }
          100% { transform: translate(-50%, -50%) scale(2.8); opacity: 0; border-width: 1px; }
        }
        
        @keyframes pulseGlow {
          0% { box-shadow: 0 0 12px currentColor, 0 0 25px currentColor; }
          50% { box-shadow: 0 0 25px currentColor, 0 0 50px #ffffff; }
          100% { box-shadow: 0 0 12px currentColor, 0 0 25px currentColor; }
        }
        
        @keyframes emberFlicker {
          0% { transform: scale(0.8) translateY(0px); opacity: 0.2; }
          50% { opacity: 0.9; }
          100% { transform: scale(1.4) translateY(-6px); opacity: 0.3; }
        }
      `}</style>

      {/* position: sticky でスクロールしてもマップ自体は画面内に留める */}
      <div
        ref={containerRef}
        style={{
          position: 'sticky',
          top: 0,
          left: 0,
          width: '100%',
          height: '100vh',
          transform: wrapperTransform,
          transformOrigin: wrapperOrigin,
          transition: wrapperTransition,
          overflow: 'hidden',
        }}
      >
        <canvas
          ref={canvasRef}
          style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}
        />

        <div style={{ position: 'relative', width: '100%', height: '100%', maxWidth: '1000px', margin: '0 auto' }}>
          {districts.map((district, index) => {
            const isSelected = selectedCode === district.code;
            const fireworkColor = getFireworkColor(district.code);

            const rankColor = district.categoryRankMeta?.color;
            const borderColor = rankColor || 'rgba(255, 255, 255, 0.3)';
            const borderWidth = rankColor ? '3px' : '1px';
            const glowEffect = rankColor ? `0 0 15px ${rankColor}80` : 'none';
            const floatDelay = `${(index * 0.1) % 2}s`;

            // 収束アニメーションの補間計算（スクロール前半50%で完了）
            const ANIMATION_END_RATIO = 0.5;
            const globalAnimProgress = clamp01(scrollProgress / ANIMATION_END_RATIO);

            const scatter = scatterMap[district.code];
            const localRaw = (globalAnimProgress - scatter.delay) / (1 - scatter.delay || 1);
            const localProgress = clamp01(localRaw);
            const eased = easeOutCubic(localProgress);

            const curX = lerp(scatter.x, district.x, eased);
            const curY = lerp(scatter.y, district.y, eased);
            
            // 端(0%/100%)から余白を持たせて圧縮：16〜84%の範囲に収める
            const safeX = 16 + curX * 0.68;
            const safeY = 16 + curY * 0.68;

            const curRotateZ = scatter.rotateZ * (1 - eased);
            const curRotateX = scatter.rotateX * (1 - eased);
            const settleScale = lerp(0.4, 1, eased);
            const opacity = lerp(0.05, 1, eased);
            const selectedBoost = isSelected ? 1.5 : 1;
            
            return (
              <div
                key={district.code}
                className="b-flower"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectDistrict(district);
                }}
                style={{
                  left: `${safeX}%`,
                  top: `${safeY}%`,
                  zIndex: isSelected ? 100 : 10,
                  opacity,
                  transform: `translate(-50%, -50%) perspective(900px) rotateX(${curRotateX}deg) rotateZ(${curRotateZ}deg) scale(${settleScale * selectedBoost})`,
                  transition: 'opacity 0.2s linear',
                }}
              >
                {/* 🎆 選択中の場合のみ花火の光環と火粉を描画 🎆 */}
                {isSelected && (
                  <div style={{ position: 'absolute', top: '50%', left: '50%', zIndex: -1 }}>
                    {/* 大輪の光環1 */}
                    <span style={{
                      position: 'absolute', top: 0, left: 0, width: '120px', height: '120px',
                      borderRadius: '50%', border: `2px solid ${fireworkColor}`,
                      boxShadow: `0 0 20px ${fireworkColor}, inset 0 0 15px ${fireworkColor}`,
                      animation: 'fireworkBurstRing 1.5s infinite ease-out', pointerEvents: 'none',
                    }} />
                    {/* 大輪の光環2 */}
                    <span style={{
                      position: 'absolute', top: 0, left: 0, width: '180px', height: '180px',
                      borderRadius: '50%', border: '1px dashed #ffffff',
                      animation: 'fireworkBurstRing 1.5s 0.3s infinite ease-out', pointerEvents: 'none',
                    }} />
                    
                    {/* 周りに舞う火粉 */}
                    {[...Array(6)].map((_, i) => {
                      const angle = (i * 60) * (Math.PI / 180);
                      const radius = 38;
                      return (
                        <span key={i} style={{
                          position: 'absolute',
                          left: `${Math.cos(angle) * radius}px`, top: `${Math.sin(angle) * radius}px`,
                          width: '5px', height: '5px', borderRadius: '50%',
                          backgroundColor: fireworkColor, boxShadow: `0 0 8px ${fireworkColor}, 0 0 12px #ffffff`,
                          animation: `emberFlicker ${1 + (i % 3) * 0.4}s ${(i * 0.15).toFixed(2)}s infinite alternate ease-in-out`,
                        }} />
                      );
                    })}
                  </div>
                )}

                <div
                  className="flower-core"
                  style={{
                    width: '40px',
                    height: '40px',
                    border: `${borderWidth} solid ${borderColor}`,
                    boxShadow: isSelected ? `0 0 30px ${fireworkColor}, 0 0 50px rgba(255,255,255,0.6)` : glowEffect,
                    animation: eased > 0.98 ? `float 4s ${floatDelay} ease-in-out infinite` : 'none',
                    animationDelay: floatDelay,
                  }}
                >
                  <span style={{ fontSize: isSelected ? '24px' : '16px', filter: 'drop-shadow(0 0 5px rgba(255,255,255,0.8))' }}>
                    {district.bestEmoji}
                  </span>
                </div>
                
                {showLabels && (
                  <span className="ward-label" style={{
                    marginTop: '8px',
                    fontSize: '13px',
                    fontWeight: 'bold',
                    color: '#fff',
                    textShadow: `0 0 10px ${borderColor}, 0 0 20px ${borderColor}`,
                    opacity: isSelected || rankColor ? 1 : 0.7,
                    transition: 'opacity 0.3s',
                    whiteSpace: 'nowrap',
                  }}>
                    {district.name}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* アニメーション完了後、自由にクリックして遊べるスクロール余白 */}
      <div
        style={{
          height: '6000px',
          width: '0.5cm',
          opacity: 0,
        }}
      />
    </div>
  );
});

export default Area23Map;