import { useEffect, useRef } from 'react';
import { findWardInDirection, swipeToDirection } from './wardNavigation';

// 「人間視点(=特定の区にフォーカスして見下ろしからズームした状態)」の間だけ、
// 矢印キーとスワイプで隣の区に移動できるようにするフック。
//
// スワイプは「距離」と「速度」の両方が閾値を超えた時だけ隣の区へ移動する。
// 弱いスワイプ(ちょっと指を動かしただけ/ゆっくりドラッグしただけ)は移動せず、
// onSwipeCancel経由でラバーバンド的な"跳ね返り"の見た目だけ呼び出し元に伝える。
// 移動中の見た目(ドラッグに追従する動き)が欲しい場合は onSwipeMove を使う。
//
// 使い方:
//   useWardKeyboardNav({
//     active: !!focusedDistrict,
//     currentDistrict: focusedDistrict,
//     districts,
//     onNavigate: (nextDistrict) => onSelectDistrict(nextDistrict),
//     onSwipeMove: (dx, dy) => { ... 追従アニメーション用、任意 ... },
//     onSwipeCancel: () => { ... 跳ね返りアニメーション用、任意 ... },
//   });

const KEY_TO_DIRECTION = {
  ArrowUp: 'up',
  ArrowDown: 'down',
  ArrowLeft: 'left',
  ArrowRight: 'right',
};

// この距離(px)未満は「弱いスワイプ」として無視
const MIN_SWIPE_DISTANCE = 60;
// この速度(px/ms)未満は「弱いスワイプ」として無視。
// 0.35 は「200pxをおよそ0.5秒以内で払う」くらいの目安
const MIN_SWIPE_VELOCITY = 0.35;

export function useWardKeyboardNav({
  active,
  currentDistrict,
  districts,
  onNavigate,
  onSwipeMove,
  onSwipeCancel,
}) {
  const touchState = useRef(null);

  useEffect(() => {
    if (!active) return;

    function handleKeyDown(e) {
      const direction = KEY_TO_DIRECTION[e.key];
      if (!direction) return;
      e.preventDefault();
      const next = findWardInDirection(currentDistrict, direction, districts);
      if (next) onNavigate(next);
    }

    function handleTouchStart(e) {
      const t = e.touches[0];
      touchState.current = { x: t.clientX, y: t.clientY, time: performance.now() };
    }

    function handleTouchMove(e) {
      if (!touchState.current) return;
      const t = e.touches[0];
      const dx = t.clientX - touchState.current.x;
      const dy = t.clientY - touchState.current.y;
      onSwipeMove?.(dx, dy);
    }

    function handleTouchEnd(e) {
      if (!touchState.current) return;
      const t = e.changedTouches[0];
      const dx = t.clientX - touchState.current.x;
      const dy = t.clientY - touchState.current.y;
      const dt = Math.max(performance.now() - touchState.current.time, 1);
      touchState.current = null;

      const distance = Math.hypot(dx, dy);
      const velocity = distance / dt;

      const isStrongEnough = distance >= MIN_SWIPE_DISTANCE && velocity >= MIN_SWIPE_VELOCITY;
      if (!isStrongEnough) {
        onSwipeCancel?.();
        return;
      }

      const direction = swipeToDirection(dx, dy);
      const next = direction ? findWardInDirection(currentDistrict, direction, districts) : null;
      if (next) {
        onNavigate(next);
      } else {
        // 方向は判定できたが移動先(隣の区)が無い場合も跳ね返りにする
        onSwipeCancel?.();
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('touchstart', handleTouchStart, { passive: true });
    window.addEventListener('touchmove', handleTouchMove, { passive: true });
    window.addEventListener('touchend', handleTouchEnd, { passive: true });

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('touchstart', handleTouchStart);
      window.removeEventListener('touchmove', handleTouchMove);
      window.removeEventListener('touchend', handleTouchEnd);
    };
  }, [active, currentDistrict, districts, onNavigate, onSwipeMove, onSwipeCancel]);
}