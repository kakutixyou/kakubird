// frontend/src/pages/RelocationMapPage.jsx
import React, { useState, useEffect, useMemo } from 'react';

// 🌟 コンポーネントのインポート
import { DistrictDetailCard } from '@tokyo/components/DistrictDetailCard';
import Area23Map from '@tokyo/components/Tokyo_s_23_wards';
import WardEffectCanvas from '@tokyo/components/backgrounds/WardEffectCanvas';
import MapVisualizer from '@tokyo/components/maps/MapVisualizer';
import { TOKYO_23_DISTRICTS } from '@tokyo/data/tokyoData';

// 🌟 データとロジックのインポート
import {
  CATEGORIES,
  RANK_CONFIG,
  IMPLEMENTED_METRIC_KEYS,
  METRIC_KEY_TO_BACKEND_THEME,
  buildDistrictsFromApiScores,
  calculateCategoryScore,
  analyzeDistrict,
} from '@tokyo/constants/pillarMeta';
import { WardLabelsProvider, WardLabelsToggle } from '@tokyo/components/wardnav/wardLabels';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

async function fetchAllThemeScores() {
  const backendThemes = IMPLEMENTED_METRIC_KEYS
    .map((k) => METRIC_KEY_TO_BACKEND_THEME[k])
    .filter(Boolean);

  const results = await Promise.all(
    backendThemes.map((theme) =>
      fetch(`${API_BASE}/api/scores?theme=${encodeURIComponent(theme)}`)
        .then((r) => (r.ok ? r.json() : []))
        .catch(() => []) 
    )
  );

  const apiScoresByTheme = {};
  backendThemes.forEach((theme, i) => {
    apiScoresByTheme[theme] = Object.fromEntries(
      (results[i] || []).map((row) => [row.city_name, { score: row.total_score, raw_count: row.raw_count }])
    );
  });
  return apiScoresByTheme;
}

