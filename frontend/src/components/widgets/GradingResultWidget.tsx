// frontend/src/components/widgets/GradingResultWidget.tsx
// 先生の採点支援・一斉確認＆ワンクリック修正ウィジェット
// - 採点の厳しさ3段階切り替え（厳格 / 標準 / 優しめ）
// - 条件付き救済ルール設定（例: 30点以下なら△や惜しい解答を自動救済、生徒ごとの個別「優しめ」指定）
// - AI確信度フィルタ（すべて / 要確認のみ / 30点以下救済対象 / 未承認のみ）
// - 10人ずつページング表示 ＆ 全員一斉表示切り替え
// - 設問ごとの ○ / △ / × ワンクリック変更・点数微調整・高確信度の一括承認

import React, { useMemo, useState } from "react";

// ==========================================
// 1. 型定義
// ==========================================

export type StrictnessLevel = "strict" | "standard" | "lenient";
export type ConfidenceLevel = "high" | "medium" | "low";
export type MarkSymbol = "correct" | "partial" | "incorrect";

export interface GradedAnswerItem {
  question_id: string;
  number: number;
  question_text: string;
  student_answer: string;
  model_answer: string;
  mark: MarkSymbol;
  awarded_points: number;
  max_points: number;
  confidence: ConfidenceLevel;
  reason: string;
  lenient_boosted?: boolean;
}

export interface StudentSubmission {
  submission_id: string;
  session_id: string;
  student_id: string;
  student_name: string;
  seat_number: number;
  applied_strictness: StrictnessLevel;
  raw_score: number;
  final_score: number;
  max_score: number;
  rescue_applied: boolean;
  rescue_bonus: number;
  overall_confidence: ConfidenceLevel;
  needs_review: boolean;
  teacher_approved: boolean;
  answers: GradedAnswerItem[];
  ocr_raw_text?: string;
  source_device?: string;
}

export interface GradingSessionData {
  session_id: string;
  title: string;
  strictness: StrictnessLevel;
  rescue_threshold: number;
  rescue_enabled: boolean;
  batch_size: number;
  student_overrides: Record<string, StrictnessLevel>;
  submissions: StudentSubmission[];
  stats?: {
    total_students: number;
    approved_count: number;
    needs_review_count: number;
    rescued_count: number;
    average_score: number;
  };
}

export interface GradingResultWidgetProps {
  initialData?: Partial<GradingSessionData>;
  apiBaseUrl?: string;
  onOptionSelect?: (payload: Record<string, unknown>) => void;
}

// ==========================================
// 2. デモ用初期データ（バックエンド未接続時も即座にプレビュー可能）
// ==========================================

