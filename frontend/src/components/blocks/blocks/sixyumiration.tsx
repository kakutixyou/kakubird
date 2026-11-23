// frontend/src/components/blocks/sixyumiration.tsx
import React, { useMemo, useState } from "react";
import {
  ShieldAlert,
  ExternalLink,
  Sparkles,
  Heart,
  Trophy,
  RotateCcw,
  Image as ImageIcon,
  Palette,
  CheckCircle2,
  XCircle,
} from "lucide-react";

export interface ProtectedReferenceImage {
  url: string;
  caption?: string;
  source_url?: string;
  source_domain?: string;
  copyright_label?: string;
}

export interface AtmosphereTheme {
  id: string;
  label: string;
  accent?: string;
  bg_gradient?: string;
}

export interface SimulationQuestion {
  id: string;
  prompt: string;
  choices: string[];
  answer_index: number;
  explanation?: string;
}

export interface SixyumirationPayload {
  title?: string;
  source_url?: string;
  source_domain?: string;
  copyright_notice?: string;
  atmosphere?: AtmosphereTheme;
  available_atmospheres?: AtmosphereTheme[];
  images?: ProtectedReferenceImage[];
  questions?: SimulationQuestion[];
  initial_hp?: number;
  data?: SixyumirationPayload;
}

export interface SixyumirationProps {
  title?: string;
  data?: SixyumirationPayload | Record<string, any>;
  onOptionSelect?: (payload: unknown) => void;
}

const DEFAULT_THEMES: AtmosphereTheme[] = [
  {
    id: "academic_quest",
    label: "📘 青い宝箱・探究モード",
    bg_gradient: "from-slate-950 via-blue-950 to-indigo-950",
  },
  {
    id: "cyber_security",
    label: "🛡️ サイバー防衛ラボ",
    bg_gradient: "from-slate-950 via-cyan-950 to-slate-900",
  },
  {
    id: "history_scroll",
    label: "🏯 歴史絵巻フィールド",
    bg_gradient: "from-stone-950 via-amber-950 to-stone-900",
  },
  {
    id: "culinary_science",
    label: "🍳 料理科学キッチン",
    bg_gradient: "from-zinc-950 via-rose-950 to-stone-900",
  },
];

