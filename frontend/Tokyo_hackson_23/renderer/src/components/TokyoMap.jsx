import React from 'react';

export default function TokyoMap({ districts, selectedCode, onSelectDistrict }) {
  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', maxWidth: '800px', margin: '0 auto' }}>
      {districts.map((district) => {
        const isSelected = selectedCode === district.code;
        const color = district.categoryRankMeta?.color || '#05d5e7';
        
        return (
          <div
            key={district.code}
            onClick={() => onSelectDistrict(district)}
            style={{
              position: 'absolute',
              left: `${district.x}%`,
              top: `${district.y}%`,
              transform: 'translate(-50%, -50%)', // 中心を合わせる
              cursor: 'pointer',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              transition: 'all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
              zIndex: isSelected ? 10 : 1,
              scale: isSelected ? '1.3' : '1',
            }}
          >
            {/* ピンのアニメーション部分 */}
            <div style={{
              width: isSelected ? '50px' : '36px',
              height: isSelected ? '50px' : '36px',
              backgroundColor: 'rgba(10, 14, 35, 0.8)',
              border: `2px solid ${color}`,
              borderRadius: '50%',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              fontSize: isSelected ? '24px' : '16px',
              boxShadow: `0 0 15px ${color}80`,
            }}>
              {district.bestEmoji}
            </div>
            
            <span style={{
              marginTop: '4px',
              fontSize: '12px',
              fontWeight: 'bold',
              color: isSelected ? '#fff' : 'rgba(255,255,255,0.7)',
              textShadow: '0 2px 4px rgba(0,0,0,0.8)'
            }}>
              {district.name}
            </span>
          </div>
        );
      })}
    </div>
  );
}