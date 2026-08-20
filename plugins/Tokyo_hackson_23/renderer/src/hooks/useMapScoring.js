// frontend/Tokyo_hackson_23/src/hooks/useMapScoring.js
import { useState, useCallback, useEffect, useRef } from 'react';
import { PILLAR_CATEGORIES, calculateDistanceMeters, getDistanceScore } from '../utils/distanceUtils';

export function useMapScoring(initialCenter) {
  const [center, setCenter] = useState(initialCenter);
  const [previousCenter, setPreviousCenter] = useState(initialCenter); // 🌟 追加: 最後に成功した座標
  const [poiList, setPoiList] = useState([]);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [workplace, setWorkplace] = useState(null);
  const [categories, setCategories] = useState(
    PILLAR_CATEGORIES.map(cat => ({ ...cat, enabled: cat.enabled ?? true }))
  );
  const [score, setScore] = useState(0);
  const [apiError, setApiError] = useState(false); // 🌟 追加: エラー状態を管理

  const abortControllerRef = useRef(null);

  const recalculateScore = useCallback((targetPos, currentCategories, pois, currentWorkplace) => {
    const activeCategories = currentCategories.filter(c => c.enabled);
    if (activeCategories.length === 0) {
      setScore(0); return;
    }

    let weightedTotal = 0;
    let weightSum = 0;

    activeCategories.forEach(cat => {
      let categoryScore = 0;
      if (cat.id === 'Work' && currentWorkplace) {
        const distance = calculateDistanceMeters(targetPos, currentWorkplace);
        const commuteMinutes = distance / 400; 
        categoryScore = getDistanceScore(commuteMinutes);
      } else {
        const categoryPois = pois.filter(poi => poi.category === cat.id);
        if (categoryPois.length > 0) {
          const nearestDistance = Math.min(
            ...categoryPois.map(poi => calculateDistanceMeters(targetPos, [poi.lat, poi.lng]))
          );
          categoryScore = getDistanceScore(nearestDistance / 80);
        }
      }
      weightedTotal += categoryScore * cat.weight;
      weightSum += cat.weight;
    });

    const finalScore = weightSum > 0 ? Math.round(weightedTotal / weightSum) : 0;
    setScore(finalScore);
  }, []);

  const toggleCategory = useCallback((categoryId) => {
    setCategories(prev => {
      const newCategories = prev.map(cat =>
        cat.id === categoryId ? { ...cat, enabled: !cat.enabled } : cat
      );
      recalculateScore(center, newCategories, poiList, workplace);
      return newCategories;
    });
  }, [center, poiList, workplace, recalculateScore]);

  const handleSetWorkplace = useCallback((newWorkplace) => {
    setWorkplace(newWorkplace);
    recalculateScore(center, categories, poiList, newWorkplace);
  }, [center, categories, poiList, recalculateScore]);
const fetchPois = useCallback(async (targetLat, targetLng) => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    abortControllerRef.current = new AbortController();

    setIsEvaluating(true);
    setApiError(false);

    try {
      // 🌟 ① 確認できたRenderのAPI URLを指定
      const BASE_URL = 'https://kakubird.onrender.com';

      // 🌟 ② フロントのカテゴリと、バックエンドの「theme」を紐付け
      const themeMapping = {
        'Medical': 'medical',
        'Shopping': 'shopping',
        'Health': 'sports', 
        'Park': 'park',
      };

      // 有効なカテゴリだけを抽出し、リクエスト用の配列を作成
      const activeThemes = categories
        .filter(cat => cat.enabled && themeMapping[cat.id])
        .map(cat => ({ categoryId: cat.id, theme: themeMapping[cat.id] }));

      // 🌟 ③ 各テーマのバックエンドAPIを同時にリクエスト
      const fetchPromises = activeThemes.map(async ({ categoryId, theme }) => {
        // バックエンドの /api/facilities エンドポイントを叩く
        const res = await fetch(`${BASE_URL}/api/facilities?theme=${theme}&limit=1000`, {
          signal: abortControllerRef.current.signal
        });
        
        if (!res.ok) throw new Error(`APIエラー: ${theme} - ${res.status}`);
        const data = await res.json();
        
        // 🌟 ④ バックエンドのデータをフロントの形式 (lat, lng, category) に変換
        return data.map(facility => ({
          id: facility.id,
          name: facility.name || '不明な施設',
          lat: facility.latitude,
          lng: facility.longitude,
          category: categoryId
        }));
      });

      // すべてのAPIリクエストが完了するのを待つ
      const results = await Promise.all(fetchPromises);
      
      // 複数のテーマの配列を1つにまとめ、緯度経度がない不正データを弾く
      const realPois = results.flat().filter(poi => poi.lat && poi.lng);

      setPoiList(realPois);
      recalculateScore([targetLat, targetLng], categories, realPois, workplace);
      setPreviousCenter([targetLat, targetLng]);

    } catch (error) {
      if (error.name === 'AbortError') return;
      console.error("データ取得失敗", error);
      setApiError(true);
      setCenter(previousCenter);
    } finally {
      setIsEvaluating(false);
    }
  }, [categories, workplace, recalculateScore, previousCenter]);
  const handleMapClick = useCallback((newPos) => {
    setCenter(newPos);
    fetchPois(newPos[0], newPos[1]);
  }, [fetchPois]);

  useEffect(() => {
    if (initialCenter && initialCenter.length === 2) {
      fetchPois(initialCenter[0], initialCenter[1]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 🌟 返り値に apiError を追加
  return { center, isEvaluating, categories, score, toggleCategory, handleMapClick, poiList, workplace, handleSetWorkplace, apiError };
}