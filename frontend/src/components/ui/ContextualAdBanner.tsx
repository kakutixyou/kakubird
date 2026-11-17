// frontend/src/components/ui/ContextualAdBanner.tsx
import React, { useState, useEffect, useMemo } from "react";
import { ExternalLink, EyeOff, Sparkles, Coffee, Image as ImageIcon } from "lucide-react";
import {
  LoadingContextType,
  inferLoadingContextFromPrompt,
} from "./LoadingIndicator";

export interface AdSlotItem {
  id: string;
  badge: string;
  categoryLabel: string;
  title: string;
  description: string;
  url: string;
  imageUrl?: string; // 🆕 バナー・書籍サムネイル画像URL（Base64やローカルパスも可）
  imageAlt?: string;
  ctaText?: string;
}

export interface ContextualAdBannerProps {
  contextType?: LoadingContextType;
  promptHint?: string;
  customAd?: AdSlotItem;
  compact?: boolean;
  showRestoreToggle?: boolean;
  className?: string;
}

const STORAGE_KEY_AD_ENABLED = "to_studio_contextual_ad_enabled";

const CONTEXTUAL_AD_CATALOG: Record<LoadingContextType, AdSlotItem> = {
  default: {
    id: "ad_default_dev",
    badge: "PR",
    categoryLabel: "AI開発・インフラ応援",
    title: "ローカルAI ＆ 省電力開発環境ガイド",
    description:
      "KnowledgeRouterと小型モデルでGPU代と電気代を抑える実践アーキテクチャ解説書",
    url: "https://example.com/pr/green-ai-architecture",
    imageUrl: "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=160&auto=format&fit=crop&q=80",
    ctaText: "詳細を見る",
  },
  value_eval: {
    id: "ad_ethics_energy",
    badge: "PR / 書籍・教養",
    categoryLabel: "倫理・エネルギー3E+S",
    title: "『これからの「正義」の話をしよう ／ エネルギーと地域共生の経済学』",
    description:
      "トロッコ問題から原発・データセンターの排熱活用まで、対話と合意形成を深める必読書",
    url: "https://example.com/pr/ethics-and-energy-books",
    imageUrl: "https://images.unsplash.com/photo-1473341304170-971dccb5ac1e?w=160&auto=format&fit=crop&q=80",
    ctaText: "書籍を見る",
  },
  security: {
    id: "ad_security_lab",
    badge: "PR / 専門書",
    categoryLabel: "マルウェア解析・防衛",
    title: "『実践マルウェア解析 ＆ リバースエンジニアリング入門』",
    description:
      "仮想Ubuntuラボ構築、PEヘッダ表層解析、INetSimによるC2通信捕捉をゼロから学べる教本",
    url: "https://example.com/pr/malware-analysis-book",
    imageUrl: "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=160&auto=format&fit=crop&q=80",
    ctaText: "教材を見る",
  },
  niche_column: {
    id: "ad_niche_encyclopedia",
    badge: "PR / 図鑑・史料",
    categoryLabel: "専門コラム・フィールド図鑑",
    title: "『ビジュアル日本史料 ＆ 菌類・自然科学フィールド図鑑』",
    description:
      "一次史料の背景や、キノコ・鉱物・生物の構造特徴を美しい写真で深掘りできる専門図鑑",
    url: "https://example.com/pr/niche-encyclopedia",
    imageUrl: "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=160&auto=format&fit=crop&q=80",
    ctaText: "図鑑を見る",
  },
  ocr_grading: {
    id: "ad_ocr_scanner",
    badge: "PR / 機材・ツール",
    categoryLabel: "OCR・自動採点効率化",
    title: "ドキュメントスキャナー ＆ 構造特徴アルゴリズム実践ガイド",
    description:
      "答案用紙の斜め撮影補正やミリ単位の枠切り出し精度を高める周辺機器と画像処理ノウハウ",
    url: "https://example.com/pr/ocr-scanner-tools",
    imageUrl: "https://images.unsplash.com/photo-1586281380349-632531db7ed4?w=160&auto=format&fit=crop&q=80",
    ctaText: "ツールを見る",
  },
  ocr_character: {
    id: "ad_ocr_font",
    badge: "PR / フォント・文字解析",
    categoryLabel: "手書き文字・フォント設計",
    title: "『文字骨格トポロジーとオリジナルフォント制作入門』",
    description:
      "閉ループ・交差数・ストローク密度の解析からTTF/WOFF2出力までを学ぶガイド",
    url: "https://example.com/pr/font-topology-guide",
    imageUrl: "https://images.unsplash.com/photo-1455390582262-044cdead277a?w=160&auto=format&fit=crop&q=80",
    ctaText: "詳細を見る",
  },
  sql: {
    id: "ad_sql_db",
    badge: "PR / データベース",
    categoryLabel: "SQL・データ設計",
    title: "『達人に学ぶSQL徹底指南書 ＆ 高速インデックス設計』",
    description: "SQLiteから大規模RDBまで、安全なクエリ構築とチューニングの定石",
    url: "https://example.com/pr/sql-master-book",
    ctaText: "詳細を見る",
  },
  css: {
    id: "ad_css_ui",
    badge: "PR / UIデザイン",
    categoryLabel: "Tailwind CSS & コンポーネント設計",
    title: "『Refactoring UI — エンジニアのための実践デザインシステム』",
    description: "ダークモード配色、余白、視線誘導を論理的に組み立てる決定版",
    url: "https://example.com/pr/refactoring-ui",
    ctaText: "詳細を見る",
  },
  job_eval: {
    id: "ad_career_it",
    badge: "PR / キャリア",
    categoryLabel: "エンジニアキャリア・労働法規",
    title: "『ITエンジニアのための労働法規・下請法 ＆ 健全なキャリア選び』",
    description: "求人票のチェックポイントと価値観に合った開発環境を見極めるガイド",
    url: "https://example.com/pr/engineer-career-guide",
    ctaText: "詳細を見る",
  },
  knowledge: {
    id: "ad_knowledge_rag",
    badge: "PR / AI設計",
    categoryLabel: "RAG・ナレッジ検索",
    title: "『ハイブリッド検索 ＆ ナレッジグラフ構築実践入門』",
    description: "決定論的ルーターとベクトル検索を組み合わせた高速・低コストAI設計",
    url: "https://example.com/pr/rag-knowledge-book",
    ctaText: "詳細を見る",
  },
  workspace_zip: {
    id: "ad_workspace_clean",
    badge: "PR / アーキテクチャ",
    categoryLabel: "リファクタリング・構造解析",
    title: "『良いコード／悪いコードで学ぶ設計入門』",
    description: "チャンク分割や依存関係グラフを綺麗に保つためのモジュール設計術",
    url: "https://example.com/pr/clean-code-architecture",
    ctaText: "詳細を見る",
  },
  project_build: {
    id: "ad_project_template",
    badge: "PR / フルスタック",
    categoryLabel: "React × FastAPI × Electron",
    title: "『モダンフルスタック・デスクトップアプリ開発テンプレート集』",
    description: "PythonバックエンドとTypeScriptフロントエンドを統合するブループリント",
    url: "https://example.com/pr/fullstack-blueprint",
    ctaText: "詳細を見る",
  },
  agent: {
    id: "ad_agent_orchestrator",
    badge: "PR / AIエージェント",
    categoryLabel: "自律エージェント設計",
    title: "『マルチハンドラー・AIオーケストレーター設計パターン』",
    description: "IntentInspectorと専門Handler群を協調させる自己検証型AIシステムの作り方",
    url: "https://example.com/pr/ai-orchestrator-patterns",
    ctaText: "詳細を見る",
  },
  copilot: {
    id: "ad_copilot_dev",
    badge: "PR / 開発機材",
    categoryLabel: "コーディング・ゲーム制作",
    title: "Python / React / Unity / Blender 快適開発ギア特集",
    description: "長時間のコーディングや3Dモデリングを支えるキーボード＆モニター環境",
    url: "https://example.com/pr/developer-gear",
    imageUrl: "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=160&auto=format&fit=crop&q=80",
    ctaText: "機材を見る",
  },
};

