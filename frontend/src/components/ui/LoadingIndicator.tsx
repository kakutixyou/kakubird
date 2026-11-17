// frontend/src/components/ui/LoadingIndicator.tsx
import React, { useEffect, useMemo, useState } from "react";
import { cn } from "../../utils/cn";

// ==========================================
// 1. 型定義 (Types)
// ==========================================

export type LoadingVariant =
  | "dots"      // 標準: ●●● + テキスト
  | "typing"    // 吹き出し内の●●●（LLMタイピング風）
  | "shimmer"   // テキストが光って流れる
  | "wave"      // 音声波形風のバー
  | "spinner"   // スピナー + テキスト
  | "skeleton"  // 返答ウィジェットの骨組み
  | "messages"  // 状況テキストが自動で入れ替わる
  | "steps";    // 段階チェックリスト（OCRやビルド向き）

/**
 * バックエンド (routes_chat, routes_memory, routes_system, KnowledgeManager,
 * ocr_service, VideoClaimService, ScrapingHandler) の処理内容と1対1で対応するコンテキスト型
 */
export type LoadingContextType =
  | "default"
  | "niche_column"   // マニアックなコラム・専門知識の深掘り（キノコ・歴史・科学など）
  | "knowledge"      // KnowledgeManager (index.json / LazyKnowledge / .meta.json / 1行監査)
  | "ocr_grading"    // ocr_service: 解答用紙の四隅マーカー補正＆自動採点
  | "ocr_character"  // ocr_service: 5大構造特徴（閉ループ・交差数・ゾーン密度）抽出・図解OCR
  | "sql"            // routes_sql / CustomSqlOrchestrator
  | "css"            // routes_css: Tailwind / CSS 生成
  | "job_eval"       // routes_system: /evaluate-job 求人票OCR審査
  | "value_eval"     // routes_memory: /values/evaluate トロッコ問題・原発・DC雇用・価値観診断
  | "video_claim"    // VideoClaimService: YouTube字幕取得・誤字補正・造語曲解析
  | "scraping_rag"   // ScrapingHandler: Web記事本文＆OGP・図解画像抽出・ChromaDB登録
  | "workspace_zip"  // routes_memory / routes_project: ZIP展開・チャンク化・RAG登録
  | "project_build"  // KnowledgeManager.materialize_blueprint / ZIP生成
  | "security"       // マルウェア解析・仮想Ubuntuラボ・C2遮断ルール生成
  | "agent"          // AgentOrchestrator
  | "copilot";       // CopilotOrchestrator

export interface LoadingIndicatorProps {
  /** 表示スタイルの種類（省略時は contextType や promptHint から自動選択） */
  variant?: LoadingVariant;
  /** バックエンドの処理種別（指定すると専用の進行メッセージになります） */
  contextType?: LoadingContextType;
  /** 直前のユーザー入力や検索トピック（例: "ベニテングタケの毒について"）を渡すとマニアック演出に自動変化 */
  promptHint?: string;
  /** メインラベルの上書き */
  label?: string;
  /** messages / steps 用のカスタム文言リスト（指定時はプリセットより優先） */
  messages?: string[];
  /** steps 用: 現在の段階(0始まり)。省略すると時間で自動的に進む */
  stage?: number;
  /** 経過秒数を表示するかどうか */
  showElapsed?: boolean;
  /** この秒数を超えたら遅延フォロー文を出す（無効化は Infinity） */
  slowAfterSec?: number;
  /** ローディング中に控えめな文脈連動[PR]カードを表示するか（既定: true） */
  showContextualAd?: boolean;
  /** 何秒経過したら[PR]カードを表示するか（既定: 3秒） */
  adAfterSec?: number;
  className?: string;
}

interface ContextPreset {
  icon: string;
  defaultVariant: LoadingVariant;
  label: string;
  steps: string[];
}

interface InlineAdItem {
  badge: string;
  categoryLabel: string;
  title: string;
  description: string;
  url: string;
  imageUrl?: string;
}

const STORAGE_KEY_AD_ENABLED = "to_studio_contextual_ad_enabled";

// ==========================================
// 2. バックエンド連携プリセット定義
// ==========================================