const FALLBACK_SESSION_DATA: GradingSessionData = {
  session_id: "session_default_1a",
  title: "日本史・古典 記述小テスト（1年A組）",
  strictness: "standard",
  rescue_threshold: 30,
  rescue_enabled: true,
  batch_size: 10,
  student_overrides: { S04: "lenient" },
  submissions: [
    {
      submission_id: "sub_session_default_1a_S01",
      session_id: "session_default_1a",
      student_id: "S01",
      student_name: "佐藤 陽葵",
      seat_number: 1,
      applied_strictness: "standard",
      raw_score: 100,
      final_score: 100,
      max_score: 100,
      rescue_applied: false,
      rescue_bonus: 0,
      overall_confidence: "high",
      needs_review: false,
      teacher_approved: true,
      answers: [
        {
          question_id: "Q1",
          number: 1,
          question_text: "753年に来日し唐招提寺を創建した僧侶",
          student_answer: "鑑真",
          model_answer: "鑑真",
          mark: "correct",
          awarded_points: 25,
          max_points: 25,
          confidence: "high",
          reason: "模範解答と完全一致",
        },
        {
          question_id: "Q2",
          number: 2,
          question_text: "1792年に根室へ来航したロシア使節",
          student_answer: "ラクスマン",
          model_answer: "ラクスマン",
          mark: "correct",
          awarded_points: 25,
          max_points: 25,
          confidence: "high",
          reason: "模範解答と完全一致",
        },
        {
          question_id: "Q3",
          number: 3,
          question_text: "「咲かず」の「ず」の助動詞と活用形",
          student_answer: "打消の助動詞・終止形",
          model_answer: "打消の助動詞「ず」の終止形",
          mark: "correct",
          awarded_points: 25,
          max_points: 25,
          confidence: "high",
          reason: "模範解答と一致",
        },
        {
          question_id: "Q4",
          number: 4,
          question_text: "五・一五事件で暗殺された首相",
          student_answer: "犬養毅",
          model_answer: "犬養毅",
          mark: "correct",
          awarded_points: 25,
          max_points: 25,
          confidence: "high",
          reason: "模範解答と完全一致",
        },
      ],
    },
    {
      submission_id: "sub_session_default_1a_S03",
      session_id: "session_default_1a",
      student_id: "S03",
      student_name: "高橋 結衣",
      seat_number: 3,
      applied_strictness: "standard",
      raw_score: 67,
      final_score: 67,
      max_score: 100,
      rescue_applied: false,
      rescue_bonus: 0,
      overall_confidence: "medium",
      needs_review: true,
      teacher_approved: false,
      answers: [
        {
          question_id: "Q1",
          number: 1,
          question_text: "753年に来日し唐招提寺を創建した僧侶",
          student_answer: "鑑真和上",
          model_answer: "鑑真",
          mark: "correct",
          awarded_points: 25,
          max_points: 25,
          confidence: "high",
          reason: "許容解答と一致",
        },
        {
          question_id: "Q2",
          number: 2,
          question_text: "1792年に根室へ来航したロシア使節",
          student_answer: "ラスクマン",
          model_answer: "ラクスマン",
          mark: "partial",
          awarded_points: 12,
          max_points: 25,
          confidence: "low",
          reason: "1文字転置（ラスクマン）のため部分点・先生確認推奨",
        },
        {
          question_id: "Q3",
          number: 3,
          question_text: "「咲かず」の「ず」の助動詞と活用形",
          student_answer: "打消",
          model_answer: "打消の助動詞「ず」の終止形",
          mark: "partial",
          awarded_points: 15,
          max_points: 25,
          confidence: "medium",
          reason: "助動詞の意味は正解、活用形が未記入",
        },
        {
          question_id: "Q4",
          number: 4,
          question_text: "五・一五事件で暗殺された首相",
          student_answer: "犬養",
          model_answer: "犬養毅",
          mark: "partial",
          awarded_points: 15,
          max_points: 25,
          confidence: "medium",
          reason: "名字のみ一致（下の名前が未記入）",
        },
      ],
    },
    {
      submission_id: "sub_session_default_1a_S04",
      session_id: "session_default_1a",
      student_id: "S04",
      student_name: "田中 颯太",
      seat_number: 4,
      applied_strictness: "lenient",
      raw_score: 27,
      final_score: 38,
      max_score: 100,
      rescue_applied: true,
      rescue_bonus: 11,
      overall_confidence: "low",
      needs_review: true,
      teacher_approved: false,
      answers: [
        {
          question_id: "Q1",
          number: 1,
          question_text: "753年に来日し唐招提寺を創建した僧侶",
          student_answer: "唐招提寺をつくった人",
          model_answer: "鑑真",
          mark: "partial",
          awarded_points: 17,
          max_points: 25,
          confidence: "low",
          reason: "優しめ＋30点以下救済 (+5点): 関連キーワードを評価",
          lenient_boosted: true,
        },
        {
          question_id: "Q2",
          number: 2,
          question_text: "1792年に根室へ来航したロシア使節",
          student_answer: "レザノフ",
          model_answer: "ラクスマン",
          mark: "partial",
          awarded_points: 3,
          max_points: 25,
          confidence: "low",
          reason: "1804年長崎来航の使節と混同（※30点以下救済 +3点）",
          lenient_boosted: true,
        },
        {
          question_id: "Q3",
          number: 3,
          question_text: "「咲かず」の「ず」の助動詞と活用形",
          student_answer: "",
          model_answer: "打消の助動詞「ず」の終止形",
          mark: "incorrect",
          awarded_points: 0,
          max_points: 25,
          confidence: "high",
          reason: "未記入（空欄）",
        },
        {
          question_id: "Q4",
          number: 4,
          question_text: "五・一五事件で暗殺された首相",
          student_answer: "話せばわかるの人",
          model_answer: "犬養毅",
          mark: "partial",
          awarded_points: 18,
          max_points: 25,
          confidence: "low",
          reason: "優しめ＋30点以下救済 (+3点): エピソード理解を評価",
          lenient_boosted: true,
        },
      ],
    },
  ],
};

