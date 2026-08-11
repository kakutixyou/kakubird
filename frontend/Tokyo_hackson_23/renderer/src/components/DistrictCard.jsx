import React from 'react';

export default function DistrictCard({ district, activeCategory, onClose }) {
  if (!district) return null;

  return (
    <div style={{
      position: 'fixed', bottom: '24px', right: '24px', width: 'calc(100% - 48px)', maxWidth: '400px',
      backgroundColor: 'rgba(10, 14, 35, 0.85)', backdropFilter: 'blur(16px)',
      borderRadius: '24px', border: `1px solid ${district.categoryRankMeta?.color || '#ffd700'}`,
      boxShadow: '0 20px 50px rgba(0, 0, 0, 0.8)', color: '#ffffff', padding: '24px', zIndex: 100,
      animation: 'cardSlideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1)'
    }}>
      <button onClick={onClose} style={{ position: 'absolute', top: '16px', right: '16px', background: 'transparent', border: 'none', color: '#fff', fontSize: '18px', cursor: 'pointer' }}>✕</button>
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '14px' }}>
        <span style={{ fontSize: '38px' }}>{district.bestEmoji}</span>
        <div>
          <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 'bold' }}>{district.name}</h2>
          <span style={{ fontSize: '12px', color: district.categoryRankMeta?.color }}>
            {district.categoryRankMeta?.label} (スコア: {district.categoryNormalizedScore})
          </span>
        </div>
      </div>
      
      {/* その他の詳細情報やシェアボタンなどをここに配置 */}
    </div>
  );
}