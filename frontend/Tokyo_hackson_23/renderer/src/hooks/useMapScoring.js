// frontend/Tokyo_hackson_23/src/hooks/useMapScoring.js
import { useState, useCallback, useEffect } from 'react';
import { PILLAR_CATEGORIES, calculateDistanceMeters, getDistanceScore } from '../utils/distanceUtils';

export function useMapScoring(initialCenter) {
  const [center, setCenter] = useState(initialCenter);
  const [poiList, setPoiList] = useState([]);
  const [isEvaluating, setIsEvaluating] = useState(false);

  const [categories, setCategories] = useState(
    PILLAR_CATEGORIES.map(cat => ({ ...cat, enabled: cat.enabled ?? true }))
  );
  const [score, setScore] = useState(0);

  // 1. カテゴリの表示/非表示を切り替える関数
  const toggleCategory = useCallback((categoryId) => {
    setCategories(prev => {
      const newCategories = prev.map(cat =>
        cat.id === categoryId ? { ...cat, enabled: !cat.enabled } : cat
      );
      recalculateScore(center, newCategories, poiList);
      return newCategories;
    });
  }, [center, poiList]);

  // 2. 重み付き・距離ベースのスコアリングロジック
  //    各カテゴリについて「最寄りの施設までの徒歩分数」からスコアを出し、
  //    weight で加重平均する。施設が0件のカテゴリはスコア0として重みに含める。
  const recalculateScore = useCallback((targetPos, currentCategories, pois) => {
    const activeCategories = currentCategories.filter(c => c.enabled);

    if (activeCategories.length === 0) {
      setScore(0);
      return;
    }

    let weightedTotal = 0;
    let weightSum = 0;

    activeCategories.forEach(cat => {
      const categoryPois = pois.filter(poi => poi.category === cat.id);
      let categoryScore = 0;

      if (categoryPois.length > 0) {
        const nearestDistance = Math.min(
          ...categoryPois.map(poi => calculateDistanceMeters(targetPos, [poi.lat, poi.lng]))
        );
        const walkingTimeMinutes = nearestDistance / 80; // 徒歩速度 約80m/分
        categoryScore = getDistanceScore(walkingTimeMinutes);
      }

      weightedTotal += categoryScore * cat.weight;
      weightSum += cat.weight;
    });

    const finalScore = weightSum > 0 ? Math.round(weightedTotal / weightSum) : 0;
    setScore(finalScore);
  }, []);

  // 3. OpenStreetMap (Overpass API) から実データをFetch
// 3. OpenStreetMap (Overpass API) から実データをFetch
  const fetchPois = useCallback(async (targetLat, targetLng) => {
    setIsEvaluating(true);
    try {
      const radius = 1500; // 🌟 1.5kmに変更（nwrでデータが増えるため、少し絞ると高速になります）

      // 🌟 修正ポイント1: node を nwr に変更し、コンビニを追加！
      // 🌟 修正ポイント2: out body; を out center; に変更！
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

      const response = await fetch('https://overpass-api.de/api/interpreter', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `data=${encodeURIComponent(query)}`
      });

      if (!response.ok) throw new Error('ネットワークエラー');

      const data = await response.json();

      const realPois = data.elements.map(el => {
        let category = 'Other';
        const tags = el.tags || {};

        // カテゴリの振り分け
        if (tags.office) category = 'Work';
        else if (tags.amenity === 'hospital' || tags.amenity === 'clinic') category = 'Medical';
        else if (tags.shop === 'supermarket' || tags.shop === 'mall' || tags.shop === 'convenience') category = 'Shopping'; // 🌟 コンビニもShoppingに追加
        else if (tags.leisure === 'fitness_centre') category = 'Health';
        else if (tags.leisure === 'park') category = 'Park';

        // 🌟 修正ポイント3: 面（way/relation）の場合は center の座標を取得する
        const lat = el.lat || (el.center && el.center.lat);
        const lon = el.lon || (el.center && el.center.lon);

        if (!lat || !lon) return null; // 座標がない不正データは除外

        return {
          id: el.id,
          name: tags.name || '名称不明の施設',
          lat: lat,
          lng: lon, // OSMは 'lon' 
          category
        };
      }).filter(poi => poi && poi.category !== 'Other'); // nullを除外するために poi && を追加

      setPoiList(realPois);
      recalculateScore([targetLat, targetLng], categories, realPois);

    } catch (error) {
      console.error("データの取得に失敗しました", error);
      setPoiList([]);
      setScore(0);
    } finally {
      setIsEvaluating(false);
    }
  }, [categories, recalculateScore]);

  // マップクリック時の処理
  const handleMapClick = useCallback((newPos) => {
    setCenter(newPos);
    fetchPois(newPos[0], newPos[1]);
  }, [fetchPois]);

  useEffect(() => {
    fetchPois(initialCenter[0], initialCenter[1]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    center,
    isEvaluating,
    categories,
    score,
    toggleCategory,
    handleMapClick,
    poiList, // ← 実際にスコアに使っているPOIをそのまま返す（地図表示にもこれを使う）
  };
}