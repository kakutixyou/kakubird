// frontend/src/components/maps/MapVisualizer.jsx
import React, { useState, useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Circle, Marker, Popup, Polyline, useMapEvents, useMap } from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

import { TOKYO_23_DISTRICTS } from '../../data/tokyoData'; 
import { useMapScoring } from '../../hooks/useMapScoring';
import { calculateDistanceMeters, getDistanceScore } from '../../utils/distanceUtils';

// --- Leafletアイコン設定 ---
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';
let DefaultIcon = L.icon({ iconUrl: icon, shadowUrl: iconShadow, iconAnchor: [12, 41], popupAnchor: [1, -34] });
L.Marker.prototype.options.icon = DefaultIcon;

const workplaceIcon = L.divIcon({
  html: '<div style="font-size:28px; filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.3));">🏢</div>',
  className: 'custom-workplace-icon', iconSize: [30, 30], iconAnchor: [15, 15],
});

function MapFlyToController({ center }) {
  const map = useMap();
  useEffect(() => {
    if (center) map.flyTo(center, 14, { duration: 1.5, easeLinearity: 0.25 });
  }, [center, map]);
  return null;
}

// 🌟 新規追加: 地図イベントを処理するコンポーネント
function MapEventsHandler({ onMapClick, onCenterChange }) {
  useMapEvents({
    click: (e) => onMapClick([e.latlng.lat, e.latlng.lng]),
    moveend: (e) => onCenterChange([e.target.getCenter().lat, e.target.getCenter().lng])
  });
  return null;
}

const INITIAL_CENTER = [35.6896, 139.7006];