const CONTEXT_PRESETS: Record<LoadingContextType, ContextPreset> = {
  default: {
    icon: "🤖",
    defaultVariant: "messages",
    label: "AIが思考中...",
    steps: [
      "ユーザーの意図（IntentInspector）を解析しています",
      "関連するコンテキストと記憶（Memory）を照合中",
      "最適な回答とUIブロックを構築しています",
    ],
  },
  niche_column: {
    icon: "🍄",
    defaultVariant: "messages",
    label: "マニアックな専門コラムを調査中...",
    steps: [
      "マニアックな専門文献・知識インデックスを深掘りしています",
      "分類・特徴・珍しいトリビアを抽出しています",
      "図鑑・コラム風の解説データを編成しています",
    ],
  },
  knowledge: {
    icon: "📚",
    defaultVariant: "messages",
    label: "Knowledgeベースを検索・監査中...",
    steps: [
      "KnowledgeRouter で関連ドメインのスコアを計算中",
      "index.json と既出・被りJSONの有無を高速照合中",
      "LazyKnowledge から必要な知識データのみを遅延ロード中",
    ],
  },
  ocr_grading: {
    icon: "📝",
    defaultVariant: "steps",
    label: "解答用紙を構造特徴OCRで自動採点中...",
    steps: [
      "四隅マーカー(■)を検出し、斜め撮影の台形歪みを射影補正中",
      "局所背景除算で照明の影と消しゴムの消し残りを除去中",
      "ミリ単位座標 (xMM/yMM) から解答枠を切り出し・文字分割中",
      "5大構造特徴（穴の数・線分比・交差数）で模範解答と照合中",
    ],
  },
  ocr_character: {
    icon: "🔍",
    defaultVariant: "steps",
    label: "図解・文字の構造特徴OCRを解析中...",
    steps: [
      "画像・図解の解像度と傾き（スラント）を自動解析中",
      "閉ループ（穴）の数と骨格トポロジー（端点・交差点）を計測中",
      "抽出テキストを CodeChunker で分割し VectorStore へ登録中",
    ],
  },
  sql: {
    icon: "🗄️",
    defaultVariant: "messages",
    label: "SQLクエリとスキーマを解析中...",
    steps: [
      "sqlite_master からテーブル構造とスキーマを安全に検証中",
      "SQLインジェクション対策を適用してクエリを組み立て中",
      "データ取得結果とプレビューを生成しています",
    ],
  },
  css: {
    icon: "🎨",
    defaultVariant: "shimmer",
    label: "Tailwind CSS & スタイル定義を生成しています...",
    steps: [
      "デザインプロンプトからカラートークンを解析中",
      "Tailwind クラスとカスタムCSSルールを生成中",
    ],
  },
  job_eval: {
    icon: "📊",
    defaultVariant: "steps",
    label: "求人データを審査・スコアリング中...",
    steps: [
      "OCRテキストから企業名・給与・勤務地・条件を構造化中",
      "求人評価プラグインでグレードと懸念点を算出中",
      "JsonViewerBlock 審査レポートを作成しています",
    ],
  },
  value_eval: {
    icon: "🧭",
    defaultVariant: "steps",
    label: "価値観＆判断軸の一貫性をクロス診断中...",
    steps: [
      "功利主義・義務論・決断力・共感・リスク管理の6軸スコアを集計中",
      "トロッコ問題と実務判断（原発・DC雇用・納期）の矛盾を機械検出中",
      "DecisionPolicy で行動方針を採択し学習ノートへ記録中",
    ],
  },
  video_claim: {
    icon: "🎬",
    defaultVariant: "steps",
    label: "YouTube動画の字幕・造語曲を解析中...",
    steps: [
      "youtube-transcript-api で字幕とタイムスタンプを取得中",
      "TranscriptCleaner で専門用語の誤変換・同音異義語を文脈補正中",
      "ConlangLexicon で造語の意味とテーマ・主張(claims)を抽出中",
    ],
  },
  scraping_rag: {
    icon: "🌐",
    defaultVariant: "steps",
    label: "Web記事の本文と図解画像を抽出・記憶中...",
    steps: [
      "Webページから本文と OGP・記事内図解画像URLを抽出中",
      "CodeChunker でテキストを分割しノイズを除去中",
      "EmbeddingService でベクトル化し ChromaDB へ記憶定着中",
    ],
  },
  workspace_zip: {
    icon: "📦",
    defaultVariant: "steps",
    label: "ワークスペースZIPを展開・記憶へ定着中...",
    steps: [
      "ZIPアーカイブの安全性検証と一時展開を実行中",
      "WorkspaceScanner でソースコード構造とホットスポットを走査中",
      "CodeChunker でチャンク分割し VectorStore へ登録中",
    ],
  },
  project_build: {
    icon: "⚡",
    defaultVariant: "steps",
    label: "プロジェクトのブループリントを展開中...",
    steps: [
      "テンプレート (blueprint_files) の構成を解決中",
      "コードを出力しダウンロード用ZIPアーカイブをパッケージング中",
    ],
  },
  security: {
    icon: "🛡️",
    defaultVariant: "steps",
    label: "通信ログとマルウェア挙動を解析中...",
    steps: [
      "不審なC2通信先IPとPEヘッダ・ペイロードをスキャン中",
      "仮想Ubuntuラボ状態とファイアウォール遮断ルールを合成中",
    ],
  },
  agent: {
    icon: "🧠",
    defaultVariant: "steps",
    label: "自律エージェントがタスクを実行中...",
    steps: [
      "目標をサブタスクに分解し実行計画を立案中",
      "必要なローカルツールとKnowledgeを選択・実行中",
      "実行結果を検証して最終応答を統合中",
    ],
  },
  copilot: {
    icon: "⌨️",
    defaultVariant: "messages",
    label: "コードを解析・生成中...",
    steps: [
      "アクティブなファイルとAST構造を解析しています",
      "型安全性と整合性を保ったコードパッチを生成中",
    ],
  },
};

