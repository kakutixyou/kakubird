import React, { useState } from 'react';
import { Link } from 'react-router-dom';

type Source = 'qiita' | 'github' | 'youtube';
type Result = {
  source: Source;
  title: string;
  url: string;
  description: string;
  category: string;
  published_at?: string;
  metrics?: Record<string, number | string>;
  evidence?: string[];
  moments?: { seconds: number; url: string }[];
};
type Analysis = {
  query: string;
  normalized_terms: string[];
  categories: string[];
  stock_analysis: null | { win_mentions: number; loss_mentions: number; reason_mentions: number; note: string };
  results: Result[];
  warnings: string[];
};

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8765').replace(/\/$/, '');
const sourceLabels: Record<Source, string> = { qiita: 'Qiita', github: 'GitHub', youtube: 'YouTube' };

export default function TopicAnalysisPage() {
  const [query, setQuery] = useState('りんご');
  const [category, setCategory] = useState('すべて');
  const [sources, setSources] = useState<Source[]>(['qiita', 'github', 'youtube']);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const runAnalysis = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!query.trim() || sources.length === 0) return;
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_BASE}/api/topic-analysis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query.trim(), category, sources }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || '分析に失敗しました。バックエンドの起動状態を確認してください。');
      setAnalysis(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '分析に失敗しました。');
    } finally {
      setLoading(false);
    }
  };

  const toggleSource = (source: Source) => setSources((current) =>
    current.includes(source) ? current.filter((item) => item !== source) : [...current, source],
  );

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900 sm:px-8">
      <div className="mx-auto max-w-6xl">
        <Link to="/" className="text-sm font-medium text-indigo-600 hover:underline">← ダッシュボード</Link>
        <header className="mb-8 mt-5">
          <p className="text-sm font-semibold uppercase tracking-widest text-indigo-600">Cross-source explorer</p>
          <h1 className="mt-2 text-3xl font-bold">テーマを絞って情報を分析</h1>
          <p className="mt-2 max-w-3xl text-slate-600">Qiita・GitHub・YouTubeを横断して検索。りんご／appleのような表記ゆれを補い、テーマ別に結果を見やすく整理します。</p>
        </header>

        <form onSubmit={runAnalysis} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
          <label htmlFor="topic-query" className="mb-2 block text-sm font-semibold">調べたいテーマ</label>
          <div className="flex flex-col gap-3 sm:flex-row">
            <input id="topic-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="例：りんご、株、React" className="min-w-0 flex-1 rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100" />
            <select aria-label="テーマ分類" value={category} onChange={(event) => setCategory(event.target.value)} className="rounded-xl border border-slate-300 bg-white px-4 py-3">
              <option>すべて</option><option>料理</option><option>料金</option><option>美味しさ</option><option>検索</option><option>株価</option><option>売買理由</option>
            </select>
            <button disabled={loading || !query.trim() || sources.length === 0} className="rounded-xl bg-indigo-600 px-6 py-3 font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50">{loading ? '分析中…' : '分析する'}</button>
          </div>
          <fieldset className="mt-5">
            <legend className="mb-2 text-sm font-semibold">情報源</legend>
            <div className="flex flex-wrap gap-2">{(['qiita', 'github', 'youtube'] as Source[]).map((source) => (
              <label key={source} className={`cursor-pointer rounded-full border px-4 py-2 text-sm ${sources.includes(source) ? 'border-indigo-300 bg-indigo-50 text-indigo-700' : 'border-slate-200 text-slate-500'}`}>
                <input type="checkbox" className="sr-only" checked={sources.includes(source)} onChange={() => toggleSource(source)} />{sourceLabels[source]}
              </label>
            ))}</div>
          </fieldset>
          <p className="mt-3 text-xs text-slate-500">YouTube検索にはサーバー側の YOUTUBE_API_KEY が必要です。APIが設定されていない情報源は警告として表示されます。</p>
        </form>

        {error && <div role="alert" className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-700">{error}</div>}
        {analysis && <section className="mt-8" aria-live="polite">
          <div className="mb-5 flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-2xl font-bold">「{analysis.query}」の分析結果</h2><p className="mt-1 text-sm text-slate-500">検索語: {analysis.normalized_terms.join(' / ')}</p></div><span className="rounded-full bg-slate-200 px-3 py-1 text-sm">{analysis.results.length} 件</span></div>
          <div className="mb-5 flex flex-wrap gap-2">{analysis.categories.map((item) => <span key={item} className="rounded-full bg-white px-3 py-1.5 text-sm text-slate-700 shadow-sm">{item}</span>)}</div>
          {analysis.stock_analysis && <div className="mb-6 rounded-2xl border border-amber-200 bg-amber-50 p-5"><h3 className="font-bold text-amber-950">株に関する言及の手がかり</h3><div className="mt-3 grid gap-3 sm:grid-cols-3"><Metric label="勝ち・利益への言及" value={analysis.stock_analysis.win_mentions} /><Metric label="負け・損失への言及" value={analysis.stock_analysis.loss_mentions} /><Metric label="理由への言及" value={analysis.stock_analysis.reason_mentions} /></div><p className="mt-3 text-xs text-amber-900">{analysis.stock_analysis.note}</p></div>}
          {analysis.warnings.length > 0 && <div className="mb-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">{analysis.warnings.map((warning) => <p key={warning}>• {warning}</p>)}</div>}
          {analysis.results.length === 0 ? <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">該当する情報はありません。テーマや情報源を変えて再検索してください。</div> : <div className="grid gap-4 lg:grid-cols-2">{analysis.results.map((result) => <article key={`${result.source}:${result.url}`} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="mb-3 flex items-center justify-between gap-3"><span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700">{sourceLabels[result.source]}</span><span className="text-xs text-slate-500">{result.category}{result.published_at ? ` · ${result.published_at.slice(0, 10)}` : ''}</span></div><h3 className="text-lg font-bold leading-snug"><a href={result.url} target="_blank" rel="noreferrer" className="hover:text-indigo-700">{result.title}</a></h3><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600">{result.description || '概要はありません。'}</p>{result.metrics && <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">{Object.entries(result.metrics).map(([key, value]) => <span key={key}>{key}: {value}</span>)}</div>}{result.evidence && result.evidence.length > 0 && <p className="mt-3 text-xs text-amber-800">言及: {result.evidence.join('、')}</p>}{result.moments && <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3"><span className="mr-1 text-xs text-slate-500">動画の冒頭へ:</span>{result.moments.map((moment) => <a key={moment.seconds} href={moment.url} target="_blank" rel="noreferrer" className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-medium hover:bg-indigo-100">{moment.seconds}秒</a>)}</div>}</article>)}</div>}
        </section>}
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-xl bg-white/80 p-3"><p className="text-xs text-slate-500">{label}</p><p className="mt-1 text-xl font-bold text-slate-900">{value} 件</p></div>;
}
