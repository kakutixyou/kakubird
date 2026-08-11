import React, { createContext, useContext, useState } from 'react';

// 区名ラベルの表示/非表示だけを管理する小さなContext。
// Tokyo_s_23_wards.jsx側は useWardLabels() で読むだけでよく、
// app.jsxは <WardLabelsProvider> で全体を包んで <WardLabelsToggle /> を
// 好きな場所に置くだけでいい。状態のロジックは全部このファイルに閉じる。

const WardLabelsContext = createContext({ showLabels: true, toggle: () => {} });

export function WardLabelsProvider({ children, defaultVisible = true }) {
  const [showLabels, setShowLabels] = useState(defaultVisible);
  const toggle = () => setShowLabels((v) => !v);
  return (
    <WardLabelsContext.Provider value={{ showLabels, toggle }}>
      {children}
    </WardLabelsContext.Provider>
  );
}

export function useWardLabels() {
  return useContext(WardLabelsContext);
}

export function WardLabelsToggle({ style }) {
  const { showLabels, toggle } = useWardLabels();
  return (
    <button
      onClick={toggle}
      style={{
        position: 'fixed',
        right: '700px',
        top: '10px',
        zIndex: 60,
        padding: '10px 16px',
        borderRadius: '30px',
        border: '1px solid rgba(255,255,255,0.2)',
        background: showLabels ? 'rgba(5, 213, 231, 0.15)' : 'rgba(255,255,255,0.05)',
        color: showLabels ? '#05d5e7' : '#fff',
        fontSize: '12px',
        fontWeight: 'bold',
        cursor: 'pointer',
        backdropFilter: 'blur(5px)',
        ...style,
      }}
    >
      {showLabels ? '区名を非表示' : '区名を表示'}
    </button>
  );
}