// frontend/src/hooks/useHighRated.ts を上書き

import { useCallback, useEffect, useRef, useState } from 'react';
import type { HighRatedItem, RatingKind, RatingSource } from '../types/highRated';

const API_BASE: string = import.meta.env.VITE_API_BASE ?? '';

interface Options {
  enabled: boolean;
  kind: RatingKind;
  source: RatingSource;
  limit?: number;
}

export function useHighRated({ enabled, kind, source, limit = 20 }: Options) {
  const [items, setItems] = useState<HighRatedItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const load = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ kind, source, limit: String(limit) });
      const res = await fetch(`${API_BASE}/api/to/high-rated?${params}`, {
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      
      const responseData: { data: HighRatedItem[] } = await res.json();
      setItems(Array.isArray(responseData.data) ? responseData.data : []);
    } catch (e) {
      if ((e as Error).name === 'AbortError') return;
      setError('高評価リストを取得できませんでした。');
      setItems([]);
    } finally {
      if (abortRef.current === controller) setIsLoading(false);
    }
  }, [kind, source, limit]);

  // 💡 追加: 削除機能
  const removeItem = useCallback(async (id: string) => {
    // 画面から先に消して体感速度を上げる(オプティミスティックUI)
    setItems((prev) => prev.filter(item => item.id !== id));
    
    try {
      const res = await fetch(`${API_BASE}/api/to/ratings/like/${id}`, {
        method: 'DELETE',
      });
      if (!res.ok) throw new Error('Delete failed');
    } catch (e) {
      console.error("削除に失敗しました", e);
      // 失敗したらリロードして元に戻す
      void load(); 
    }
  }, [load]);

  useEffect(() => {
    if (!enabled) return;
    void load();
    return () => abortRef.current?.abort();
  }, [enabled, load]);

  return { items, isLoading, error, reload: load, removeItem };
}