export default function RelocationMapPage() {
  const [baseDistricts, setBaseDistricts] = useState([]);
  const [isLoadingScores, setIsLoadingScores] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const [activeCategoryKey, setActiveCategoryKey] = useState(null);
  const [selectedDistrict, setSelectedDistrict] = useState(null);
  const [districtsState, setDistrictsState] = useState([]);
  const [isHeaderVisible, setIsHeaderVisible] = useState(true);

  // 🌟 マップの表示モード管理 ('3D', 'OSM_DETAIL', 'ALL_OSM')
  const [viewMode, setViewMode] = useState('3D');
  // 👇 自動ジャンプのON/OFF状態（初期値はtrue）
  const [isAutoJumpEnabled, setIsAutoJumpEnabled] = useState(true);

  // 🌟 3Dマップで区をクリックした時のハンドラー
  const handleDistrictSelect = (district) => {
    setSelectedDistrict(district);
    
    // isAutoJumpEnabled が true の時だけジャンプさせる
    if (isAutoJumpEnabled) {
      setTimeout(() => {
        setViewMode('OSM_DETAIL');
      }, 1500);
    }
  };

  // 実データ取得
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setIsLoadingScores(true);
      setLoadError(null);
      try {
        const apiScoresByTheme = await fetchAllThemeScores();
        if (cancelled) return;
        const districts = buildDistrictsFromApiScores(apiScoresByTheme);
        setBaseDistricts(districts);
        setDistrictsState(districts);
      } catch (err) {
        if (!cancelled) setLoadError(err.message || 'スコアの取得に失敗しました');
      } finally {
        if (!cancelled) setIsLoadingScores(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // スタイルの注入
  useEffect(() => {
    const styleId = 'app-custom-styles';
    if (!document.getElementById(styleId)) {
      const styleEl = document.createElement('style');
      styleEl.id = styleId;
      styleEl.innerHTML = `
        @keyframes bounce { 
          0%, 100% { transform: translateY(0); } 
          50% { transform: translateY(10px); } 
        }
        .bouncing-text {
          animation: bounce 2s infinite;
        }
        @keyframes cardSlideUp {
          from { transform: translateY(40px) scale(0.95); opacity: 0; }
          to { transform: translateY(0) scale(1); opacity: 1; }
        }
        .district-detail-card {
          animation: cardSlideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .detail-btn {
          transition: all 0.2s ease;
          cursor: pointer;
          border-radius: 10px;
          padding: 10px;
          font-weight: bold;
          font-size: 12px;
        }
        .detail-btn:hover {
          filter: brightness(1.2);
          transform: translateY(-2px);
        }
      `;
      document.head.appendChild(styleEl);
    }
  }, []);

  const handleCategorySelect = (key) => {
    if (activeCategoryKey === key) {
      setActiveCategoryKey(null);
      setDistrictsState(baseDistricts);
      setSelectedDistrict(null);
      setViewMode('3D');
      return;
    }

    setActiveCategoryKey(key);
    const category = CATEGORIES[key];

    const rankedDistricts = baseDistricts
      .map((district) => {
        const scoreInfo = calculateCategoryScore(district.scores, category.metrics, 2, key);
        return {
          ...district,
          categoryTotalScore: scoreInfo.total,
          categoryNormalizedScore: scoreInfo.normalizedScore,
          categoryRank: scoreInfo.rank,
          categoryRankMeta: scoreInfo.rankMeta,
          snapshotText: scoreInfo.snapshotText,
        };
      })
      .sort((a, b) => b.categoryNormalizedScore - a.categoryNormalizedScore);

    setDistrictsState(rankedDistricts);
    setSelectedDistrict(rankedDistricts[0]);
  };

  const analysisData = useMemo(() => {
    return analyzeDistrict(selectedDistrict, districtsState);
  }, [selectedDistrict, districtsState]);

  const activeWardBaseData = TOKYO_23_DISTRICTS.find(d => d.code === selectedDistrict?.code);
  const targetEffectKey = activeWardBaseData?.effectKey;

  return (
    // 親のレイアウト（Layoutコンポーネント）でサイドバーが表示される前提で、
    // ここではメインのマップ領域のみを返します。
    <div style={{
      flex: 1, // 親がFlexboxの場合、残りのスペースをすべて埋める
      backgroundColor: '#02040a',
      color: '#fff',
      fontFamily: 'sans-serif',
      margin: 0,
      padding: 0,
      height: '100%',
      width: '100%',
      position: 'relative',
      overflow: 'hidden'
    }}>
      <WardLabelsProvider>

        {/* 演出用Canvas（一番後ろ） */}
        <WardEffectCanvas wardCode={targetEffectKey} />

        {/* 🌟 右上メニュー: 自動ジャンプ切替 ＆ 区名ラベル表示 ＆ ALL_OSM切替ボタン */}
        <div style={{ position: 'absolute', top: '10px', right: '20px', zIndex: 600, display: 'flex', gap: '12px', alignItems: 'center' }}>
          <button
            onClick={() => setIsAutoJumpEnabled(prev => !prev)}
            style={{
              padding: '10px 16px',
              borderRadius: '30px',
              border: '1px solid rgba(255,255,255,0.2)',
              background: isAutoJumpEnabled ? 'rgba(5, 213, 231, 0.15)' : 'rgba(255,255,255,0.05)',
              color: isAutoJumpEnabled ? '#05d5e7' : '#fff',
              fontSize: '12px',
              fontWeight: 'bold',
              cursor: 'pointer',
              backdropFilter: 'blur(10px)',
            }}
          >
            {isAutoJumpEnabled ? '🚀 自動ジャンプ: ON' : '⏸️ 自動ジャンプ: OFF'}
          </button>
          
          <WardLabelsToggle />
          
          <button
            onClick={() => {
              if (viewMode === 'ALL_OSM') {
                setViewMode('3D');
              } else {
                setViewMode('ALL_OSM');
                setSelectedDistrict(null);
              }
            }}
            className="px-4 py-2 bg-slate-900 text-white font-bold rounded-lg shadow-lg border border-slate-700 hover:bg-slate-800 transition-all text-sm"
          >
            {viewMode === 'ALL_OSM' ? '🌌 3Dマップへ戻る' : '🗺️ 全体マップ(OSM)'}
          </button>
        </div>

        {isLoadingScores && (
          <div style={{
            position: 'absolute', top: '12px', left: '12px', zIndex: 500,
            color: '#888', fontSize: '12px', background: 'rgba(0,0,0,0.5)',
            padding: '6px 12px', borderRadius: '8px',
          }}>
            スコアを読み込み中...
          </div>
        )}
        {loadError && (
          <div style={{
            position: 'absolute', top: '12px', left: '12px', zIndex: 500,
            color: '#ff5e00', fontSize: '12px', background: 'rgba(0,0,0,0.7)',
            padding: '6px 12px', borderRadius: '8px',
          }}>
            読み込みエラー: {loadError}
          </div>
        )}

        {/* レイヤー1 (奥): OSM実用マップ (MapVisualizer) */}
        <div 
          style={{
            position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
            opacity: (viewMode === 'OSM_DETAIL' || viewMode === 'ALL_OSM') ? 1 : 0,
            pointerEvents: (viewMode === 'OSM_DETAIL' || viewMode === 'ALL_OSM') ? 'auto' : 'none',
            transition: 'opacity 1.2s ease-in-out',
            zIndex: 10,
            backgroundColor: '#f8fafc'
          }}
        >
          {viewMode === 'OSM_DETAIL' && (
            <button 
              onClick={() => {
                setViewMode('3D');
                setSelectedDistrict(null);
              }}
              className="absolute top-6 left-20 z-[600] px-6 py-3 bg-slate-900 text-white font-bold rounded-full shadow-2xl border border-slate-700 hover:bg-slate-800 transition-all flex items-center gap-2"
            >
              <span>🚀</span> 宇宙マップに戻る
            </button>
          )}
          
          <MapVisualizer 
            selectedWardCode={viewMode === 'ALL_OSM' ? null : selectedDistrict?.code} 
          />
        </div>

        {/* レイヤー2 (手前): 3D直感マップ (Area23Map) */}
<div
  style={{ 
    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, 
    opacity: viewMode === '3D' ? 1 : 0,
    pointerEvents: viewMode === '3D' ? 'auto' : 'none',
    transition: 'opacity 1.2s ease-in-out',
    zIndex: 20 
  }}
  onClick={() => setSelectedDistrict(null)}
>
  <Area23Map
    districts={districtsState}
    selectedCode={selectedDistrict?.code || null}
    selectedCategory={activeCategoryKey} // 👈 activeCategoryKey を渡す
    onSelectDistrict={handleDistrictSelect}
    onSettleChange={null}
  />
        </div>

        {/* 上部：カテゴリ選択 */}
        <section style={{
          position: 'absolute',
          top: 0, left: 0, right: 0,
          padding: '40px 20px 40px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          zIndex: 30,
          background: 'linear-gradient(to bottom, rgba(2,4,10,0.9) 0%, rgba(2,4,10,0.6) 60%, transparent 100%)',
          opacity: isHeaderVisible && viewMode === '3D' ? 1 : 0,
          transform: isHeaderVisible && viewMode === '3D' ? 'translateY(0)' : 'translateY(-200px)',
          visibility: isHeaderVisible && viewMode === '3D' ? 'visible' : 'hidden',
          transition: 'all 0.6s cubic-bezier(0.22, 1, 0.36, 1)',
          pointerEvents: 'none'
        }}>
          <div style={{ pointerEvents: isHeaderVisible && viewMode === '3D' ? 'auto' : 'none', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <h1 style={{ fontSize: '32px', margin: '0 0 10px 0', background: 'linear-gradient(90deg, #00ff9f, #05d5e7)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              TOKYO 23 MATCHING
            </h1>
            <p style={{ color: '#888', margin: '0 0 30px 0', fontSize: '14px', textShadow: '0 2px 4px rgba(0,0,0,0.8)' }}>
              あなたが重視するテーマを選んで、最適な区を見つけよう
            </p>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', justifyContent: 'center', maxWidth: '800px' }}>
              {Object.entries(CATEGORIES).map(([key, cat]) => (
                <button
                  key={key}
                  onClick={() => handleCategorySelect(key)}
                  style={{
                    background: activeCategoryKey === key ? 'rgba(5, 213, 231, 0.2)' : 'rgba(255,255,255,0.05)',
                    border: activeCategoryKey === key ? '1px solid #05d5e7' : '1px solid rgba(255,255,255,0.1)',
                    color: activeCategoryKey === key ? '#05d5e7' : '#fff',
                    padding: '12px 20px', borderRadius: '30px', cursor: 'pointer', fontWeight: 'bold', transition: 'all 0.3s',
                    backdropFilter: 'blur(5px)'
                  }}
                >
                  {cat.emoji} {cat.label}
                </button>
              ))}
            </div>
          </div>
        </section>
        
        {/* 左端：ランク凡例 */}
        <div style={{
          position: 'absolute', left: '20px', top: '50%', transform: 'translateY(-50%)', zIndex: 30,
          display: 'flex', flexDirection: 'column', gap: '12px', background: 'rgba(10, 14, 35, 0.7)',
          padding: '16px', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.1)',
          backdropFilter: 'blur(10px)', WebkitBackdropFilter: 'blur(10px)',
          opacity: viewMode === '3D' ? 1 : 0,
          pointerEvents: viewMode === '3D' ? 'auto' : 'none',
          transition: 'opacity 0.6s'
        }}>
          <h3 style={{ fontSize: '11px', margin: '0 0 5px 0', color: '#888', textAlign: 'center', letterSpacing: '2px' }}>RANK</h3>
          {Object.entries(RANK_CONFIG).map(([key, config]) => (
            <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '14px', height: '14px', borderRadius: '50%', backgroundColor: config.color, boxShadow: `0 0 10px ${config.color}` }}></div>
              <span style={{ fontSize: '13px', fontWeight: 'bold', color: '#eee' }}>{config.label}</span>
            </div>
          ))}
        </div>
        
        {/* 詳細カード */}
        {selectedDistrict && (
          <div style={{ position: 'absolute', bottom: '20px', right: '20px', zIndex: 1000, width: '400px' }}>
            <DistrictDetailCard
              district={selectedDistrict}
              activeCategory={activeCategoryKey ? CATEGORIES[activeCategoryKey] : null}
              analysis={analysisData}
              onJumpToComplement={(complementDistrict) => {
                setSelectedDistrict(complementDistrict);
                setViewMode('OSM_DETAIL'); 
              }}
              onGoogleSearch={(districtName, metricLabel) => {
                const query = `${districtName} ${metricLabel}`;
                window.open(`https://www.google.com/search?q=${encodeURIComponent(query)}`, '_blank');
              }}
              onClose={() => {
                setSelectedDistrict(null);
                setViewMode('3D'); 
              }}
            />
          </div>
        )}

      </WardLabelsProvider>
    </div>
  );
}