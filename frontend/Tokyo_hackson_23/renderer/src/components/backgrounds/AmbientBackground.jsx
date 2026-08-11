import React, { useEffect, useRef } from 'react';
import { getEffect } from './ambientAnimations';
import { resolveEffectKeyByValue } from './backgroundRules';

/**
 * 条件に応じて演出（背景）を差し替えるコンポーネント。
 *
 * 使い方1: キーを直接指定
 *   <AmbientBackground effectKey="chuo" />
 *
 * 使い方2: 0〜100の数値から自動解決（93〜100なら katsushika、など）
 *   <AmbientBackground value={clickedNumber} />
 *
 * 演出は2種類あり、このコンポーネントが自動で出し分ける：
 *   - canvas型     : requestAnimationFrameで描き続けるアニメーション（星空・桜吹雪など）
 *   - component型  : ShibamataTownのようなJSX/Tailwindで組み上がる演出
 */
export default function AmbientBackground({ effectKey, value, className, style }) {
  const canvasRef = useRef(null);

  const resolvedKey = effectKey ?? resolveEffectKeyByValue(value ?? -1);
  const effect = getEffect(resolvedKey);

  useEffect(() => {
    if (effect.type !== 'canvas') return undefined;
    const canvas = canvasRef.current;
    if (!canvas) return undefined;

    const stop = effect.run(canvas);
    // resolvedKeyが変わったとき／アンマウント時は前の演出を必ず止める
    return () => {
      if (typeof stop === 'function') stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resolvedKey]);

  if (effect.type === 'component') {
    const Component = effect.Component;
    return <Component />;
  }

  return (
    <canvas
      ref={canvasRef}
      className={className}
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        display: 'block',
        ...style,
      }}
    />
  );
}