// ローディング待機中（3秒経過後）に透明度60%で表示される文脈連動[PR]カタログ
const INLINE_AD_CATALOG: Partial<Record<LoadingContextType, InlineAdItem>> = {
  value_eval: {
    badge: "PR / 書籍・討論",
    categoryLabel: "倫理・エネルギー3E+S",
    title: "『これからの「正義」の話をしよう ／ エネルギーと地域共生の経済学』",
    description: "トロッコ問題から原発・データセンター排熱活用まで、合意形成を深める必読書",
    url: "https://example.com/pr/ethics-and-energy-books",
    imageUrl: "https://images.unsplash.com/photo-1473341304170-971dccb5ac1e?w=120&auto=format&fit=crop&q=80",
  },
  security: {
    badge: "PR / 専門書",
    categoryLabel: "マルウェア解析・防衛",
    title: "『実践マルウェア解析 ＆ リバースエンジニアリング入門』",
    description: "仮想Ubuntuラボ構築、PE表層解析、INetSimによるC2通信捕捉を学べる教本",
    url: "https://example.com/pr/malware-analysis-book",
    imageUrl: "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=120&auto=format&fit=crop&q=80",
  },
  niche_column: {
    badge: "PR / 図鑑・史料",
    categoryLabel: "専門コラム・フィールド図鑑",
    title: "『ビジュアル日本史料 ＆ 菌類・自然科学フィールド図鑑』",
    description: "一次史料やキノコ・鉱物・生物の構造特徴を美しい写真で深掘りできる専門図鑑",
    url: "https://example.com/pr/niche-encyclopedia",
    imageUrl: "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=120&auto=format&fit=crop&q=80",
  },
  ocr_grading: {
    badge: "PR / 機材・OCR",
    categoryLabel: "自動採点・スキャナー",
    title: "ドキュメントスキャナー ＆ 構造特徴OCRアルゴリズム実践ガイド",
    description: "答案の台形補正やミリ単位の枠切り出し精度を高める周辺機器と画像処理ノウハウ",
    url: "https://example.com/pr/ocr-scanner-tools",
  },
  ocr_character: {
    badge: "PR / 文字解析",
    categoryLabel: "図解OCR・フォント設計",
    title: "『文字骨格トポロジーとオリジナルフォント制作入門』",
    description: "閉ループ・交差数・ストローク密度解析からTTF/WOFF2出力までを学ぶガイド",
    url: "https://example.com/pr/font-topology-guide",
  },
  video_claim: {
    badge: "PR / 音響・動画",
    categoryLabel: "字幕解析・DTM造語楽曲",
    title: "『音響音声学（IPA）と架空言語ソング制作・字幕自動化ガイド』",
    description: "YouTube字幕解析やフォルマント・ピッチ分離、造語辞書の作り方を徹底解説",
    url: "https://example.com/pr/conlang-video-guide",
  },
  scraping_rag: {
    badge: "PR / AI設計",
    categoryLabel: "RAG・ChromaDB・知識構造化",
    title: "『PythonによるWebスクレイピング ＆ ハイブリッドRAG構築実践入門』",
    description: "BeautifulSoupでの図解抽出からベクトル検索・KnowledgeRouter連携までの定石",
    url: "https://example.com/pr/rag-scraping-book",
  },
  default: {
    badge: "PR / 開発応援",
    categoryLabel: "Green AI・省電力開発",
    title: "ローカルAI ＆ 省電力開発環境ガイド（KnowledgeRouter × 軽量モデル）",
    description: "GPU代とデータセンターの電力負荷を抑えるハイブリッドAI設計ノウハウ",
    url: "https://example.com/pr/green-ai-architecture",
  },
};

