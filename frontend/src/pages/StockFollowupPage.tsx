import React, { useState } from 'react';
import { Link } from 'react-router-dom';

type Checkpoint = { target_date: string; status: 'pending' | 'up' | 'down' | 'flat'; message?: string; price_date?: string; close?: number; change_percent?: number; judgment?: string };
type Followup = {
  symbol: string;
  recommendation_date: string;
  recommendation_url?: string | null;
  baseline: { date: string; close: number; basis: string };
  horizons: Record<string, Checkpoint>;
  data_source: string;
  disclaimer: string;
};
type SavedFollowup = { id: string; created_at: string; result: Followup };
const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8765').replace(/\/$/, '');
const STORAGE_KEY = 'kakubird.stock-followups.v1';

function loadSaved(): SavedFollowup[] {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]') as SavedFollowup[]; } catch { return []; }
}

export default function StockFollowupPage() {
  const [symbol, setSymbol] = useState('');
  const [recommendationDate, setRecommendationDate] = useState(new Date().toISOString().slice(0, 10));
  const [referencePrice, setReferencePrice] = useState('');
  const [recommendationUrl, setRecommendationUrl] = useState('');
  const [result, setResult] = useState<Followup | null>(null);
  const [saved, setSaved] = useState<SavedFollowup[]>(loadSaved);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const analyze = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(''); setLoading(true); setResult(null);
    try {
      const response = await fetch(`${API_BASE}/api/stock-followup`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: symbol.trim(), recommendation_date: recommendationDate, reference_price: referencePrice ? Number(referencePrice) : null, recommendation_url: recommendationUrl.trim() || null }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || '株価の確認に失敗しました。銘柄コードとバックエンドを確認してください。');
      setResult(data as Followup);
    } catch (err) { setError(err instanceof Error ? err.message : '分析に失敗しました。'); }
    finally { setLoading(false); }
  };

  const save = () => {
    if (!result) return;
    const next = [{ id: `${Date.now()}-${result.symbol}`, created_at: new Date().toISOString(), result }, ...saved].slice(0, 100);
    setSaved(next);
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); }
    catch { setError('保存に失敗しました。ブラウザーのローカル保存容量を確認してください。'); }
  };

  const removeSaved = (id: string) => {
    const next = saved.filter((item) => item.id !== id);
    setSaved(next);
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); } catch { /* The in-memory list still updates. */ }
  };

  return <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900 sm:px-8">
    <div className="mx-auto max-w-5xl">
      <Link to="/analysis" className="text-sm font-medium text-indigo-600 hover:underline">← テーマ分析に戻る</Link>
      <header className="mb-8 mt-5"><p className="text-sm font-semibold uppercase tracking-widest text-indigo-600">Recommendation follow-up</p><h1 className="mt-2 text-3xl font-bold">紹介後の株価を追跡</h1><p className="mt-2 max-w-3xl text-slate-600">銘柄コードと紹介日を記録し、紹介後の1日・7日・1ヶ月の終値が基準価格より上がったか下がったかを確認します。</p></header>
      <form onSubmit={analyze} className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:grid-cols-2 sm:p-7">
        <label className="text-sm font-semibold">銘柄コード<input required value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="例: 7203.jp / aapl.us" className="mt-2 block w-full rounded-xl border border-slate-300 px-4 py-3 font-normal outline-none focus:border-indigo-500" /><span className="mt-1 block text-xs font-normal text-slate-500">Stooqのシンボル表記を入力（日本株の例: 7203.jp、米国株の例: aapl.us）</span></label>
        <label className="text-sm font-semibold">紹介日<input required type="date" value={recommendationDate} onChange={(e) => setRecommendationDate(e.target.value)} className="mt-2 block w-full rounded-xl border border-slate-300 px-4 py-3 font-normal" /></label>
        <label className="text-sm font-semibold">紹介時の価格（任意）<input type="number" min="0.000001" step="any" value={referencePrice} onChange={(e) => setReferencePrice(e.target.value)} placeholder="空欄なら紹介日近辺の終値を代用" className="mt-2 block w-full rounded-xl border border-slate-300 px-4 py-3 font-normal" /><span className="mt-1 block text-xs font-normal text-slate-500">記事に書かれた価格が分かる場合は入力。比較基準が明確になります。</span></label>
        <label className="text-sm font-semibold">紹介元URL（任意）<input type="url" value={recommendationUrl} onChange={(e) => setRecommendationUrl(e.target.value)} placeholder="https://..." className="mt-2 block w-full rounded-xl border border-slate-300 px-4 py-3 font-normal" /></label>
        <div className="sm:col-span-2"><button disabled={loading || !symbol.trim()} className="rounded-xl bg-indigo-600 px-6 py-3 font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">{loading ? '株価を確認中…' : '株価を照合'}</button><p className="mt-3 text-xs leading-5 text-slate-500">1日後・7日後は紹介日からの暦日で、休場日は次の取引日の終値を採用します。1ヶ月後は暦上の同日（同日がない月は月末）以降の取引日で判定します。</p></div>
      </form>
      {error && <div role="alert" className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-700">{error}</div>}
      {result && <FollowupCard result={result} onSave={save} />}
      <section className="mt-10"><div className="mb-4 flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-2xl font-bold">記録した紹介</h2><p className="mt-1 text-sm text-slate-500">このブラウザー内に保存されます。別の端末とは同期されません。</p></div><span className="rounded-full bg-slate-200 px-3 py-1 text-sm">{saved.length} 件</span></div>
        {saved.length === 0 ? <p className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">まだ記録はありません。</p> : <div className="space-y-3">{saved.map((item) => <article key={item.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4"><div><strong>{item.result.symbol}</strong><span className="ml-3 text-sm text-slate-600">紹介日 {item.result.recommendation_date}</span><p className="mt-1 text-xs text-slate-500">{Object.entries(item.result.horizons).map(([label, point]) => `${label}: ${point.status === 'pending' ? '判定待ち' : `${point.change_percent}% (${point.judgment})`}`).join('　·　')}</p></div><button onClick={() => removeSaved(item.id)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50">削除</button></article>)}</div>}
      </section>
    </div>
  </main>;
}

function FollowupCard({ result, onSave }: { result: Followup; onSave: () => void }) {
  return <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">{result.data_source}</p><h2 className="mt-1 text-xl font-bold">{result.symbol} · 紹介日 {result.recommendation_date}</h2><p className="mt-1 text-sm text-slate-600">比較基準: {result.baseline.close} ({result.baseline.date}, {result.baseline.basis})</p>{result.recommendation_url && <a className="mt-1 inline-block text-sm text-indigo-700 underline" href={result.recommendation_url} target="_blank" rel="noreferrer">紹介元を開く</a>}</div><button onClick={onSave} className="rounded-xl border border-indigo-300 px-4 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-50">この記録を保存</button></div><div className="mt-5 grid gap-3 md:grid-cols-3">{Object.entries(result.horizons).map(([label, point]) => <article key={label} className={`rounded-xl border p-4 ${point.status === 'down' ? 'border-rose-200 bg-rose-50' : point.status === 'up' ? 'border-emerald-200 bg-emerald-50' : 'border-slate-200 bg-slate-50'}`}><h3 className="font-bold">{label}</h3>{point.status === 'pending' ? <p className="mt-2 text-sm text-slate-600">判定待ち<p className="mt-1 text-xs">{point.target_date}: {point.message}</p></p> : <><p className={`mt-2 text-2xl font-bold ${point.status === 'down' ? 'text-rose-700' : point.status === 'up' ? 'text-emerald-700' : 'text-slate-700'}`}>{point.change_percent! > 0 ? '+' : ''}{point.change_percent}%</p><p className="mt-1 text-sm">{point.judgment} · 終値 {point.close}</p><p className="mt-1 text-xs text-slate-500">判定に使った取引日: {point.price_date}</p></>}</article>)}</div><p className="mt-5 rounded-xl bg-amber-50 p-4 text-xs leading-5 text-amber-950">{result.disclaimer}</p></section>;
}