// ==========================================
// 3. 補助バッジコンポーネント
// ==========================================

function ConfidenceBadge({ level }: { level: ConfidenceLevel }): React.ReactElement {
  const styles: Record<ConfidenceLevel, { label: string; cls: string }> = {
    high: {
      label: "確信度: 高",
      cls: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800",
    },
    medium: {
      label: "確信度: 中",
      cls: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800",
    },
    low: {
      label: "要先生確認",
      cls: "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/50 dark:text-rose-300 dark:border-rose-800 font-bold",
    },
  };
  const target = styles[level] || styles.medium;
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs ${target.cls}`}>
      {target.label}
    </span>
  );
}

function StrictnessBadge({ level }: { level: StrictnessLevel }): React.ReactElement {
  const map: Record<StrictnessLevel, { text: string; cls: string }> = {
    strict: {
      text: "厳格",
      cls: "bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700",
    },
    standard: {
      text: "標準",
      cls: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800",
    },
    lenient: {
      text: "優しめ適用",
      cls: "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/40 dark:text-purple-300 dark:border-purple-800 font-semibold",
    },
  };
  const item = map[level] || map.standard;
  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] ${item.cls}`}>
      {item.text}
    </span>
  );
}

// ==========================================
// 4. メインコンポーネント
// ==========================================

