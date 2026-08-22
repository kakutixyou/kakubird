 // frontend/Tokyo_hackson_23/src/hooks/useMapScoring.js(apiを使わなくても動くよう.txt)
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
      const radius = 800;
      // 🌟修正1: node ではなく nwr (Node, Way, Relation) を使用し、out center にする
      const query = `
        [out:json][timeout:15];
        (
          nwr["office"](around:${radius},${targetLat},${targetLng});
          nwr["amenity"="hospital"](around:${radius},${targetLat},${targetLng});
          nwr["amenity"="clinic"](around:${radius},${targetLat},${targetLng});
          nwr["shop"="supermarket"](around:${radius},${targetLat},${targetLng});
          nwr["shop"="convenience"](around:${radius},${targetLat},${targetLng});
          nwr["shop"="mall"](around:${radius},${targetLat},${targetLng});
          nwr["leisure"="fitness_centre"](around:${radius},${targetLat},${targetLng});
          nwr["leisure"="park"](around:${radius},${targetLat},${targetLng});
        );
        out center;
      `;

      // 🌟修正2: 安定している公式メインサーバーに変更
      const response = await fetch('https://overpass-api.de/api/interpreter', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ data: query }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) throw new Error(`ネットワークエラー: ${response.status}`);
      const data = await response.json();

      // 🌟修正3: API制限等で elements が無い場合のクラッシュを防ぐ
      if (!data || !data.elements) {
        throw new Error('APIから期待するデータが返ってきませんでした');
      }

      const realPois = data.elements.map(el => {
        let category = 'Other';
        const tags = el.tags || {};
        if (tags.office) category = 'Work';
        else if (tags.amenity === 'hospital' || tags.amenity === 'clinic') category = 'Medical';
        else if (tags.shop === 'supermarket' || tags.shop === 'mall' || tags.shop === 'convenience') category = 'Shopping';
        else if (tags.leisure === 'fitness_centre') category = 'Health';
        else if (tags.leisure === 'park') category = 'Park';

        // 🌟修正4: out center; の場合、wayやrelationの座標は el.center に入る
        const lat = el.lat || (el.center && el.center.lat);
        const lon = el.lon || (el.center && el.center.lon);
        if (!lat || !lon) return null;

        return { id: el.id, name: tags.name || '不明な施設', lat: lat, lng: lon, category };
      }).filter(poi => poi && poi.category !== 'Other');

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