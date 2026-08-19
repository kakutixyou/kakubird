// DistrictDetailCard.jsx
import React, { useState } from 'react';
import { getGoogleSearchUrl, getGoogleMapsUrl, getMetricMeta } from '../constants/pillarMeta';
import {
  getTwitterShareUrl,
  getLineShareUrl,
  copyToClipboard,
  shareNative,
} from '../utils/shareUtils';
import './DistrictDetailCard.css'
// import { WARD_ART_META } from '../data/wardArtMeta';
import { TOKYO_23_DISTRICTS } from '../data/tokyoData';

export function DistrictDetailCard({
  district,
  activeCategory,
  analysis,
  onJumpToComplement,
  onGoogleSearch,
  onClose,
  viewMode = '3D',
}) {
  if (!district) return null;

  const [expandedKey, setExpandedKey] = useState(null);
  const toggleExpand = (key) => setExpandedKey(expandedKey === key ? null : key);
  const [copied, setCopied] = useState(false);
  const [detail, setDetail] = useState(null);
  const [openKey, setOpenKey] = useState(null);
  // const [isArtMetaExpanded, setIsArtMetaExpanded] = useState(false);

  // 🌟 追加：0点またはデータが無い場合に '-' を返すフォーマット関数
  const formatScore = (value) => {
    if (value === 0 || value === '0' || value === null || value === undefined) {
      return '-';
    }
    return value;
  };

  async function handlePillarClick(metricKey, backendTheme, wardName) {
    if (!backendTheme) return;
    setOpenKey(metricKey);
    const res = await fetch(
      `${import.meta.env.VITE_API_BASE || 'http://localhost:8000'}/api/wards/${encodeURIComponent(wardName)}?theme=${encodeURIComponent(backendTheme)}`
    );
    const data = await res.json();
    setDetail(data);
  }

  const handleGoogleSearch = (e) => {
    e.stopPropagation();
    const metricKey = activeCategory?.key || 'park';
    if (onGoogleSearch) {
      const meta = getMetricMeta(metricKey);
      onGoogleSearch(district.name, meta.label);
      return;
    }
    const url = getGoogleSearchUrl(district.name, metricKey);
    window.open(url, '_blank');
  };

  const handleJumpToComplement = (e) => {
    e.stopPropagation();
    if (analysis?.complement && onJumpToComplement) {
      onJumpToComplement(analysis.complement);
    }
  };

  const handleGoogleMaps = (e) => {
    e.stopPropagation();
    const metricKey = activeCategory?.key || 'park';
    const url = getGoogleMapsUrl(district.name, metricKey);
    window.open(url, '_blank');
  };

  const handleShareX = (e) => {
    e.stopPropagation();
    const url = getTwitterShareUrl(district, activeCategory);
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const handleShareLine = (e) => {
    e.stopPropagation();
    const url = getLineShareUrl(district, activeCategory);
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const handleCopyLink = async (e) => {
    e.stopPropagation();
    const sharedNatively = await shareNative(district, activeCategory);
    if (sharedNatively) return;

    const success = await copyToClipboard(district, activeCategory);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2200);
    }
  };

  const getScoreColor = (score) => {
    if (score === null || score === undefined || score === 0 || score === '0') return '#7f8c8d'; // 0点や無い場合はグレーに
    if (score >= 25) return '#00ff9f';
    if (score >= 4) return '#ffd700';
    if (score >= 1) return '#05d5e7';
    return '#ff5e00';
  };

  const baseData = TOKYO_23_DISTRICTS.find(d => d.code === district.code);
  const safeEffectKey = district.effectKey || baseData?.effectKey;
  
  // 🌟 メインスコアの算出とフォーマット
  const rawMainScore = district.categoryNormalizedScore
    ?? (activeCategory && district.scores ? district.scores[activeCategory.key] : undefined)
    ?? district.categoryTotalScore;
    
  const formattedMainScore = rawMainScore !== undefined && rawMainScore !== null 
    ? formatScore(rawMainScore) 
    : 'データ準備中';

  const isOSM = viewMode === 'OSM';

  // 常に表示されるように位置を調整
  const cardStyle = isOSM
    ? {
        position: 'fixed',
        top: '80px',
        right: '24px',
        bottom: '24px',
        width: '360px',
        maxWidth: '85vw',
        borderRadius: '24px',
      }
    : {
        position: 'fixed',
        bottom: '24px',
        right: '30px',
        width: 'calc(100% - 48px)',
        maxWidth: '360px',
        maxHeight: '85vh',
        borderRadius: '24px',
      };

  return (
    <div
      className="district-detail-card"
      style={{
        ...cardStyle,
        backgroundColor: 'rgba(10, 14, 35, 0.90)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        border: '1px solid rgba(255, 215, 0, 0.35)',
        boxShadow: '0 20px 50px rgba(0, 0, 0, 0.8), 0 0 30px rgba(255, 215, 0, 0.15)',
        color: '#ffffff',
        padding: 0,
        boxSizing: 'border-box',
        zIndex: 600,
        overflow: 'hidden',
        fontFamily: "'Hiragino Kaku Gothic ProN', 'メイリオ', sans-serif",
      }}
    >
      {/* 中身のラッパー（スライド等のtransformを削除し、純粋なスクロールコンテナに） */}
      <div
        style={{
          position: 'relative',
          height: '100%',
          padding: '24px',
          boxSizing: 'border-box',
          overflowY: 'auto',
        }}
      >
        {/* 閉じるボタン */}
        <div style={{ position: 'absolute', top: '16px', right: '16px', zIndex: 700 }}>
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (onClose) onClose();
            }}
            style={{
              background: 'rgba(255, 255, 255, 0.1)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              color: '#aaaaaa',
              fontSize: '16px',
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            ✕
          </button>
        </div>

        {/* ヘッダーエリア */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '14px' }}>
          <span style={{ fontSize: '38px', filter: 'drop-shadow(0 0 10px rgba(255, 215, 0, 0.5))' }}>
            {district.bestEmoji || '✨'}
          </span>
          <div>
            <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 'bold', color: '#ffffff' }}>
              {district.name}
            </h2>
            <div style={{ fontSize: '11px', color: 'rgba(255, 255, 255, 0.6)', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>行政コード: {district.code}</span>
              <span style={{ background: 'rgba(255, 255, 255, 0.15)', padding: '2px 6px', borderRadius: '4px', color: '#05d5e7' }}>
                演出: {safeEffectKey}
              </span>
            </div>
          </div>
        </div>

        {/* 概要メッセージ */}
        {district.description && (
          <p
            style={{
              fontSize: '13px',
              lineHeight: '1.6',
              color: '#dddddd',
              marginBottom: '12px',
              background: 'rgba(255, 255, 255, 0.04)',
              padding: '10px 14px',
              borderRadius: '12px',
              borderLeft: '3px solid #ffd700',
            }}
          >
            {district.description}
          </p>
        )}

        {/* カテゴリスコア表示 */}
        {activeCategory && district.scores && (
          <div
            style={{
              background: 'linear-gradient(135deg, rgba(255, 215, 0, 0.12), rgba(255, 42, 109, 0.12))',
              border: '1px solid rgba(255, 215, 0, 0.4)',
              borderRadius: '16px',
              padding: '12px 16px',
              marginBottom: '18px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '20px' }}>{activeCategory.emoji}</span>
              <span style={{ fontSize: '14px', fontWeight: 'bold' }}>{activeCategory.label}</span>
            </div>
            
            {/* 🌟 0点回避フォーマットを適用 */}
            <span
              style={{
                fontSize: '22px',
                fontWeight: '900',
                color: getScoreColor(rawMainScore),
              }}
            >
              {formattedMainScore}
              {formattedMainScore !== '-' && formattedMainScore !== 'データ準備中' ? ' 点' : ''}
            </span>
          </div>
        )}

        {/* 強み・弱み・補完区 */}
        {analysis && (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
              marginBottom: '18px',
              fontSize: '12px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>💪 強み: {analysis.best.meta.emoji} {analysis.best.meta.label}</span>
              {/* 🌟 0点回避フォーマットを適用 */}
              <span style={{ fontWeight: 'bold', color: '#00ff9f' }}>
                {formatScore(analysis.best.score) === '-' ? '-' : `${formatScore(analysis.best.score)}点`}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>⚠️ 弱み: {analysis.worst.meta.emoji} {analysis.worst.meta.label}</span>
              {/* 🌟 0点回避フォーマットを適用 */}
              <span style={{ fontWeight: 'bold', color: '#ff5e00' }}>
                {formatScore(analysis.worst.score) === '-' ? '-' : `${formatScore(analysis.worst.score)}点`}
              </span>
            </div>
            {analysis.complement && (
              <button
                className="detail-card-btn"
                onClick={handleJumpToComplement}
                style={{
                  marginTop: '4px',
                  padding: '8px',
                  borderRadius: '10px',
                  border: '1px solid rgba(0, 255, 159, 0.35)',
                  background: 'rgba(0, 255, 159, 0.1)',
                  color: '#00ff9f',
                  fontSize: '11px',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                }}
              >
                {analysis.complement.name}で弱みを補完する →
              </button>
            )}
          </div>
        )}

        {/* スコア一覧 */}
        <div style={{ marginBottom: '18px' }}>
          <h3 style={{ fontSize: '13px', color: '#ffd700', margin: '0 0 10px 0' }}>
            📊 指標別スコア一覧
            <p className="click-hint" style={{ fontSize: '10px', color: '#aaa', margin: '2px 0 0 0' }}>👆 各スコアをクリックして根拠データを見る</p>
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {district.scores &&
              Object.entries(district.scores).map(([key, score]) => {
                const meta = getMetricMeta(key);
                const hasScore = score !== null && score !== undefined;
                const status = district.scoreStatus?.[key];
                const label = status === 'not_implemented' ? '未実装' : status === 'no_data' ? '資料なし' : null;
                
                const scoreColor = getScoreColor(score);
                const isExpanded = expandedKey === key;
                
                // 🌟 個別スコアにも0点回避フォーマットを適用
                const formattedScore = formatScore(score);

                return (
                  <div key={key}>
                    <div
                      onClick={() => hasScore && toggleExpand(key)}
                      style={{ cursor: hasScore ? 'pointer' : 'default', transition: 'opacity 0.2s' }}
                      onMouseOver={(e) => hasScore && (e.currentTarget.style.opacity = '0.8')}
                      onMouseOut={(e) => hasScore && (e.currentTarget.style.opacity = '1')}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '3px' }}>
                        <span>{meta.emoji} {meta.label}</span>
                        <span style={{ fontWeight: 'bold', color: scoreColor }}>
                          {/* 🌟 0点の場合は - だけ表示、そうでない場合は 〇〇点 */}
                          {hasScore ? (formattedScore === '-' ? '-' : `${formattedScore}点`) : label}
                        </span>
                      </div>
                      <div style={{ width: '100%', height: '5px', backgroundColor: 'rgba(255, 255, 255, 0.1)', borderRadius: '3px' }}>
                        <div
                          style={{
                            width: hasScore && formattedScore !== '-' ? `${score}%` : (formattedScore === '-' ? '0%' : '100%'),
                            height: '100%',
                            backgroundColor: hasScore ? scoreColor : 'rgba(255, 255, 255, 0.08)',
                            backgroundImage: hasScore
                              ? 'none'
                              : 'repeating-linear-gradient(45deg, rgba(255,255,255,0.06) 0 4px, transparent 4px 8px)',
                            borderRadius: '3px',
                          }}
                        />
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="mysterious-breakdown" style={{ marginTop: '8px', padding: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '6px' }}>
                        <div style={{ marginBottom: '6px', fontSize: '11px' }}>
                          <span style={{ color: '#aaa' }}>施設・データ総数: </span>
                          <span className="mysterious-text" style={{ color: '#fff' }}>
                            {district.evidence?.facility_count || 0} 件
                          </span>
                        </div>
                        <div style={{ marginBottom: '6px', fontSize: '11px' }}>
                          <span style={{ color: '#aaa' }}>データ信頼性: </span>
                          <span className="mysterious-text" style={{ color: '#fff' }}>
                            {district.evidence?.confidence_score || '---'} %
                          </span>
                        </div>
                        <div style={{ fontSize: '11px' }}>
                          <span style={{ color: '#aaa' }}>参照元情報: </span>
                          <span className="mysterious-text" style={{ fontSize: '10px', color: '#fff' }}>
                            {district.evidence?.datasets?.[0]?.title || '情報収集中...'}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
          </div>
        </div>

        <div className="card-content">
          {/* 🔍 周辺検索ボタン群 */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '14px' }}>
            <button
              className="detail-card-btn"
              onClick={handleGoogleSearch}
              style={{
                padding: '9px',
                borderRadius: '10px',
                border: '1px solid rgba(255, 215, 0, 0.3)',
                background: 'rgba(255, 215, 0, 0.1)',
                color: '#ffd700',
                fontSize: '11px',
                fontWeight: 'bold',
                cursor: 'pointer',
              }}
            >
              🔍 Google検索
            </button>
            <button
              className="detail-card-btn"
              onClick={handleGoogleMaps}
              style={{
                padding: '9px',
                borderRadius: '10px',
                border: '1px solid rgba(5, 213, 231, 0.3)',
                background: 'rgba(5, 213, 231, 0.1)',
                color: '#05d5e7',
                fontSize: '11px',
                fontWeight: 'bold',
                cursor: 'pointer',
              }}
            >
              🗺️ Google Maps
            </button>
          </div>

          {/* 📤 SNS共有ボタン群 */}
          <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.1)', paddingTop: '14px' }}>
            <h3 style={{ fontSize: '12px', color: '#aaaaaa', margin: '0 0 10px 0' }}>
              📤 この結果をシェアする
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
              <button
                className="detail-card-btn"
                onClick={handleShareX}
                style={{
                  padding: '9px 4px',
                  borderRadius: '10px',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                  background: '#000000',
                  color: '#ffffff',
                  fontSize: '11px',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                }}
              >
                𝕏 で投稿
              </button>

              <button
                className="detail-card-btn"
                onClick={handleShareLine}
                style={{
                  padding: '9px 4px',
                  borderRadius: '10px',
                  border: '1px solid rgba(6, 199, 85, 0.4)',
                  background: 'rgba(6, 199, 85, 0.2)',
                  color: '#06c755',
                  fontSize: '11px',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                }}
              >
                LINE 送信
              </button>

              <button
                className="detail-card-btn"
                onClick={handleCopyLink}
                style={{
                  padding: '9px 4px',
                  borderRadius: '10px',
                  border: copied ? '1px solid #00ff9f' : '1px solid rgba(255, 255, 255, 0.2)',
                  background: copied ? 'rgba(0, 255, 159, 0.2)' : 'rgba(255, 255, 255, 0.08)',
                  color: copied ? '#00ff9f' : '#ffffff',
                  fontSize: '11px',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                }}
              >
                {copied ? '✅ コピー完了' : '🔗 リンク作成'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}