export function SixyumirationBlock({
  title,
  data,
  onOptionSelect,
}: SixyumirationProps): React.ReactElement {
  const raw = (data ?? {}) as SixyumirationPayload;
  const payload: SixyumirationPayload =
    raw.questions || raw.source_url || raw.atmosphere
      ? raw
      : (raw.data ?? raw);

  const themes =
    Array.isArray(payload.available_atmospheres) &&
    payload.available_atmospheres.length > 0
      ? payload.available_atmospheres
      : DEFAULT_THEMES;

  const [selectedThemeId, setSelectedThemeId] = useState<string>(
    payload.atmosphere?.id || themes[0].id
  );
  const [stepIndex, setStepIndex] = useState<number>(0);
  const [selectedChoice, setSelectedChoice] = useState<number | null>(null);
  const [hp, setHp] = useState<number>(payload.initial_hp ?? 100);
  const [score, setScore] = useState<number>(0);
  const [brokenImages, setBrokenImages] = useState<Record<string, boolean>>({});

  const activeTheme = useMemo(
    () => themes.find((t) => t.id === selectedThemeId) || themes[0],
    [themes, selectedThemeId]
  );

  const questions: SimulationQuestion[] = Array.isArray(payload.questions)
    ? payload.questions
    : [];
  const images: ProtectedReferenceImage[] = Array.isArray(payload.images)
    ? payload.images.filter((img) => img?.url && !brokenImages[img.url])
    : [];

  const currentQuestion = questions[stepIndex];
  const isFinished = questions.length > 0 && stepIndex >= questions.length;
  const isGameOver = hp <= 0;

  const handleSelectChoice = (idx: number) => {
    if (selectedChoice !== null || !currentQuestion) return;
    setSelectedChoice(idx);

    const isCorrect = idx === currentQuestion.answer_index;
    if (isCorrect) {
      setScore((s) => s + 250);
    } else {
      setHp((h) => Math.max(0, h - 30));
    }

    onOptionSelect?.({
      action: "sixyumiration_answer",
      question_id: currentQuestion.id,
      is_correct: isCorrect,
      theme: activeTheme.id,
    });
  };

  const handleNext = () => {
    setSelectedChoice(null);
    setStepIndex((i) => i + 1);
  };

  const handleReset = () => {
    setStepIndex(0);
    setSelectedChoice(null);
    setHp(payload.initial_hp ?? 100);
    setScore(0);
  };

  return (
    <div
      className={`my-3 rounded-2xl border border-sky-500/40 bg-gradient-to-br ${
        activeTheme.bg_gradient || "from-slate-950 via-blue-950 to-indigo-950"
      } p-4 text-slate-100 shadow-xl space-y-4 transition-colors duration-500`}
    >
      {/* 1. ヘッダー ＆ HP・スコアステータス */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-3">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2 text-xs font-bold text-sky-300">
            <Sparkles className="w-4 h-4" />
            <span>SIXYUMIRATION ENGINE — 学習知識シミュレーション</span>
          </div>
          <h3 className="text-base font-extrabold text-white">
            {title || payload.title || "学習データ連動ゲーム"}
          </h3>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 rounded-lg border border-rose-500/40 bg-rose-950/50 px-2.5 py-1 text-xs font-bold text-rose-200">
            <Heart className="w-3.5 h-3.5 text-rose-400 fill-rose-400" />
            <span>HP {hp}</span>
          </div>
          <div className="flex items-center gap-1.5 rounded-lg border border-amber-500/40 bg-amber-950/50 px-2.5 py-1 text-xs font-bold text-amber-200">
            <Trophy className="w-3.5 h-3.5 text-amber-400" />
            <span>{score} pt</span>
          </div>
        </div>
      </div>

      {/* 2. 雰囲気（テーマ）切り替えバー */}
      <div className="flex flex-wrap items-center gap-1.5 rounded-xl border border-white/10 bg-black/30 p-2">
        <span className="inline-flex items-center gap-1 px-2 text-[11px] font-bold text-slate-300">
          <Palette className="w-3.5 h-3.5 text-sky-400" />
          <span>雰囲気切替:</span>
        </span>
        {themes.map((t) => {
          const active = t.id === activeTheme.id;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setSelectedThemeId(t.id)}
              className={`rounded-lg px-2.5 py-1 text-[11px] font-semibold transition ${
                active
                  ? "bg-sky-500 text-slate-950 shadow"
                  : "bg-white/5 text-slate-300 hover:bg-white/15"
              }`}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      {/* 3. 著作権保護 ＆ 出典明示バナー */}
      <div className="rounded-xl border border-amber-400/40 bg-amber-950/35 p-2.5 text-xs text-amber-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-start gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">【著作権保護・出典明示】</span>{" "}
            <span>
              {payload.copyright_notice ||
                "表示されている画像・引用テキストの著作権は各出典元の権利者に帰属します。"}
            </span>
          </div>
        </div>
        {payload.source_url && (
          <a
            href={payload.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 shrink-0 rounded-lg border border-amber-400/40 bg-black/40 px-2.5 py-1 text-[11px] font-semibold text-amber-200 hover:bg-black/60"
          >
            <span>出典元を開く</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>

      {/* 4. 著作権保護ラベル付き参照画像ギャラリー */}
      {images.length > 0 && (
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5 text-[11px] font-bold text-slate-300">
            <ImageIcon className="w-3.5 h-3.5 text-sky-400" />
            <span>参照ビジュアル（著作権保護対象・引用プレビュー）</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            {images.slice(0, 3).map((img, i) => (
              <div
                key={`${img.url}-${i}`}
                className="overflow-hidden rounded-xl border border-white/15 bg-black/50 flex flex-col justify-between"
              >
                <div className="relative h-28 w-full bg-slate-900 flex items-center justify-center">
                  <img
                    src={img.url}
                    alt={img.caption || `参照画像 ${i + 1}`}
                    referrerPolicy="no-referrer"
                    onError={() =>
                      setBrokenImages((prev) => ({ ...prev, [img.url]: true }))
                    }
                    className="h-full w-full object-contain p-1.5"
                  />
                  <span className="absolute bottom-1 left-1 right-1 rounded bg-black/75 px-1.5 py-0.5 text-[9px] text-amber-200 truncate">
                    {img.copyright_label ||
                      `© ${img.source_domain || "出典元"}（著作権保護）`}
                  </span>
                </div>
                <div className="px-2 py-1.5 text-[10px] text-slate-300 truncate">
                  {img.caption || "引用図解"}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 5. シミュレーション＆クイズ本編 */}
      {questions.length === 0 ? (
        <div className="rounded-xl border border-white/10 bg-black/30 p-4 text-xs text-slate-300">
          先にURLを「記憶して」「要約して」と読み込ませてから、シミュレーションを開始してください。
        </div>
      ) : isFinished || isGameOver ? (
        <div className="rounded-xl border border-sky-400/40 bg-black/40 p-4 text-center space-y-3">
          <div className="text-lg font-extrabold text-white">
            {isGameOver
              ? "💥 シミュレーション中断（HPが0になりました）"
              : "🎉 シミュレーション完了！"}
          </div>
          <p className="text-xs text-slate-300">
            最終スコア: <span className="font-bold text-amber-300">{score} pt</span> ／
            残りHP: <span className="font-bold text-rose-300">{hp}</span>
          </p>
          <button
            type="button"
            onClick={handleReset}
            className="inline-flex items-center gap-1.5 rounded-lg bg-sky-500 px-4 py-1.5 text-xs font-bold text-slate-950 hover:bg-sky-400 transition"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>もう一度挑戦する</span>
          </button>
        </div>
      ) : (
        <div className="rounded-xl border border-white/15 bg-black/40 p-4 space-y-3">
          <div className="flex items-center justify-between text-[11px] text-slate-400">
            <span>
              フェーズ {stepIndex + 1} / {questions.length}
            </span>
            <span>正解で +250pt / 不正解で HP -30</span>
          </div>

          <p className="text-sm font-bold text-white leading-relaxed">
            {currentQuestion.prompt}
          </p>

          <div className="space-y-2">
            {currentQuestion.choices.map((choice, idx) => {
              const answered = selectedChoice !== null;
              const isCorrect = idx === currentQuestion.answer_index;
              const isPicked = idx === selectedChoice;

              let btnStyle =
                "border-white/15 bg-white/5 hover:bg-white/15 text-slate-100";
              if (answered) {
                if (isCorrect) {
                  btnStyle =
                    "border-emerald-400 bg-emerald-950/60 text-emerald-200";
                } else if (isPicked) {
                  btnStyle = "border-rose-400 bg-rose-950/60 text-rose-200";
                } else {
                  btnStyle = "border-white/10 bg-black/20 text-slate-400";
                }
              }

              return (
                <button
                  key={idx}
                  type="button"
                  disabled={answered}
                  onClick={() => handleSelectChoice(idx)}
                  className={`w-full text-left rounded-xl border px-3 py-2.5 text-xs font-medium transition flex items-center justify-between gap-2 ${btnStyle}`}
                >
                  <span>{choice}</span>
                  {answered && isCorrect && (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  )}
                  {answered && isPicked && !isCorrect && (
                    <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                  )}
                </button>
              );
            })}
          </div>

          {selectedChoice !== null && (
            <div className="pt-2 space-y-2 border-t border-white/10">
              {currentQuestion.explanation && (
                <p className="text-xs text-sky-200 bg-sky-950/40 rounded-lg p-2.5 border border-sky-500/30">
                  💡 {currentQuestion.explanation}
                </p>
              )}
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={handleNext}
                  className="rounded-lg bg-sky-500 px-4 py-1.5 text-xs font-bold text-slate-950 hover:bg-sky-400 transition"
                >
                  {stepIndex + 1 >= questions.length
                    ? "結果を見る →"
                    : "次のフェーズへ →"}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default SixyumirationBlock;