export function useContextualAdPreference(): [boolean, (next: boolean) => void] {
  const [enabled, setEnabled] = useState<boolean>(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY_AD_ENABLED);
      return saved === null ? true : saved === "true";
    } catch {
      return true;
    }
  });

  useEffect(() => {
    const handleCustomEvent = (e: Event) => {
      const custom = e as CustomEvent<boolean>;
      if (typeof custom.detail === "boolean") setEnabled(custom.detail);
    };
    window.addEventListener("to-ad-pref-change", handleCustomEvent);
    return () => window.removeEventListener("to-ad-pref-change", handleCustomEvent);
  }, []);

  const updatePreference = (next: boolean) => {
    setEnabled(next);
    try {
      window.localStorage.setItem(STORAGE_KEY_AD_ENABLED, String(next));
      window.dispatchEvent(new CustomEvent("to-ad-pref-change", { detail: next }));
    } catch {}
  };

  return [enabled, updatePreference];
}

export default function ContextualAdBanner({
  contextType = "default",
  promptHint,
  customAd,
  compact = false,
  showRestoreToggle = true,
  className = "",
}: ContextualAdBannerProps): React.ReactElement | null {
  const [adEnabled, setAdEnabled] = useContextualAdPreference();
  const [imgError, setImgError] = useState(false);

  const resolvedContext = useMemo(
    () => inferLoadingContextFromPrompt(promptHint, contextType),
    [promptHint, contextType]
  );

  const adItem: AdSlotItem = useMemo(() => {
    setImgError(false);
    if (customAd) return customAd;
    return (
      CONTEXTUAL_AD_CATALOG[resolvedContext.context] ||
      CONTEXTUAL_AD_CATALOG.default
    );
  }, [customAd, resolvedContext.context]);

  if (!adEnabled) {
    if (!showRestoreToggle) return null;
    return (
      <div className={`flex justify-end ${className}`}>
        <button
          type="button"
          onClick={() => setAdEnabled(true)}
          style={{ opacity: 0.45 }}
          className="inline-flex items-center gap-1 rounded-md border border-slate-700/50 bg-slate-900/40 px-2 py-0.5 text-[10px] text-slate-400 transition hover:opacity-100 hover:text-slate-200"
        >
          <Coffee className="h-2.5 w-2.5" />
          <span>開発応援[PR]を表示</span>
        </button>
      </div>
    );
  }

  return (
    <div
      style={{ opacity: 0.6 }}
      className={`group relative rounded-xl border border-dashed border-slate-300/80 bg-slate-50/60 p-3 text-xs text-slate-600 transition-all duration-200 hover:!opacity-100 hover:border-indigo-500/50 dark:border-slate-800 dark:bg-slate-900/45 dark:text-slate-300 ${className}`}
    >
      <div className="flex items-center gap-3">
        {/* 🆕 サムネイル画像表示スロット（エラー時はアイコンにフォールバック） */}
        {!compact && (
          <div className="h-14 w-14 shrink-0 overflow-hidden rounded-lg border border-slate-200 bg-slate-900/60 flex items-center justify-center dark:border-slate-800">
            {adItem.imageUrl && !imgError ? (
              <img
                src={adItem.imageUrl}
                alt={adItem.imageAlt || adItem.title}
                onError={() => setImgError(true)}
                className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                loading="lazy"
              />
            ) : (
              <ImageIcon className="h-5 w-5 text-slate-500" />
            )}
          </div>
        )}

        <div className="space-y-1 flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-bold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
              {adItem.badge}
            </span>
            <span className="text-[10px] font-medium text-indigo-500 dark:text-indigo-400 flex items-center gap-0.5">
              <Sparkles className="h-2.5 w-2.5" />
              {adItem.categoryLabel}
            </span>
          </div>

          <a
            href={adItem.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block group-hover:underline"
          >
            <div className="font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1">
              <span className="truncate">{adItem.title}</span>
              <ExternalLink className="h-3 w-3 shrink-0 text-indigo-400" />
            </div>
            {!compact && (
              <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400 line-clamp-1">
                {adItem.description}
              </p>
            )}
          </a>
        </div>

        <div className="flex flex-col items-end gap-1.5 shrink-0">
          <button
            type="button"
            onClick={() => setAdEnabled(false)}
            className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white/70 px-2 py-1 text-[10px] text-slate-400 transition hover:text-slate-700 dark:border-slate-800 dark:bg-slate-950/70 dark:hover:text-slate-200"
          >
            <EyeOff className="h-3 w-3" />
            <span>隠す</span>
          </button>
        </div>
      </div>
    </div>
  );
}