// ==========================================
// 3. ユーザー入力から演出を自動推論するヘルパー
// ==========================================

export function inferLoadingContextFromPrompt(
  prompt?: string,
  explicitContext?: LoadingContextType,
): { context: LoadingContextType; customTopic?: string; customSteps?: string[] } {
  if (explicitContext && explicitContext !== "default") {
    return { context: explicitContext };
  }
  const text = (prompt || "").trim();
  if (!text) {
    return { context: "default" };
  }

  // 1. キノコ・菌類などのマニアックなテーマ判定
  const mushroomMatch = text.match(
    /(キノコ|きのこ|茸|菌類|ベニテングタケ|タマゴタケ|ドクツルタケ|マツタケ|エリンギ|シイタケ|マイタケ|なめこ|トリュフ|冬虫夏草|胞子|菌糸)/,
  );
  if (mushroomMatch) {
    const word = mushroomMatch[1];
    return {
      context: "niche_column",
      customTopic: word,
      customSteps: [
        `「${word}」に関するマニアックな菌類図鑑・コラムを調べています`,
        "傘・柄の構造特徴や毒性・食用価値・見分け方を照合中",
        "深掘りトリビアと解説テキストを編成しています",
      ],
    };
  }

  // 2. 日本史・世界史・古文・科学などのマニアックなコラム判定
  const nicheTopicMatch = text.match(
    /(歴史|古文|天皇|ムガル|アクバル|卑弥呼|聖武|孝謙|淳仁|阿部比羅夫|契沖|ラクスマン|レザノフ|量子|相対性理論|素数|トポロジー|古生物|深海魚|鉱物|雑学|コラム|トリビア)/,
  );
  if (nicheTopicMatch) {
    const word = nicheTopicMatch[1];
    return {
      context: "niche_column",
      customTopic: word,
      customSteps: [
        `「${word}」に関するマニアックな史料・専門コラムを検索中`,
        "背景知識や時代考証・関連エピソードを掘り起こしています",
        "わかりやすい解説コラムへと構造化しています",
      ],
    };
  }

  // 3. バックエンドの各機能に対応するキーワード判定
  if (/(youtube\.com|youtu\.be|字幕|文字起こし|造語|conlang|動画メモ)/i.test(text)) {
    return { context: "video_claim" };
  }
  if (/(スクレイピング|http:\/\/|https:\/\/.*(記憶|読ん|覚え|学習|インプット))/i.test(text)) {
    return { context: "scraping_rag" };
  }
  if (/(解答用紙|採点|丸つけ|答案|配点|模範解答)/.test(text)) {
    return { context: "ocr_grading" };
  }
  if (/(OCR|文字認識|手書き|画像解析|スクショ|図解)/.test(text)) {
    return { context: "ocr_character" };
  }
  if (/(トロッコ|価値観|倫理|面接診断|一貫性|原発|データセンター|地域雇用|雪うなぎ)/.test(text)) {
    return { context: "value_eval" };
  }
  if (/(求人|募集要項|年収|企業評価)/.test(text)) {
    return { context: "job_eval" };
  }
  if (/(1行|一行|被りJSON|既出JSON|いらないJSON|重複JSON|ジャンルを絞って)/i.test(text)) {
    return { context: "knowledge" };
  }
  if (/(SQL|データベース|テーブル|SELECT|sqlite|スキーマ)/i.test(text)) {
    return { context: "sql" };
  }
  if (/(CSS|Tailwind|スタイル|配色|UIデザイン)/i.test(text)) {
    return { context: "css" };
  }
  if (/(マルウェア|セキュリティ|C2|DoS|脆弱性|WAF|pefile|inetsim|表層解析)/i.test(text)) {
    return { context: "security" };
  }
  if (/(ZIP|ワークスペース|一括生成|テンプレート展開|ブループリント)/i.test(text)) {
    return { context: "project_build" };
  }
  if (/(Unity|Blender|React|TypeScript|FastAPI|Python|実装|コード|バグ|エラー)/i.test(text)) {
    return { context: "copilot" };
  }

  return { context: "default" };
}

