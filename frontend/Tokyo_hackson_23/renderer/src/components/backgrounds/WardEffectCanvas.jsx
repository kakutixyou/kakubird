// WardEffectCanvas.jsx
import React, { useEffect, useRef, useState } from 'react';

// Vite専用: events/wards内のjsファイルをすべて事前に認識させておく
const effectModules = import.meta.glob('../../../events/wards/*.js');

function EffectLayer({ wardCode, isActive, onFadeOutComplete }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !wardCode) return;
    let stopEffect = () => {};
    let isMounted = true;

    const loadEffect = async () => {
      try {
        const path = `../../../events/wards/${wardCode}.js`;
        // ファイルが存在するかチェックしてから読み込む
        if (effectModules[path]) {
          const effectModule = await effectModules[path]();
          if (isMounted && canvasRef.current) {
            stopEffect = effectModule.run(canvasRef.current);
          }
        } else {
          console.warn(`[WardEffect] 演出ファイルが見つかりません: ${path}`);
        }
      } catch (err) {
        console.error(`[WardEffect] 読み込みエラー:`, err);
      }
    };
    loadEffect();

    return () => {
      isMounted = false;
      if (typeof stopEffect === 'function') stopEffect();
    };
  }, [wardCode]);

  useEffect(() => {
    if (!isActive) {
      const timer = setTimeout(() => {
        onFadeOutComplete();
      }, 1000); // 1秒かけてフェードアウト
      return () => clearTimeout(timer);
    }
  }, [isActive, onFadeOutComplete]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        display: 'block',
        opacity: isActive ? 1 : 0,
        transition: 'opacity 1s ease-in-out',
        zIndex: isActive ? 1 : 0,
      }}
    />
  );
}

export default function WardEffectCanvas({ wardCode }) {
  const [current, setCurrent] = useState(wardCode);
  const [previous, setPrevious] = useState(null);

  useEffect(() => {
    if (wardCode !== current) {
      setPrevious(current);
      setCurrent(wardCode);
    }
  }, [wardCode, current]);

  if (!current && !previous) return null;

  return (
// WardEffectCanvas.jsx の一番下

    <div style={{
      position: 'absolute',
      inset: 0,
      pointerEvents: 'none',
      zIndex: 5, // Area23Map (zIndex:1) より手前に配置
      
      // ❌ 下の1行を削除（または // でコメントアウト）してください！
      // mixBlendMode: 'screen', 
    }}>
      {previous && (
        <EffectLayer
          key={`prev-${previous}`}
          wardCode={previous}
          isActive={false}
          onFadeOutComplete={() => setPrevious(null)}
        />
      )}
      {current && (
        <EffectLayer
          key={`curr-${current}`}
          wardCode={current}
          isActive={true}
          onFadeOutComplete={() => {}}
        />
      )}
    </div>
  
  );
}