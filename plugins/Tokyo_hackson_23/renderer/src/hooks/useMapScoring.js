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
    setApiError(false); // 🌟 追加: リクエスト開始時にエラー状態をリセット

    try {
      const radius = 800;
      // const query = `
      //   [out:json][timeout:25];
      //   (
      //     nwr["office"](around:${radius},${targetLat},${targetLng});
      //     nwr["amenity"="hospital"](around:${radius},${targetLat},${targetLng});
      //     nwr["amenity"="clinic"](around:${radius},${targetLat},${targetLng});
      //     nwr["shop"="supermarket"](around:${radius},${targetLat},${targetLng});
      //     nwr["shop"="convenience"](around:${radius},${targetLat},${targetLng});
      //     nwr["shop"="mall"](around:${radius},${targetLat},${targetLng});
      //     nwr["leisure"="fitness_centre"](around:${radius},${targetLat},${targetLng});
      //     nwr["leisure"="park"](around:${radius},${targetLat},${targetLng});
      //   );
      //   out center;
      // `;
      // 修正前: nwr["office"]...
      // 修正後: node["office"]... とし、out body; に戻す
 // useMapScoring.js の 90行目付近の query を以下に書き換え
      const query = `
        [out:json][timeout:15];
        (
          node["office"](around:${radius},${targetLat},${targetLng});
          node["amenity"="hospital"](around:${radius},${targetLat},${targetLng});
          node["amenity"="clinic"](around:${radius},${targetLat},${targetLng});
          node["shop"="supermarket"](around:${radius},${targetLat},${targetLng});
          node["shop"="convenience"](around:${radius},${targetLat},${targetLng});
          node["shop"="mall"](around:${radius},${targetLat},${targetLng});
          node["leisure"="fitness_centre"](around:${radius},${targetLat},${targetLng});
          node["leisure"="park"](around:${radius},${targetLat},${targetLng});
        );
        out body;
      `;

      const response = await fetch('https://lz4.overpass-api.de/api/interpreter', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ data: query }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) throw new Error(`ネットワークエラー: ${response.status}`);
      const data = await response.json();

      const realPois = data.elements.map(el => {
        let category = 'Other';
        const tags = el.tags || {};
        if (tags.office) category = 'Work';
        else if (tags.amenity === 'hospital' || tags.amenity === 'clinic') category = 'Medical';
        else if (tags.shop === 'supermarket' || tags.shop === 'mall' || tags.shop === 'convenience') category = 'Shopping';
        else if (tags.leisure === 'fitness_centre') category = 'Health';
        else if (tags.leisure === 'park') category = 'Park';

        // 👇 修正：node のみになったので center へのフォールバックを削除
        const lat = el.lat;
        const lon = el.lon;
        if (!lat || !lon) return null;

        return { id: el.id, name: tags.name || '不明な施設', lat: lat, lng: lon, category };
      }).filter(poi => poi && poi.category !== 'Other');

      setPoiList(realPois);
      recalculateScore([targetLat, targetLng], categories, realPois, workplace);
      setPreviousCenter([targetLat, targetLng]); // 🌟 成功したら「最後に成功した座標」を更新

    } catch (error) {
      if (error.name === 'AbortError') return;
      console.error("データ取得失敗", error);
      setApiError(true);           // 🌟 エラー状態をON
      setCenter(previousCenter);   // 🌟 失敗したら「最後に成功した座標」にマップを戻す
      // 💡 setPoiList([]) と setScore(0) を削除したため、前回のデータが維持される
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