export default function GradingResultWidget({
  initialData,
  apiBaseUrl = "",
  onOptionSelect,
}: GradingResultWidgetProps): React.ReactElement {
  const [session, setSession] = useState<GradingSessionData>(() => ({
    ...FALLBACK_SESSION_DATA,
    ...initialData,
    submissions:
      Array.isArray(initialData?.submissions) && initialData.submissions.length > 0
        ? initialData.submissions
        : FALLBACK_SESSION_DATA.submissions,
  }));

  const [filterMode, setFilterMode] = useState<"all" | "needs_review" | "rescued" | "unapproved">("all");
  const [batchViewMode, setBatchViewMode] = useState<"batch_10" | "all">("batch_10");
  const [pageIndex, setPageIndex] = useState<number>(0);
  const [expandedStudentIds, setExpandedStudentIds] = useState<Record<string, boolean>>({
    S03: true,
    S04: true,
  });
  const [isBusy, setIsBusy] = useState<boolean>(false);

  // API通信ヘルパー（バックエンド接続時は実APIを叩き、オフラインでもローカルStateを即座に更新）
  const callGradingApi = async (endpoint: string, body: Record<string, unknown>) => {
    onOptionSelect?.({ action: endpoint, ...body });
    if (!apiBaseUrl) return null;
    try {
      setIsBusy(true);
      const res = await fetch(`${apiBaseUrl.replace(/\/+$/, "")}/api/grading/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        const json = await res.json();
        if (json?.content?.submissions) {
          setSession(json.content);
        }
        return json;
      }
    } catch (err) {
      console.warn("Grading API fallback to local state:", err);
    } finally {
      setIsBusy(false);
    }
    return null;
  };

  // --- A. 全体の採点厳しさ（3段階）または30点以下救済条件の変更 ---
  const handleGlobalRuleChange = async (
    nextStrictness: StrictnessLevel,
    nextRescueEnabled: boolean,
    nextThreshold: number
  ) => {
    setSession((prev) => ({
      ...prev,
      strictness: nextStrictness,
      rescue_enabled: nextRescueEnabled,
      rescue_threshold: nextThreshold,
    }));

    await callGradingApi("batch", {
      session_id: session.session_id,
      mode: batchViewMode,
      offset: pageIndex * 10,
      strictness: nextStrictness,
      rescue_enabled: nextRescueEnabled,
      rescue_threshold: nextThreshold,
      student_overrides: session.student_overrides,
    });
  };

  // --- B. 生徒ごとの個別「優しめ / 標準 / 厳格」切り替え ---
  const handleStudentStrictnessChange = async (submission: StudentSubmission, level: StrictnessLevel) => {
    setSession((prev) => {
      const nextOverrides = { ...prev.student_overrides, [submission.student_id]: level };
      const nextSubs = prev.submissions.map((sub) => {
        if (sub.submission_id !== submission.submission_id) return sub;
        // ローカル即時プレビュー用に優しめ変更時は△を底上げ
        const updatedAnswers = sub.answers.map((ans) => {
          if (level === "lenient" && ans.mark === "partial") {
            return {
              ...ans,
              awarded_points: ans.max_points,
              mark: "correct" as MarkSymbol,
              reason: "個別「優しめ」指定により○へ繰り上げ",
              lenient_boosted: true,
            };
          }
          return ans;
        });
        const newFinal = updatedAnswers.reduce((acc, a) => acc + a.awarded_points, 0);
        return {
          ...sub,
          applied_strictness: level,
          answers: updatedAnswers,
          final_score: newFinal,
        };
      });
      return { ...prev, student_overrides: nextOverrides, submissions: nextSubs };
    });

    await callGradingApi("override", {
      session_id: session.session_id,
      submission_id: submission.submission_id,
      student_strictness: level,
    });
  };

  // --- C. 先生による設問ごとの ○ / △ / × または点数のワンクリック修正 ---
  const handleAnswerOverride = async (
    submissionId: string,
    questionId: string,
    newMark: MarkSymbol,
    explicitPoints?: number
  ) => {
    setSession((prev) => ({
      ...prev,
      submissions: prev.submissions.map((sub) => {
        if (sub.submission_id !== submissionId) return sub;
        const nextAnswers = sub.answers.map((ans) => {
          if (ans.question_id !== questionId) return ans;
          const pts =
            explicitPoints !== undefined
              ? Math.max(0, Math.min(ans.max_points, explicitPoints))
              : newMark === "correct"
              ? ans.max_points
              : newMark === "incorrect"
              ? 0
              : Math.floor(ans.max_points / 2);
          return {
            ...ans,
            mark: newMark,
            awarded_points: pts,
            confidence: "high" as ConfidenceLevel,
            reason: "先生が手動で確認・修正済み",
          };
        });
        const nextScore = nextAnswers.reduce((sum, a) => sum + a.awarded_points, 0);
        const stillNeedsReview = nextAnswers.some((a) => a.confidence === "low");
        return {
          ...sub,
          answers: nextAnswers,
          final_score: nextScore,
          needs_review: stillNeedsReview,
        };
      }),
    }));

    await callGradingApi("override", {
      session_id: session.session_id,
      submission_id: submissionId,
      question_id: questionId,
      new_mark: newMark,
      new_points: explicitPoints,
    });
  };

  // --- D. 生徒1人の採点確定トグル ＆ 高確信度の一括確定 ---
  const handleApproveStudent = async (submissionId: string, approved: boolean) => {
    setSession((prev) => ({
      ...prev,
      submissions: prev.submissions.map((sub) =>
        sub.submission_id === submissionId
          ? { ...sub, teacher_approved: approved, needs_review: approved ? false : sub.needs_review }
          : sub
      ),
    }));

    await callGradingApi("override", {
      session_id: session.session_id,
      submission_id: submissionId,
      approve_submission: approved,
    });
  };

  const handleBulkApproveHighConfidence = async () => {
    setSession((prev) => ({
      ...prev,
      submissions: prev.submissions.map((sub) =>
        sub.overall_confidence === "high"
          ? { ...sub, teacher_approved: true, needs_review: false }
          : sub
      ),
    }));
    await callGradingApi("bulk-approve", {
      session_id: session.session_id,
      include_medium: false,
    });
  };

  // --- フィルタリングと10人ごとページング計算 ---
  const filteredSubmissions = useMemo(() => {
    return session.submissions.filter((sub) => {
      if (filterMode === "needs_review") return sub.needs_review || sub.overall_confidence === "low";
      if (filterMode === "rescued") return sub.rescue_applied || sub.raw_score <= session.rescue_threshold;
      if (filterMode === "unapproved") return !sub.teacher_approved;
      return true;
    });
  }, [session.submissions, filterMode, session.rescue_threshold]);

  const pageSize = batchViewMode === "batch_10" ? 10 : Math.max(1, filteredSubmissions.length);
  const totalPages = Math.max(1, Math.ceil(filteredSubmissions.length / pageSize));
  const currentSlice = useMemo(() => {
    if (batchViewMode === "all") return filteredSubmissions;
    const start = pageIndex * 10;
    return filteredSubmissions.slice(start, start + 10);
  }, [filteredSubmissions, batchViewMode, pageIndex]);

  // 統計サマリー算出
  const stats = useMemo(() => {
    const total = session.submissions.length;
    const approved = session.submissions.filter((s) => s.teacher_approved).length;
    const review = session.submissions.filter((s) => (s.needs_review || s.overall_confidence === "low") && !s.teacher_approved).length;
    const rescued = session.submissions.filter((s) => s.rescue_applied).length;
    const avg = total > 0 ? (session.submissions.reduce((acc, s) => acc + s.final_score, 0) / total).toFixed(1) : "0.0";
    return { total, approved, review, rescued, avg };
  }, [session.submissions]);

  return (
    <div className="w-full space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      {/* 1. ヘッダー & 統計サマリーバー */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg">📝</span>
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
              {session.title}
            </h3>
            {isBusy && (
              <span className="rounded bg-indigo-50 px-2 py-0.5 text-xs text-indigo-600 dark:bg-indigo-950 dark:text-indigo-300">
                自作AI通信中...
              </span>
            )}
          </div>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            AIが下採点し、確信度が低い解答や30点以下の救済対象だけを先生が素早く確認・修正できます
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className="rounded-lg bg-slate-50 px-3 py-1.5 dark:bg-slate-800">
            <span className="text-slate-500 dark:text-slate-400">平均点: </span>
            <span className="font-bold text-slate-900 dark:text-white">{stats.avg}点</span>
          </div>
          <div className="rounded-lg bg-rose-50 px-3 py-1.5 dark:bg-rose-950/40">
            <span className="text-rose-600 dark:text-rose-300">要確認: </span>
            <span className="font-bold text-rose-700 dark:text-rose-200">{stats.review}名</span>
          </div>
          <div className="rounded-lg bg-purple-50 px-3 py-1.5 dark:bg-purple-950/40">
            <span className="text-purple-600 dark:text-purple-300">救済適用: </span>
            <span className="font-bold text-purple-700 dark:text-purple-200">{stats.rescued}名</span>
          </div>
          <div className="rounded-lg bg-emerald-50 px-3 py-1.5 dark:bg-emerald-950/40">
            <span className="text-emerald-600 dark:text-emerald-300">確定済: </span>
            <span className="font-bold text-emerald-700 dark:text-emerald-200">
              {stats.approved}/{stats.total}名
            </span>
          </div>
        </div>
      </div>

      {/* 2. コントロールパネル（厳しさ3段階・30点以下救済ルール・一斉採点単位） */}
      <div className="grid grid-cols-1 gap-3 rounded-xl bg-slate-50 p-3.5 dark:bg-slate-800/60 md:grid-cols-3">
        {/* (1) 厳しさ3段階 */}
        <div className="space-y-1.5">
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
            ① 全体の採点基準（3段階）
          </label>
          <div className="grid grid-cols-3 gap-1 rounded-lg bg-slate-200/70 p-1 dark:bg-slate-900">
            {(
              [
                { id: "strict", label: "厳格" },
                { id: "standard", label: "標準" },
                { id: "lenient", label: "優しめ" },
              ] as const
            ).map((tab) => {
              const active = session.strictness === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() =>
                    handleGlobalRuleChange(tab.id, session.rescue_enabled, session.rescue_threshold)
                  }
                  className={`rounded-md py-1.5 text-xs font-semibold transition ${
                    active
                      ? "bg-white text-indigo-600 shadow-sm dark:bg-slate-800 dark:text-indigo-300"
                      : "text-slate-600 hover:text-slate-900 dark:text-slate-400"
                  }`}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            {session.strictness === "lenient"
              ? "ひらがな・言い換え表現も意図が合っていれば○にします"
              : session.strictness === "strict"
              ? "漢字・送り仮名まで模範解答との完全一致を求めます"
              : "意味一致で正解、要素不足は自動で部分点（△）にします"}
          </p>
        </div>

        {/* (2) 条件付き救済ルール（30点以下など） */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              ② 条件付きの優しめ救済ルール
            </label>
            <input
              type="checkbox"
              checked={session.rescue_enabled}
              onChange={(e) =>
                handleGlobalRuleChange(session.strictness, e.target.checked, session.rescue_threshold)
              }
              className="h-4 w-4 rounded border-slate-300 text-indigo-600"
            />
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 dark:border-slate-700 dark:bg-slate-900">
            <span className="text-xs text-slate-600 dark:text-slate-300">合計</span>
            <input
              type="number"
              min={0}
              max={100}
              step={5}
              value={session.rescue_threshold}
              onChange={(e) =>
                handleGlobalRuleChange(
                  session.strictness,
                  session.rescue_enabled,
                  Number(e.target.value || 0)
                )
              }
              className="w-16 rounded border border-slate-300 px-2 py-0.5 text-center text-xs font-bold text-indigo-600 dark:border-slate-700 dark:bg-slate-800 dark:text-indigo-300"
            />
            <span className="text-xs text-slate-600 dark:text-slate-300">点以下は△・記入解答に加点</span>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            もう少し点数をあげたい生徒の惜しい解答を自動で底上げします
          </p>
        </div>

        {/* (3) 一斉採点モード（10人ずつ / 全員）＆ 一括承認 */}
        <div className="flex flex-col justify-between space-y-1.5">
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
            ③ 一斉採点単位 ＆ 高確信度の一括確定
          </label>
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => {
                setBatchViewMode("batch_10");
                setPageIndex(0);
              }}
              className={`flex-1 rounded-lg border px-2.5 py-1.5 text-xs font-semibold ${
                batchViewMode === "batch_10"
                  ? "border-indigo-600 bg-indigo-600 text-white"
                  : "border-slate-300 bg-white text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
              }`}
            >
              10人ずつ採点
            </button>
            <button
              type="button"
              onClick={() => setBatchViewMode("all")}
              className={`flex-1 rounded-lg border px-2.5 py-1.5 text-xs font-semibold ${
                batchViewMode === "all"
                  ? "border-indigo-600 bg-indigo-600 text-white"
                  : "border-slate-300 bg-white text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
              }`}
            >
              全員一斉 ({session.submissions.length}人)
            </button>
          </div>
          <button
            type="button"
            onClick={handleBulkApproveHighConfidence}
            className="w-full rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-500"
          >
            ✓ 確信度「高」の生徒をまとめて確定
          </button>
        </div>
      </div>

      {/* 3. フィルタタブ & ページネーション */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1.5">
          {(
            [
              { id: "all", label: `すべて (${session.submissions.length})` },
              { id: "needs_review", label: `要確認のみ (${stats.review})` },
              { id: "rescued", label: `${session.rescue_threshold}点以下・救済 (${stats.rescued})` },
              { id: "unapproved", label: `未確定 (${ stats.total - stats.approved })` },
            ] as const
          ).map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => {
                setFilterMode(f.id);
                setPageIndex(0);
              }}
              className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                filterMode === f.id
                  ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {batchViewMode === "batch_10" && totalPages > 1 && (
          <div className="flex items-center gap-2 text-xs">
            <button
              type="button"
              disabled={pageIndex === 0}
              onClick={() => setPageIndex((p) => Math.max(0, p - 1))}
              className="rounded border border-slate-300 px-2.5 py-1 disabled:opacity-40 dark:border-slate-700"
            >
              ← 前の10人
            </button>
            <span className="font-mono text-slate-600 dark:text-slate-400">
              {pageIndex + 1} / {totalPages} バッチ
            </span>
            <button
              type="button"
              disabled={pageIndex >= totalPages - 1}
              onClick={() => setPageIndex((p) => Math.min(totalPages - 1, p + 1))}
              className="rounded border border-slate-300 px-2.5 py-1 disabled:opacity-40 dark:border-slate-700"
            >
              次の10人 →
            </button>
          </div>
        )}
      </div>

      {/* 4. 生徒別採点カード一覧 */}
      <div className="space-y-3">
        {currentSlice.map((sub) => {
          const isExpanded = !!expandedStudentIds[sub.student_id];
          return (
            <div
              key={sub.submission_id}
              className={`rounded-xl border transition ${
                sub.needs_review && !sub.teacher_approved
                  ? "border-rose-300 bg-rose-50/20 dark:border-rose-900/70 dark:bg-rose-950/10"
                  : sub.teacher_approved
                  ? "border-emerald-200 bg-emerald-50/10 dark:border-emerald-900/50"
                  : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
              }`}
            >
              {/* 生徒サマリー行 */}
              <div className="flex flex-wrap items-center justify-between gap-2 p-3">
                <div className="flex flex-wrap items-center gap-2.5">
                  <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-slate-200 text-xs font-bold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                    {sub.seat_number}
                  </span>
                  <span className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    {sub.student_name}
                  </span>
                  <ConfidenceBadge level={sub.overall_confidence} />
                  <StrictnessBadge level={sub.applied_strictness} />
                  {sub.rescue_applied && (
                    <span className="rounded-md bg-purple-100 px-2 py-0.5 text-[11px] font-semibold text-purple-800 dark:bg-purple-950 dark:text-purple-200">
                      救済 +{sub.rescue_bonus}点 (素点 {sub.raw_score}点)
                    </span>
                  )}
                </div>

                {/* 右側：個別厳しさ変更・合計点・確定ボタン */}
                <div className="flex flex-wrap items-center gap-2">
                  <div className="flex items-center gap-1 text-xs">
                    <span className="text-slate-400">個別基準:</span>
                    <select
                      value={sub.applied_strictness}
                      onChange={(e) =>
                        handleStudentStrictnessChange(sub, e.target.value as StrictnessLevel)
                      }
                      className="rounded border border-slate-300 bg-white px-2 py-1 text-xs dark:border-slate-700 dark:bg-slate-800"
                    >
                      <option value="strict">厳格</option>
                      <option value="standard">標準</option>
                      <option value="lenient">優しめ (個別救済)</option>
                    </select>
                  </div>

                  <div className="min-w-[84px] text-right">
                    <span className="text-xl font-extrabold text-indigo-600 dark:text-indigo-400">
                      {sub.final_score}
                    </span>
                    <span className="text-xs text-slate-500"> / {sub.max_score}点</span>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleApproveStudent(sub.submission_id, !sub.teacher_approved)}
                    className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                      sub.teacher_approved
                        ? "bg-emerald-600 text-white"
                        : "border border-slate-300 bg-white text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                    }`}
                  >
                    {sub.teacher_approved ? "✓ 確定済" : "確認OK"}
                  </button>

                  <button
                    type="button"
                    onClick={() =>
                      setExpandedStudentIds((prev) => ({
                        ...prev,
                        [sub.student_id]: !prev[sub.student_id],
                      }))
                    }
                    className="rounded-lg bg-slate-100 px-2.5 py-1.5 text-xs text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300"
                  >
                    {isExpanded ? "▲ 閉じる" : "▼ 解答明細・修正"}
                  </button>
                </div>
              </div>

              {/* 設問ごとの明細 & 先生のワンクリック修正パネル */}
              {isExpanded && (
                <div className="border-t border-slate-100 bg-slate-50/60 p-3 dark:border-slate-800 dark:bg-slate-950/40">
                  <div className="space-y-2">
                    {sub.answers.map((ans) => (
                      <div
                        key={ans.question_id}
                        className="flex flex-col justify-between gap-2 rounded-lg border border-slate-200/80 bg-white p-2.5 text-xs dark:border-slate-800 dark:bg-slate-900 md:flex-row md:items-center"
                      >
                        <div className="space-y-1 md:max-w-[58%]">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-700 dark:text-slate-200">
                              問{ans.number}. {ans.question_text}
                            </span>
                            <ConfidenceBadge level={ans.confidence} />
                          </div>
                          <div className="flex flex-wrap gap-3 text-xs">
                            <span>
                              <strong className="text-slate-500">生徒解答:</strong>{" "}
                              <span className="rounded bg-amber-50 px-1.5 py-0.5 font-mono font-semibold text-slate-900 dark:bg-amber-950/40 dark:text-amber-200">
                                {ans.student_answer || "（空欄）"}
                              </span>
                            </span>
                            <span>
                              <strong className="text-slate-500">模範解答:</strong>{" "}
                              <span className="text-slate-700 dark:text-slate-300">
                                {ans.model_answer}
                              </span>
                            </span>
                          </div>
                          <div className="text-[11px] text-slate-500 dark:text-slate-400">
                            💬 AI判定理由: {ans.reason}
                          </div>
                        </div>

                        {/* 先生のワンクリック ○ / △ / × 修正 ＆ 点数入力 */}
                        <div className="flex items-center gap-2 self-end md:self-center">
                          <div className="inline-flex rounded-lg border border-slate-200 p-0.5 dark:border-slate-700">
                            {(
                              [
                                { mark: "correct", symbol: "○ 正解", activeCls: "bg-emerald-600 text-white" },
                                { mark: "partial", symbol: "△ 部分点", activeCls: "bg-amber-500 text-white" },
                                { mark: "incorrect", symbol: "× 不正解", activeCls: "bg-rose-600 text-white" },
                              ] as const
                            ).map((btn) => (
                              <button
                                key={btn.mark}
                                type="button"
                                onClick={() =>
                                  handleAnswerOverride(sub.submission_id, ans.question_id, btn.mark)
                                }
                                className={`rounded-md px-2.5 py-1 text-xs font-bold transition ${
                                  ans.mark === btn.mark
                                    ? btn.activeCls
                                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                                }`}
                              >
                                {btn.symbol}
                              </button>
                            ))}
                          </div>

                          <div className="flex items-center gap-1">
                            <input
                              type="number"
                              min={0}
                              max={ans.max_points}
                              value={ans.awarded_points}
                              onChange={(e) =>
                                handleAnswerOverride(
                                  sub.submission_id,
                                  ans.question_id,
                                  ans.mark,
                                  Number(e.target.value || 0)
                                )
                              }
                              className="w-14 rounded border border-slate-300 px-1.5 py-1 text-right font-mono text-xs font-bold dark:border-slate-700 dark:bg-slate-800"
                            />
                            <span className="text-slate-400">/ {ans.max_points}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}