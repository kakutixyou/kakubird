// App.jsx
import React, { useState, useEffect, useMemo } from 'react';

// 🌟 コンポーネントのインポート
import { DistrictDetailCard } from './components/DistrictDetailCard';
import Area23Map from './components/Tokyo_s_23_wards';
import WardEffectCanvas from './components/backgrounds/WardEffectCanvas';
import MapVisualizer from './components/maps/MapVisualizer';
import { TOKYO_23_DISTRICTS } from './data/tokyoData';

// 🌟 データとロジックのインポート
import {
  CATEGORIES,
  RANK_CONFIG,
  IMPLEMENTED_METRIC_KEYS,
  METRIC_KEY_TO_BACKEND_THEME,
  buildDistrictsFromApiScores,
  calculateCategoryScore,
  analyzeDistrict,
} from './constants/pillarMeta';
import './App.css';
import { WardLabelsProvider, WardLabelsToggle } from './components/wardnav/wardLabels';

const API_BASE = import.meta.env.VITE_API_BASE || 'https://kakubird.onrender.com';

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

export default function App() {
  const [baseDistricts, setBaseDistricts] = useState([]);
  const [isLoadingScores, setIsLoadingScores] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const [activeCategoryKey, setActiveCategoryKey] = useState(null);
  const [selectedDistrict, setSelectedDistrict] = useState(null);
  const [isCardVisible, setIsCardVisible] = useState(false);
  const [districtsState, setDistrictsState] = useState([]);
  const [isHeaderVisible, setIsHeaderVisible] = useState(true);

  const [viewMode, setViewMode] = useState('3D');
  const [isAutoJumpEnabled, setIsAutoJumpEnabled] = useState(true);

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
        .bouncing-text { animation: bounce 2s infinite; }
        
        @keyframes cardSlideUp {
          from { transform: translateY(40px) scale(0.95); opacity: 0; }
          to { transform: translateY(0) scale(1); opacity: 1; }
        }
        .district-detail-card { animation: cardSlideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1); }

        /* 🌟 新しい DistrictDetailCard 内のスクロールバーを装飾 */
        .district-detail-card ::-webkit-scrollbar {
          width: 6px;
        }
        .district-detail-card ::-webkit-scrollbar-track {
          background: rgba(0, 0, 0, 0.2);
          border-radius: 8px;
        }
        .district-detail-card ::-webkit-scrollbar-thumb {
          background: rgba(5, 213, 231, 0.4);
          border-radius: 8px;
        }
        .district-detail-card ::-webkit-scrollbar-thumb:hover {
          background: rgba(5, 213, 231, 0.8);
        }
      `;
      document.head.appendChild(styleEl);
    }
  }, []);

  const handleDistrictSelect = (district) => {
    setSelectedDistrict(district);
    setIsCardVisible(true);
    
    if (district && isAutoJumpEnabled) {
      setTimeout(() => {
        setViewMode('OSM');
      }, 1500);
    }
  };

  const handleCategorySelect = (key) => {
    if (activeCategoryKey === key) {
      setActiveCategoryKey(null);
      setDistrictsState(baseDistricts);
      setSelectedDistrict(null);
      setIsCardVisible(false);
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
    setIsCardVisible(true);
  };

  const handleScrollToTop = () => {
    setActiveCategoryKey(null);
    setSelectedDistrict(null);
    setIsCardVisible(false);
    setDistrictsState(baseDistricts);
  };

  const analysisData = useMemo(() => {
    return analyzeDistrict(selectedDistrict, districtsState);
  }, [selectedDistrict, districtsState]);

  const activeWardBaseData = TOKYO_23_DISTRICTS.find(d => d.code === selectedDistrict?.code);
  const targetEffectKey = activeWardBaseData?.effectKey;

  return (
    <WardLabelsProvider>
      <div style={{
        backgroundColor: '#02040a', color: '#fff', fontFamily: 'sans-serif',
        margin: 0, padding: 0, height: '100vh', width: '100vw',
        position: 'relative', overflow: 'hidden'
      }}>

        <WardEffectCanvas wardCode={targetEffectKey} />

        <div style={{ position: 'fixed', top: '20px', right: '20px', zIndex: 600, display: 'flex', gap: '12px', alignItems: 'center' }}>
          <button
            onClick={() => setIsAutoJumpEnabled(!isAutoJumpEnabled)}
            style={{
              padding: '10px 16px', borderRadius: '30px', border: '1px solid rgba(255,255,255,0.2)',
              background: isAutoJumpEnabled ? 'rgba(5, 213, 231, 0.15)' : 'rgba(255,255,255,0.05)',
              color: isAutoJumpEnabled ? '#05d5e7' : '#fff', fontSize: '12px', fontWeight: 'bold',
              cursor: 'pointer', backdropFilter: 'blur(5px)',
              display: viewMode === '3D' ? 'block' : 'none'
            }}
          >
            {isAutoJumpEnabled ? '🚀 自動ジャンプ: ON' : '⏸️ 自動ジャンプ: OFF'}
          </button>
          
          <div style={{ display: viewMode === '3D' ? 'block' : 'none' }}>
            <WardLabelsToggle />
          </div>
        </div>

        {isLoadingScores && (
          <div style={{ position: 'fixed', top: '12px', left: '12px', zIndex: 200, color: '#888', fontSize: '12px', background: 'rgba(0,0,0,0.5)', padding: '6px 12px', borderRadius: '8px' }}>
            スコアを読み込み中...
          </div>
        )}
        {loadError && (
          <div style={{ position: 'fixed', top: '12px', left: '12px', zIndex: 200, color: '#ff5e00', fontSize: '12px', background: 'rgba(0,0,0,0.7)', padding: '6px 12px', borderRadius: '8px' }}>
            読み込みエラー: {loadError}
          </div>
        )}

        {/* ==========================================
            レイヤー1 (奥): OSM実用マップ (MapVisualizer)
        ========================================== */}
        <div 
          style={{
            position: 'absolute', inset: 0, zIndex: 100,
            opacity: viewMode === 'OSM' ? 1 : 0,
            pointerEvents: viewMode === 'OSM' ? 'auto' : 'none',
            transition: 'opacity 1.2s ease-in-out',
          }}
        >
          {viewMode === 'OSM' && (
            <MapVisualizer selectedWardCode={selectedDistrict?.code} />
          )}
          <button 
            onClick={() => setViewMode('3D')}
            style={{
              position: 'absolute', top: '24px', left: '24px', zIndex: 500,
              padding: '12px 24px', background: 'rgba(30, 41, 59, 0.9)', color: '#fff',
              borderRadius: '30px', border: '1px solid rgba(255,255,255,0.2)',
              boxShadow: '0 4px 6px rgba(0,0,0,0.3)', cursor: 'pointer', fontWeight: 'bold', backdropFilter: 'blur(4px)'
            }}
          >
            🚀 宇宙（3Dマップ）に戻る
          </button>
        </div>

        {/* ==========================================
            レイヤー2 (手前): 3D直感マップ 
        ========================================== */}
        <div
          style={{ 
            position: 'absolute', inset: 0, zIndex: 1,
            opacity: viewMode === '3D' ? 1 : 0,
            visibility: viewMode === '3D' ? 'visible' : 'hidden',
            transition: 'opacity 1.2s ease-in-out, visibility 0s linear ' + (viewMode === '3D' ? '0s' : '1.2s')
          }}
          onClick={() => setSelectedDistrict(null)}
        >
          <Area23Map
            districts={districtsState}
            selectedCode={selectedDistrict?.code}
            selectedCategory={activeCategoryKey} 
            onSelectDistrict={handleDistrictSelect}
            onSettleChange={(settled) => setIsHeaderVisible(!settled)}
          />
        </div>

        {viewMode === '3D' && (!isHeaderVisible || activeCategoryKey) && (
          <button
            onClick={handleScrollToTop}
            style={{
              position: 'fixed', bottom: '30px', left: '30px', zIndex: 500,
              padding: '12px 20px', borderRadius: '30px', border: '1px solid rgba(5, 213, 231, 0.4)',
              background: 'rgba(10, 14, 35, 0.85)', color: '#05d5e7', fontSize: '13px', fontWeight: 'bold',
              cursor: 'pointer', boxShadow: '0 4px 20px rgba(5, 213, 231, 0.3)', backdropFilter: 'blur(8px)',
              display: 'flex', alignItems: 'center', gap: '8px', transition: 'all 0.2s ease',
            }}
          >
            <span style={{ fontSize: '16px' }}>⬆️</span> トップへ戻る
          </button>
        )}

        <section style={{
          position: 'fixed', top: 0, left: 0, right: 0, padding: '40px 20px 40px', display: 'flex', flexDirection: 'column', alignItems: 'center', zIndex: 10,
          background: 'linear-gradient(to bottom, rgba(2,4,10,0.9) 0%, rgba(2,4,10,0.6) 60%, transparent 100%)',
          opacity: (isHeaderVisible && viewMode === '3D') ? 1 : 0,
          transform: (isHeaderVisible && viewMode === '3D') ? 'translateY(0)' : 'translateY(-20px)',
          visibility: (isHeaderVisible && viewMode === '3D') ? 'visible' : 'hidden',
          transition: 'all 0.6s cubic-bezier(0.22, 1, 0.36, 1)', pointerEvents: 'none'
        }}>
          <div style={{ pointerEvents: (isHeaderVisible && viewMode === '3D') ? 'auto' : 'none', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <h1 style={{ fontSize: '32px', margin: '0 0 10px 0', background: 'linear-gradient(90deg, #00ff9f, #05d5e7)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              TOKYO 23 MATCHING
            </h1>
            <p style={{ color: '#888', margin: '0 0 30px 0', fontSize: '14px', textShadow: '0 2px 4px rgba(0,0,0,0.8)' }}>
              あなたが重視するテーマを選んで、最適な区を見つけよう
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', justifyContent: 'center', maxWidth: '800px' }}>
              {Object.entries(CATEGORIES).map(([key, cat]) => (
                <button
                  key={key} onClick={() => handleCategorySelect(key)}
                  style={{
                    background: activeCategoryKey === key ? 'rgba(5, 213, 231, 0.2)' : 'rgba(255,255,255,0.05)',
                    border: activeCategoryKey === key ? '1px solid #05d5e7' : '1px solid rgba(255,255,255,0.1)',
                    color: activeCategoryKey === key ? '#05d5e7' : '#fff',
                    padding: '12px 20px', borderRadius: '30px', cursor: 'pointer', fontWeight: 'bold', transition: 'all 0.3s', backdropFilter: 'blur(5px)'
                  }}
                >
                  {cat.emoji} {cat.label}
                </button>
              ))}
            </div>
          </div>
        </section>
        
        <div style={{
          position: 'fixed', left: '20px', top: '50%', transform: 'translateY(-50%)', zIndex: 50, display: 'flex', flexDirection: 'column', gap: '12px', background: 'rgba(10, 14, 35, 0.7)',
          padding: '16px', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.1)', backdropFilter: 'blur(10px)', WebkitBackdropFilter: 'blur(10px)',
          opacity: viewMode === '3D' ? 1 : 0, pointerEvents: viewMode === '3D' ? 'auto' : 'none', transition: 'opacity 0.5s'
        }}>
          <h3 style={{ fontSize: '11px', margin: '0 0 5px 0', color: '#888', textAlign: 'center', letterSpacing: '2px' }}>RANK</h3>
          {Object.entries(RANK_CONFIG).map(([key, config]) => (
            <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '14px', height: '14px', borderRadius: '50%', backgroundColor: config.color, boxShadow: `0 0 10px ${config.color}` }}></div>
              <span style={{ fontSize: '13px', fontWeight: 'bold', color: '#eee' }}>{config.label}</span>
            </div>
          ))}
        </div>
        
        {/* 🌟 DistrictDetailCardの呼び出し部分 */}
        {/* カード側で position: 'fixed' を持つため、無駄なラッパーdivを削除しました */}
{/* App.jsx の一番下にある呼び出し部分 */}
        {selectedDistrict && isCardVisible && (
          <DistrictDetailCard
            district={selectedDistrict}
            activeCategory={activeCategoryKey ? CATEGORIES[activeCategoryKey] : null}
            analysis={analysisData}
            onJumpToComplement={(complementDistrict) => handleDistrictSelect(complementDistrict)}
            onGoogleSearch={(districtName, metricLabel) => {
              const query = `${districtName} ${metricLabel}`;
              window.open(`https://www.google.com/search?q=${encodeURIComponent(query)}`, '_blank');
            }}
            viewMode={viewMode}
onClose={(mode) => {
  setIsCardVisible(false);
  setSelectedDistrict(null);
  if (mode) setViewMode(mode); // '3D' または 'OSM' が渡された場合のみ切り替え
}}
          />
        )}

      </div>
    </WardLabelsProvider>
  );
}