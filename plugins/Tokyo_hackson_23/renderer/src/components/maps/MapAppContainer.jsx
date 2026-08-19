// renderer/src/components/maps/MapAppContainer.jsx
import React, { useState } from 'react';
import Area23Map from '../Tokyo_s_23_wards'; // 3D星空マップ
import MapVisualizer from './MapVisualizer'; // OSM実用マップ
import { TOKYO_23_DISTRICTS } from '../../data/tokyoData'; // 区のデータ

export default function MapAppContainer() {
  // '3D' = 星空マップを表示 / 'OSM' = 実用マップを表示
  const [viewMode, setViewMode] = useState('3D');
  const [selectedDistrict, setSelectedDistrict] = useState(null);

  // ==========================================
  // 3Dマップ側で区がクリックされた時の処理
  // ==========================================
  const handleDistrictSelect = (district) => {
    setSelectedDistrict(district);

    // 🌟 演出のキモ：花火が上がるのを見せるため、1.5秒待ってからOSMへ切り替える
    setTimeout(() => {
      setViewMode('OSM');
    }, 1500); 
  };

  // ==========================================
  // OSMマップから3Dマップへ戻る時の処理
  // ==========================================
  const handleBackTo3D = () => {
    setViewMode('3D');
    setSelectedDistrict(null); // 選択状態をリセット
  };

  return (
    <div className="relative w-full h-screen overflow-hidden bg-[#02040a]">
      
      {/* ==========================================
          レイヤー1 (奥): OSM実用マップ (MapVisualizer)
      ========================================== */}
      <div 
        className="absolute inset-0 w-full h-full"
        style={{
          // viewModeが'OSM'の時だけ表示し、クリックできるようにする
          opacity: viewMode === 'OSM' ? 1 : 0,
          pointerEvents: viewMode === 'OSM' ? 'auto' : 'none',
          transition: 'opacity 1.2s ease-in-out', // 1.2秒かけてゆっくりフェードイン/アウト
          zIndex: 10
        }}
      >
        <MapVisualizer 
          // 👇 ここを修正：名前を selectedWardCode にし、districtのcodeだけを渡す
          selectedWardCode={selectedDistrict?.code} 
        />

        {/* 🌟 3Dマップに戻るためのボタン */}
        <button 
          onClick={handleBackTo3D}
          className="absolute top-6 left-6 z-[500] px-4 py-2 bg-slate-800/80 text-white rounded-full shadow-lg border border-slate-600 hover:bg-slate-700 transition-colors backdrop-blur-sm flex items-center gap-2"
          style={{ pointerEvents: viewMode === 'OSM' ? 'auto' : 'none' }}
        >
          <span>🚀</span> 宇宙（3Dマップ）に戻る
        </button>
      </div>

      {/* ==========================================
          レイヤー2 (手前): 3D直感マップ (Tokyo_s_23_wards)
      ========================================== */}
      <div 
        className="absolute inset-0 w-full h-full"
        style={{
          opacity: viewMode === '3D' ? 1 : 0,
          pointerEvents: viewMode === '3D' ? 'auto' : 'none',
          transition: 'opacity 1.2s ease-in-out', // フェードアウト
          zIndex: 20 // OSMマップより手前に配置
        }}
      >
        <Area23Map
          districts={TOKYO_23_DISTRICTS}
          selectedCode={selectedDistrict?.code}
          onSelectDistrict={handleDistrictSelect}
          // スクロール収束アニメーションの制御用。今回は空関数でOK
          onSettleChange={() => {}} 
        />
      </div>

    </div>
  );
}