export default function MapVisualizer({ selectedWardCode }) {
  const [candidatePins, setCandidatePins] = useState([]);
  const [currentMapCenter, setCurrentMapCenter] = useState(INITIAL_CENTER);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  
  const {
    center,
    isEvaluating,
    categories,
    score,
    toggleCategory,
    handleMapClick,
    poiList,
    workplace,
    handleSetWorkplace,
    apiError // 🌟 エラー状態をフックから受け取る
  } = useMapScoring(INITIAL_CENTER);

// 修正後
  useEffect(() => {
    if (selectedWardCode) {
      const district = TOKYO_23_DISTRICTS.find(d => d.code === selectedWardCode);
      if (district && district.lat && district.lng) {
        handleMapClick([district.lat, district.lng]);
      }
    }
    // 👇 警告が出ても無視するコメントを追加し、selectedWardCode だけにする
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedWardCode]);
  const visiblePois = useMemo(() => {
    return poiList.filter((poi) => {
      const catDef = categories.find((c) => c.id === poi.category);
      return catDef && catDef.enabled;
    });
  }, [poiList, categories]);

  const handleSearchWorkplace = async () => {
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    try {
      const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}&countrycodes=jp&limit=1`;
      const res = await fetch(url);
      const data = await res.json();
      
      if (data && data.length > 0) {
        const lat = parseFloat(data[0].lat);
        const lon = parseFloat(data[0].lon);
        handleSetWorkplace([lat, lon]); // 🌟 フックの関数を使って職場を登録
        setSearchQuery('');
        alert(`🏢 職場を設定しました！\n（${data[0].display_name.split(',')[0]}）`);
      } else {
        alert('場所が見つかりませんでした。\n※マイナーな施設名はヒットしにくいため、住所での検索をおすすめします。');
      }
    } catch (err) {
      console.error(err);
      alert('検索中にエラーが発生しました。');
    } finally {
      setIsSearching(false);
    }
  };

  const handleAddPin = () => {
    if (candidatePins.length >= 10) return;
    const newPin = { id: Date.now(), lat: currentMapCenter[0], lng: currentMapCenter[1] };
    setCandidatePins([...candidatePins, newPin]);
    handleMapClick(currentMapCenter);
  };

  const handleRemovePin = (id) => {
    setCandidatePins(prev => prev.filter(pin => pin.id !== id));
  };

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', backgroundColor: '#f8fafc', overflow: 'hidden' }}>
      
      {/* 🌟 新規追加：通信エラー時の警告バナー */}
      {apiError && (
        <div style={{
          position: 'absolute', top: '24px', left: '50%', transform: 'translateX(-50%)',
          backgroundColor: '#fee2e2', color: '#b91c1c', border: '1px solid #f87171',
          padding: '12px 24px', borderRadius: '8px', zIndex: 1000,
          boxShadow: '0 4px 6px rgba(0,0,0,0.1)', display: 'flex', alignItems: 'center', gap: '12px',
          fontWeight: 'bold', fontSize: '14px'
        }}>
          <span style={{ fontSize: '20px' }}>⚠️</span>
          <div>
            <div>通信エラー: 施設データを取得できませんでした。</div>
            <div style={{ fontSize: '12px', fontWeight: 'normal', marginTop: '2px' }}>
              ※ 前回の評価結果を維持して表示しています。時間をおいて再試行してください。
            </div>
          </div>
        </div>
      )}

      {/* 画面中央のターゲットマーカー（照準） */}
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, pointerEvents: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 400 }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', position: 'relative' }}>
          <div style={{ position: 'relative', filter: 'drop-shadow(0 4px 6px rgba(0,0,0,0.3))' }}>
            <div style={{ position: 'absolute', width: '32px', height: '32px', border: '2px solid #3b82f6', borderRadius: '50%', transform: 'translate(-50%, -50%)', backgroundColor: 'rgba(59,130,246,0.15)', backdropFilter: 'blur(2px)' }}></div>
            <div style={{ position: 'absolute', width: '2px', height: '12px', backgroundColor: '#2563eb', transform: 'translate(-50%, -50%)', top: '-12px' }}></div>
            <div style={{ position: 'absolute', width: '2px', height: '12px', backgroundColor: '#2563eb', transform: 'translate(-50%, -50%)', top: '12px' }}></div>
            <div style={{ position: 'absolute', width: '12px', height: '2px', backgroundColor: '#2563eb', transform: 'translate(-50%, -50%)', left: '-12px' }}></div>
            <div style={{ position: 'absolute', width: '12px', height: '2px', backgroundColor: '#2563eb', transform: 'translate(-50%, -50%)', left: '12px' }}></div>
            <div style={{ position: 'absolute', width: '6px', height: '6px', backgroundColor: '#2563eb', borderRadius: '50%', transform: 'translate(-50%, -50%)' }}></div>
          </div>
          <div style={{ marginTop: '32px', padding: '6px 12px', backgroundColor: 'rgba(255,255,255,0.95)', color: '#1e40af', fontSize: '12px', fontWeight: 'bold', borderRadius: '9999px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', border: '1px solid #dbeafe' }}>
            マップを動かして位置を合わせる
          </div>
        </div>
      </div>

      {/* 右上のスコア＆評価基準（チェックリスト）パネル */}
      <div style={{ position: 'absolute', top: '24px', right: '24px', zIndex: 400, width: '280px', display: 'flex', flexDirection: 'column', gap: '16px', pointerEvents: 'none' }}>
        <div style={{ backgroundColor: 'rgba(255,255,255,0.95)', backdropFilter: 'blur(12px)', padding: '16px', borderRadius: '12px', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)', border: '1px solid #e2e8f0', pointerEvents: 'auto' }}>
          
          <div style={{ textAlign: 'center', marginBottom: '16px', paddingBottom: '16px', borderBottom: '1px dashed #cbd5e1' }}>
            <h3 style={{ fontSize: '12px', fontWeight: 'bold', color: '#64748b', margin: '0 0 8px 0' }}>🌟 総合周辺環境スコア</h3>
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'center', gap: '4px' }}>
              <span style={{ fontSize: '36px', fontWeight: '900', color: isEvaluating ? '#94a3b8' : '#2563eb' }}>
                {isEvaluating ? '...' : score}
              </span>
              <span style={{ fontSize: '14px', color: '#64748b', fontWeight: 'bold' }}>/ 100点</span>
            </div>
          </div>

          <h3 style={{ fontSize: '12px', fontWeight: 'bold', color: '#64748b', margin: '0 0 12px 0' }}>✅ 評価基準（ON/OFF）</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {categories.map(cat => (
              <button
                key={cat.id}
                onClick={() => toggleCategory(cat.id)}
                disabled={isEvaluating}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%',
                  padding: '10px 12px', backgroundColor: cat.enabled ? '#eff6ff' : '#f8fafc',
                  border: `1px solid ${cat.enabled ? '#bfdbfe' : '#e2e8f0'}`, borderRadius: '8px',
                  cursor: isEvaluating ? 'not-allowed' : 'pointer', transition: 'all 0.2s', opacity: isEvaluating ? 0.5 : 1
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '16px', filter: cat.enabled ? 'none' : 'grayscale(100%) opacity(50%)' }}>{cat.icon}</span>
                  <span style={{ fontSize: '13px', fontWeight: 'bold', color: cat.enabled ? '#1e40af' : '#94a3b8' }}>{cat.name}</span>
                </div>
                
                <div style={{
                  width: '36px', height: '20px', backgroundColor: cat.enabled ? '#3b82f6' : '#cbd5e1',
                  borderRadius: '9999px', position: 'relative', transition: 'background-color 0.2s'
                }}>
                  <div style={{
                    position: 'absolute', top: '2px', left: cat.enabled ? '18px' : '2px',
                    width: '16px', height: '16px', backgroundColor: 'white', borderRadius: '50%',
                    transition: 'left 0.2s', boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
                  }} />
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 左下の検索＆ピン打ち操作パネル */}
      <div style={{ position: 'absolute', bottom: '24px', left: '24px', zIndex: 400, width: '320px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        
        <div style={{ backgroundColor: 'rgba(255,255,255,0.95)', backdropFilter: 'blur(12px)', padding: '16px', borderRadius: '12px', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)', border: '1px solid #e2e8f0', pointerEvents: 'auto' }}>
          <h3 style={{ fontSize: '14px', fontWeight: 'bold', color: '#1e293b', margin: '0 0 12px 0', display: 'flex', alignItems: 'center', gap: '6px' }}>
            🏢 職場の住所を登録
          </h3>
          <div style={{ display: 'flex', gap: '8px' }}>
            <input 
              type="text" 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="例: 東京都港区六本木6-10-1" 
              style={{ flex: 1, padding: '8px 12px', fontSize: '14px', backgroundColor: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '8px', outline: 'none', color: '#1e293b' }}
              onKeyDown={(e) => e.key === 'Enter' && handleSearchWorkplace()}
            />
            <button 
              onClick={handleSearchWorkplace}
              disabled={isSearching || !searchQuery.trim()}
              style={{ padding: '8px 16px', backgroundColor: '#2563eb', color: 'white', fontSize: '14px', fontWeight: 'bold', borderRadius: '8px', border: 'none', cursor: (isSearching || !searchQuery.trim()) ? 'not-allowed' : 'pointer', opacity: (isSearching || !searchQuery.trim()) ? 0.5 : 1, whiteSpace: 'nowrap' }}
            >
              {isSearching ? '検索中' : '登録'}
            </button>
          </div>
          <p style={{ fontSize: '10px', color: '#64748b', margin: '8px 0 0 0' }}>※施設名が出ない場合は住所を入力してください</p>
        </div>

        <div style={{ backgroundColor: 'rgba(255,255,255,0.95)', backdropFilter: 'blur(12px)', padding: '16px', borderRadius: '12px', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)', border: '1px solid #e2e8f0', pointerEvents: 'auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '12px' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 'bold', color: '#1e293b', margin: 0, display: 'flex', alignItems: 'center', gap: '6px' }}>
              📍 検討地点をピン留め
            </h3>
            <span style={{ fontSize: '12px', fontWeight: 'bold', padding: '2px 8px', borderRadius: '9999px', backgroundColor: candidatePins.length >= 10 ? '#fee2e2' : '#f1f5f9', color: candidatePins.length >= 10 ? '#dc2626' : '#475569' }}>
              {candidatePins.length}/10本
            </span>
          </div>
          
          <button 
            onClick={handleAddPin}
            disabled={candidatePins.length >= 10 || isEvaluating}
            style={{ width: '100%', padding: '12px', backgroundColor: '#1e293b', color: 'white', fontSize: '14px', fontWeight: 'bold', borderRadius: '12px', border: 'none', cursor: (candidatePins.length >= 10 || isEvaluating) ? 'not-allowed' : 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)', opacity: (candidatePins.length >= 10 || isEvaluating) ? 0.5 : 1 }}
          >
            <div style={{ width: '20px', height: '20px', borderRadius: '50%', border: '2px solid rgba(255,255,255,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px', paddingBottom: '1px' }}>+</div>
            ここを候補地に追加する
          </button>
        </div>
      </div>

      {/* ==========================================
          Leaflet マップ本体
      ========================================== */}
      <MapContainer center={center} zoom={14} zoomControl={false} style={{ width: '100%', height: '100%', zIndex: 0 }}>
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        />

        <MapFlyToController center={center} />
        <MapEventsHandler onMapClick={handleMapClick} onCenterChange={setCurrentMapCenter} />
        
        <Circle center={center} radius={isEvaluating ? 400 : 1000} pathOptions={{ color: '#3b82f6', fillOpacity: 0.08 }} />
        <Marker position={center}><Popup>📍 現在の評価地点</Popup></Marker>

        {workplace && (
          <>
            <Marker position={workplace} icon={workplaceIcon}><Popup>🏢 設定された職場</Popup></Marker>
            <Polyline positions={[center, workplace]} pathOptions={{ color: '#6366f1', weight: 3, dashArray: '6, 6' }} />
          </>
        )}

        {candidatePins.map((pin, i) => {
          let scoreUI = null;
          
          if (workplace) {
            const distance = calculateDistanceMeters([pin.lat, pin.lng], workplace);
            // 職場への距離は、スコアリングと同様に「電車・バス通勤」を想定したスピード（400m/分）で表示
            const commuteMinutes = Math.ceil(distance / 400); 
            const pinScore = getDistanceScore(commuteMinutes);
            const scoreColor = pinScore >= 80 ? '#10b981' : pinScore >= 50 ? '#f59e0b' : '#ef4444';

            scoreUI = (
              <div style={{ margin: '12px 0', padding: '8px', backgroundColor: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>🏢 職場へのアクセス</div>
                <div style={{ fontSize: '13px', fontWeight: 'bold', color: '#0f172a' }}>
                  🚃 通勤目安 約 {commuteMinutes} 分 <span style={{ fontSize: '10px', color: '#94a3b8' }}>({Math.round(distance / 1000 * 10) / 10}km)</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px', marginTop: '6px' }}>
                  <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 'bold' }}>評価:</span>
                  <span style={{ fontSize: '18px', fontWeight: '900', color: scoreColor }}>{pinScore}</span>
                  <span style={{ fontSize: '10px', color: '#94a3b8' }}>/ 100点</span>
                </div>
              </div>
            );
          }

          return (
            <Marker 
              key={pin.id} 
              position={[pin.lat, pin.lng]}
              eventHandlers={{ click: () => handleMapClick([pin.lat, pin.lng]) }}
            >
              <Popup>
                <div style={{ textAlign: 'center', minWidth: '140px' }}>
                  <div style={{ fontWeight: 'bold', fontSize: '14px', color: '#1e293b', marginBottom: '4px' }}>候補地 {i + 1}</div>
                  
                  {scoreUI || (
                    <div style={{ fontSize: '11px', color: '#64748b', margin: '8px 0' }}>
                      ※職場を登録すると<br/>アクセススコアが表示されます
                    </div>
                  )}

                  <button 
                    onClick={() => handleRemovePin(pin.id)}
                    style={{ marginTop: '8px', padding: '6px 12px', width: '100%', backgroundColor: '#fef2f2', color: '#dc2626', border: '1px solid #fecaca', borderRadius: '6px', fontSize: '12px', fontWeight: 'bold', cursor: 'pointer' }}
                  >
                    削除する
                  </button>
                </div>
              </Popup>
            </Marker>
          );
        })}

        <MarkerClusterGroup chunkedLoading={true} maxClusterRadius={40}>
          {visiblePois.map((poi) => (
            <Marker key={poi.id} position={[poi.lat, poi.lng]}>
              <Popup>{poi.name}</Popup>
            </Marker>
          ))}
        </MarkerClusterGroup>
      </MapContainer>
    </div>
  );
}