// ==========================================
// 4. アニメーション用 Keyframes & Hooks
// ==========================================

const KEYFRAMES = `
@keyframes to-wave { 0%,100% { transform: scaleY(.3); } 50% { transform: scaleY(1); } }
@keyframes to-shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
@media (prefers-reduced-motion: reduce) { .to-anim { animation: none !important; } }
`;

function useElapsedSeconds(): number {
  const [sec, setSec] = useState<number>(0);
  useEffect(() => {
    const id = window.setInterval(() => setSec((s) => s + 1), 1000);
    return () => window.clearInterval(id);
  }, []);
  return sec;
}

function useTicker(length: number, intervalMs: number, loop: boolean): number {
  const [index, setIndex] = useState<number>(0);
  useEffect(() => {
    setIndex(0);
    if (length <= 1) return;
    const id = window.setInterval(() => {
      setIndex((i) => (loop ? (i + 1) % length : Math.min(i + 1, length - 1)));
    }, intervalMs);
    return () => window.clearInterval(id);
  }, [length, intervalMs, loop]);
  return index;
}

function useAdPreference(): [boolean, (next: boolean) => void] {
  const [enabled, setEnabled] = useState<boolean>(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY_AD_ENABLED);
      return saved === null ? true : saved === "true";
    } catch {
      return true;
    }
  });

  useEffect(() => {
    const handleCustom = (e: Event) => {
      const custom = e as CustomEvent<boolean>;
      if (typeof custom.detail === "boolean") setEnabled(custom.detail);
    };
    window.addEventListener("to-ad-pref-change", handleCustom);
    return () => window.removeEventListener("to-ad-pref-change", handleCustom);
  }, []);

  const update = (next: boolean) => {
    setEnabled(next);
    try {
      window.localStorage.setItem(STORAGE_KEY_AD_ENABLED, String(next));
      window.dispatchEvent(new CustomEvent("to-ad-pref-change", { detail: next }));
    } catch {}
  };

  return [enabled, update];
}

// ==========================================
// 5. サブパーツ (Sub-components)
// ==========================================

function BounceDots(): React.ReactElement {
  return (
    <span aria-hidden className="flex items-center gap-1">
      {[0, 0.2, 0.4].map((d) => (
        <span
          key={d}
          className="to-anim animate-bounce text-indigo-500 dark:text-indigo-400"
          style={{ animationDelay: `${d}s` }}
        >
          ●
        </span>
      ))}
    </span>
  );
}

function Spinner(): React.ReactElement {
  return (
    <span
      aria-hidden
      className="to-anim inline-block h-3.5 w-3.5 shrink-0 animate-spin rounded-full border-2 border-slate-200 border-t-indigo-500 dark:border-slate-700 dark:border-t-indigo-400"
    />
  );
}

function Wave(): React.ReactElement {
  return (
    <span aria-hidden className="flex h-4 items-center gap-0.5">
      {[0, 0.15, 0.3, 0.45, 0.6].map((d) => (
        <span
          key={d}
          className="to-anim block h-4 w-[3px] rounded-full bg-indigo-500 dark:bg-indigo-400"
          style={{ animation: "to-wave 1s ease-in-out infinite", animationDelay: `${d}s` }}
        />
      ))}
    </span>
  );
}

function ShimmerText({ children }: { children: React.ReactNode }): React.ReactElement {
  return (
    <span
      className="to-anim font-medium"
      style={{
        backgroundImage: "linear-gradient(90deg, #64748b 0%, #e2e8f0 50%, #64748b 100%)",
        backgroundSize: "200% 100%",
        WebkitBackgroundClip: "text",
        backgroundClip: "text",
        color: "transparent",
        animation: "to-shimmer 2.2s linear infinite",
      }}
    >
      {children}
    </span>
  );
}

// ==========================================
// 6. メインコンポーネント (LoadingIndicator)
// ==========================================

export function LoadingIndicator({
  variant,
  contextType = "default",
  promptHint,
  label,
  messages,
  stage,
  showElapsed = false,
  slowAfterSec = 15,
  showContextualAd = true,
  adAfterSec = 3,
  className,
}: LoadingIndicatorProps): React.ReactElement {
  const elapsed = useElapsedSeconds();
  const [adEnabled, setAdEnabled] = useAdPreference();
  const [adImgBroken, setAdImgBroken] = useState(false);

  // プロンプトまたは指定された contextType からプリセットを解決
  const resolved = useMemo(
    () => inferLoadingContextFromPrompt(promptHint, contextType),
    [promptHint, contextType],
  );

  const preset = CONTEXT_PRESETS[resolved.context] || CONTEXT_PRESETS.default;
  const activeVariant: LoadingVariant = variant ?? preset.defaultVariant;
  const activeLabel = label ?? preset.label;

  const list = useMemo(() => {
    if (messages && messages.length > 0) return messages;
    if (resolved.customSteps && resolved.customSteps.length > 0) return resolved.customSteps;
    return preset.steps;
  }, [messages, resolved.customSteps, preset.steps]);

  const tick = useTicker(
    list.length,
    activeVariant === "steps" ? 2200 : 2500,
    activeVariant === "messages",
  );

  const current =
    typeof stage === "number" ? Math.max(0, Math.min(stage, list.length - 1)) : tick;

  const adItem: InlineAdItem =
    INLINE_AD_CATALOG[resolved.context] || INLINE_AD_CATALOG.default!;

  let body: React.ReactNode;

  switch (activeVariant) {
    case "typing":
      body = (
        <div className="inline-flex items-center gap-2 rounded-2xl rounded-bl-none border border-slate-100 bg-white px-4 py-3 text-xs shadow-sm dark:border-slate-700/60 dark:bg-slate-800">
          <span>{preset.icon}</span>
          <BounceDots />
        </div>
      );
      break;

    case "shimmer":
      body = (
        <span className="flex items-center gap-2">
          <span>{preset.icon}</span>
          <ShimmerText>{activeLabel}</ShimmerText>
        </span>
      );
      break;

    case "wave":
      body = (
        <span className="flex items-center gap-2">
          <Wave />
          <span className="text-slate-600 dark:text-slate-300">{activeLabel}</span>
        </span>
      );
      break;

    case "spinner":
      body = (
        <span className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
          <Spinner />
          <span>{preset.icon}</span>
          <span>{activeLabel}</span>
        </span>
      );
      break;

    case "skeleton":
      body = (
        <div className="w-full max-w-sm space-y-2.5 rounded-2xl rounded-bl-none border border-slate-100 bg-white p-4 shadow-sm dark:border-slate-700/60 dark:bg-slate-800">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span>{preset.icon}</span>
            <span>{activeLabel}</span>
          </div>
          {["w-11/12", "w-full", "w-2/3"].map((w, i) => (
            <div
              key={`${w}-${i}`}
              className={cn(
                "to-anim h-2.5 animate-pulse rounded bg-slate-200 dark:bg-slate-700",
                w,
              )}
            />
          ))}
        </div>
      );
      break;

    case "messages":
      body = (
        <div className="inline-flex items-center gap-2.5 rounded-xl border border-slate-200/80 bg-slate-50/90 px-3.5 py-2 text-xs text-slate-700 shadow-sm dark:border-slate-800 dark:bg-slate-900/70 dark:text-slate-300">
          <Spinner />
          <span>{preset.icon}</span>
          <span key={current} className="font-medium">
            {list[current]}…
          </span>
        </div>
      );
      break;

    case "steps":
      body = (
        <div className="w-full max-w-md rounded-xl border border-slate-200 bg-slate-50/90 p-3.5 shadow-sm dark:border-slate-800 dark:bg-slate-900/60">
          <div className="mb-2 flex items-center gap-2 border-b border-slate-200/70 pb-2 text-xs font-semibold text-slate-700 dark:border-slate-800 dark:text-slate-200">
            <span>{preset.icon}</span>
            <span>{activeLabel}</span>
          </div>
          <ol className="space-y-1.5">
            {list.map((text, i) => {
              const done = i < current;
              const active = i === current;
              return (
                <li
                  key={`${i}-${text}`}
                  className={cn(
                    "flex items-center gap-2 text-xs transition-colors duration-300",
                    done
                      ? "text-emerald-600 dark:text-emerald-400"
                      : active
                        ? "font-medium text-slate-900 dark:text-slate-100"
                        : "text-slate-400 dark:text-slate-600",
                  )}
                >
                  {done ? (
                    <span
                      aria-hidden
                      className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-[10px] text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400"
                    >
                      ✓
                    </span>
                  ) : active ? (
                    <Spinner />
                  ) : (
                    <span
                      aria-hidden
                      className="flex h-4 w-4 shrink-0 items-center justify-center text-center"
                    >
                      ・
                    </span>
                  )}
                  <span>
                    {text}
                    {active ? "…" : ""}
                  </span>
                </li>
              );
            })}
          </ol>
        </div>
      );
      break;

    case "dots":
    default:
      body = (
        <span className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
          <BounceDots />
          <span>{preset.icon}</span>
          <span>{activeLabel}</span>
        </span>
      );
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn("flex flex-col items-start gap-1.5 py-2 text-xs text-slate-400", className)}
    >
      <style>{KEYFRAMES}</style>
      {body}

      {(showElapsed || elapsed >= slowAfterSec) && (
        <div className="flex flex-wrap items-center gap-2 px-1 text-[11px]">
          {showElapsed && (
            <span className="tabular-nums text-slate-400 dark:text-slate-500">
              {elapsed}秒経過
            </span>
          )}
          {elapsed >= slowAfterSec && (
            <span className="text-amber-500 dark:text-amber-400/90">
              ⚠️ ローカルモデルまたは特徴解析の処理に時間がかかっています…
            </span>
          )}
        </div>
      )}

      {/* 🆕 待機時間が adAfterSec (既定3秒) を超えた場合のみ、透明度60%の文脈連動[PR]カードを表示 */}
      {showContextualAd && elapsed >= adAfterSec && adEnabled && (
        <div
          style={{ opacity: 0.6 }}
          className="group mt-1 flex w-full max-w-md items-center justify-between gap-2.5 rounded-xl border border-dashed border-slate-300/80 bg-slate-50/60 p-2.5 text-[11px] text-slate-600 transition-opacity duration-200 hover:!opacity-100 dark:border-slate-800 dark:bg-slate-900/50 dark:text-slate-300"
        >
          {adItem.imageUrl && !adImgBroken && (
            <img
              src={adItem.imageUrl}
              alt={adItem.title}
              onError={() => setAdImgBroken(true)}
              className="h-10 w-10 shrink-0 rounded-lg object-cover border border-slate-200 dark:border-slate-800"
              loading="lazy"
            />
          )}
          <a
            href={adItem.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 min-w-0 space-y-0.5"
          >
            <div className="flex items-center gap-1.5">
              <span className="rounded bg-slate-200 px-1.5 py-0.5 text-[9px] font-bold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                {adItem.badge}
              </span>
              <span className="text-[10px] font-medium text-indigo-500 dark:text-indigo-400 truncate">
                {adItem.categoryLabel}
              </span>
            </div>
            <div className="font-semibold text-slate-800 group-hover:underline dark:text-slate-200 truncate">
              {adItem.title} ↗
            </div>
            <p className="text-[10px] text-slate-400 truncate">
              {adItem.description}
            </p>
          </a>
          <button
            type="button"
            onClick={() => setAdEnabled(false)}
            className="shrink-0 rounded px-1.5 py-1 text-[10px] text-slate-400 hover:bg-slate-200/60 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            title="[PR]表示をオフにする"
          >
            隠す
          </button>
        </div>
      )}
    </div>
  );
}

export default LoadingIndicator;