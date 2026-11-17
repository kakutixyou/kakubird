// frontend/src/components/widgets/ToAiStudioDashboard.tsx
import React, { useState, useEffect, useMemo } from "react";
import {
  Film, ShieldAlert, FileText, Code2, Play, Pause, RotateCcw,
  Music, Copy, Download, Plus, Trash2, CheckCircle2, Scale,
  AlertTriangle, HeartHandshake, Sparkles,
} from "lucide-react";
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip,
} from "recharts";

export type StudioPageType = "video" | "memo" | "security" | "values" | "code";

export interface ToAiStudioDashboardProps {
  initialPage?: StudioPageType;
  initialData?: Record<string, unknown>;
  onOptionSelect?: (data: unknown) => void;
  apiBaseUrl?: string;
}

export interface ValueQuestion {
  id: string;
  category: "trolley" | "interview";
  badge: string;
  title: string;
  question: string;
  options: {
    id: string;
    label: string;
    scores: Record<string, number>;
    tags: string[];
    respect_response?: string;
  }[];
}

// バックエンド未接続時でも動く最小フォールバック（普段はKnowledgeManagerのJSONで上書きされる）
const FALLBACK_QUESTIONS: ValueQuestion[] = [
//   {
//     id: "q_standard_trolley",
//     category: "trolley",
//     badge: "🚃 トロッコ問題（基本原則）",
//     title: "5人の救済と1人の犠牲",
//     question: "暴走トロッコの先に5人がいます。レバーを引けば5人は助かりますが、引き込み線の1人が犠牲になります。",
//     options: [
//       {
//         id: "pull",
//         label: "レバーを引く（全体の被害最小化を優先しつつ、1人への責任も自覚する）",
//         scores: { utilitarianism: 20, decisiveness: 15 },
//         tags: ["utilitarian_choice"],
//         respect_response: "「より多くの命を救いたい」という結果への責任感に基づく判断です。引かない派の「1人の人権も侵すべきでない」という原則論にも敬意を払うことで対話が成立します。",
//       },
//       {
//         id: "not_pull",
//         label: "引かない（無関係な1人を自らの手で危険に晒す一線は越えない）",
//         scores: { deontology: 20, empathy_safety: 15 },
//         tags: ["strict_deontology", "never_use_as_means"],
//         respect_response: "「人を救うためであっても無関係な誰かを犠牲にする権利はない」という誠実な規範意識です。引く派の「5人を見殺しにしたくない」という苦渋の想いも理解することが大切です。",
//       },
//     ],
//   },
//   {
//     id: "q_nuclear_empathy",
//     category: "trolley",
//     badge: "⚡ 原発と電力のジレンマ（双方向尊重）",
//     title: "現在の生活・命の保護 vs 未来世代と地域の安全",
//     question: "電力逼迫時、「今の停電・電気代高騰から弱者や産業を守りたい」という願いと、「万が一の事故や核のごみから未来と地域を守りたい」という願い、どちらを軸に対話を始めますか？",
//     options: [
//       {
//         id: "empathize_current_stability",
//         label: "「今の生活と命を守る安定供給」を軸にしつつ、慎重派が懸念する安全・最終処分への責任も重く受け止める",
//         scores: { utilitarianism: 15, risk_management: 15, empathy_safety: 10 },
//         tags: ["respect_stability", "acknowledge_safety_concern"],
//         respect_response: "推進・再稼働派の「現在の国民生活を守る」という善意と、慎重派の「取り返しのつかないリスクを防ぐ」という善意の双方を肯定し、安全基準の透明化と次世代電源への移行期間として議論する協調スタンスです。",
//       },
//       {
//         id: "empathize_future_safety",
//         label: "「未来世代と地域の安全原則」を軸にしつつ、推進派が懸念する電力不足・経済負担への代替案も一緒に考える",
//         scores: { deontology: 15, empathy_safety: 15, risk_management: 10 },
//         tags: ["respect_safety", "acknowledge_economic_concern"],
//         respect_response: "世代間倫理を守りつつ、「電気代高騰で今苦しむ人や企業をどう支えるか」という相手の懸念にも寄り添い、蓄電池や分散型電源などの現実的な移行策を共に探るスタンスです。",
//       },
//     ],
//   },
//   {
//     id: "q_datacenter_coexistence",
//     category: "interview",
//     badge: "🖥️ AIデータセンターと地域・電力の共生",
//     title": "AIの進化 vs 地域の電力・水資源・環境負荷",
//     question: "AIデータセンター新設に対し「地域の電力や水資源が圧迫される」と心配する住民の方と話すとき、どう向き合いますか？",
//     options: [
//       {
//         id: "co_design_local_benefit",
//         label: "住民の懸念を正当な権利として尊重し、排熱の地域還元や自家発電・省電力AI化をセットで提案する",
//         scores: { empathy_safety: 20, risk_management: 15, decisiveness: 10 },
//         tags: ["coexistence_model", "respect_local_residents"],
//         respect_response: "反対意見を「説得すべき障害」ではなく「設計を良くするパートナーの声」として尊重し、地域還元と省エネ技術で共生を図るアプローチです。",
//       },
//       {
//         id: "force_for_growth",
//         label: "国力と納期のため、住民の懸念や5%の不具合リスクは切り捨てて強行建設・強行リリースする",
//         scores: { utilitarianism: 25, empathy_safety: -25, deontology: -15 },
//         tags: ["skip_test_for_deadline", "ignore_local_concern"],
//         respect_response: "スピードは出ますが、切り捨てられた側の強い反発を招き、長期的な信頼や安全性を損なうリスクがあります。",
//       },
//     ],
//   },
];

export default function ToAiStudioDashboard({
  initialPage = "values",
  onOptionSelect,
  apiBaseUrl = "",
}: ToAiStudioDashboardProps) {
  const [activePage, setActivePage] = useState<StudioPageType>(initialPage);
  const [toast, setToast] = useState<string | null>(null);

  // KnowledgeManager からフォルダー単位で拾ってきたデータのステート
  const [questions, setQuestions] = useState<ValueQuestion[]>(FALLBACK_QUESTIONS);
  const [conlangDict, setConlangDict] = useState<Record<string, string>>({
    kora: "光・暁", miel: "祈り・響き", saluva: "解き放つ", aeterna: "永遠の螺旋",
  });
  const [codeSnippets, setCodeSnippets] = useState<Record<string, string>>({
    "KnowledgeManager連携": "# GET /api/to/studio/bundle で knowledge/ 配下のJSONを自動収集します",
  });

  // 1. マウント時に KnowledgeManager のバンドルAPIからJSONを一括取得
  useEffect(() => {
    const base = apiBaseUrl.replace(/\/+$/, "");
    fetch(`${base}/api/to/studio/bundle`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (Array.isArray(d?.questions) && d.questions.length > 0) {
          setQuestions(d.questions);
        }
        if (Array.isArray(d?.code_snippets) && d.code_snippets.length > 0) {
          const map: Record<string, string> = {};
          d.code_snippets.forEach((s: any) => {
            if (s.title && s.code) map[s.title] = s.code;
          });
          if (Object.keys(map).length > 0) setCodeSnippets(map);
        }
      })
      .catch(() => {});
  }, [apiBaseUrl]);

  const notify = (msg: string, payload?: Record<string, unknown>) => {
    setToast(msg);
    if (payload) onOptionSelect?.(payload);
    setTimeout(() => setToast(null), 3000);
  };

  // --- Video / Memo / Security 用の軽量ステート ---
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [memoText, setMemoText] = useState(
    "前の職場では月100時間の残業と12連勤で睡眠4時間の日が続き大変だったが、今は相手の立場を尊重できる健全なAI開発を目指している。"
  );
  const [memoComments, setMemoComments] = useState([
    { id: "c1", author: "振り返り", text: "過酷な経験があるからこそ、少数派や現場へのしわ寄せに敏感になれる。" },
  ]);
  const [newComment, setNewComment] = useState("");
  const [malwareInput, setMalwareInput] = useState(
    "!This program cannot be run is DOS mode. 128.91.34.188 keylog.txt SynFlooding"
  );
  const [secApplied, setSecApplied] = useState(false);

  // --- 🧭 Values (トロッコ・原発・データセンター対話) ステート ---
  const [answers, setAnswers] = useState<Record<string, number>>({});

  const valueReport = useMemo(() => {
    const axes = {
      utilitarianism: 50, deontology: 50, decisiveness: 50,
      empathy_safety: 50, risk_management: 50, consistency: 85,
    };
    const tags = new Set<string>();
    const dialogueGuides: string[] = [];

    questions.forEach((q) => {
      const opt = q.options[answers[q.id] ?? 0] || q.options[0];
      if (!opt) return;
      opt.tags?.forEach((t) => tags.add(t));
      if (opt.respect_response) dialogueGuides.push(opt.respect_response);
      Object.entries(opt.scores || {}).forEach(([k, v]) => {
        if (k in axes) {
          axes[k as keyof typeof axes] = Math.max(0, Math.min(100, axes[k as keyof typeof axes] + v));
        }
      });
    });

    const contradictions: string[] = [];
    const strengths: string[] = [];

    if (
      (tags.has("never_use_as_means") || tags.has("respect_safety")) &&
      tags.has("skip_test_for_deadline")
    ) {
      contradictions.push(
        "【原則と実務の乖離】トロッコ・原発問題では「少数や未来への安全・人権」を重視していますが、データセンター・開発判断では「納期や成長のために住民や5%のユーザーを切り捨てる」選択をしており、相手を尊重する軸にブレが生じています。"
      );
    }

    if (contradictions.length === 0) {
      strengths.push(
        "【相手尊重・双方向対話の一貫性◎】自分の軸を持ちながらも、反対側の立場（安定供給を求める側／安全・環境を求める側）の背景にある善意や懸念を尊重して折衷案を探る姿勢が一貫しています。"
      );
    }

    axes.consistency = Math.max(20, axes.consistency - contradictions.length * 30);

    return {
      axes,
      contradictions,
      strengths,
      dialogueGuides,
      radarData: [
        { subject: "功利・現実解", value: axes.utilitarianism },
        { subject: "規範・安全原則", value: axes.deontology },
        { subject: "決断・推進力", value: axes.decisiveness },
        { subject: "共感・相手尊重", value: axes.empathy_safety },
        { subject: "リスク管理", value: axes.risk_management },
        { subject: "論理の一貫性", value: axes.consistency },
      ],
    };
  }, [questions, answers]);

  const TABS: { id: StudioPageType; label: string; sub: string; icon: any }[] = [
    { id: "video", label: "🎬 動画・造語曲", sub: "話者・タイムバー", icon: Film },
    { id: "memo", label: "📝 体験談メモ", sub: "NLU・コメントJSON", icon: FileText },
    { id: "security", label: "🛡️ マルウェア防御", sub: "HEX・C2遮断", icon: ShieldAlert },
    { id: "values", label: "🧭 価値観＆協調討論", sub: "トロッコ・原発・DC", icon: Scale },
    { id: "code", label: "💻 Knowledge連携", sub: "JSON自動収集構造", icon: Code2 },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-6 font-sans">
      {toast && (
        <div className="fixed bottom-5 right-5 z-50 bg-indigo-950 border border-indigo-500 px-4 py-2.5 rounded-xl text-xs flex items-center gap-2 shadow-xl">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{toast}</span>
        </div>
      )}

      {/* 5タブ・ナビゲーション */}
      <nav className="max-w-7xl mx-auto mb-6 grid grid-cols-2 lg:grid-cols-5 gap-2.5">
        {TABS.map((t) => {
          const Icon = t.icon;
          const active = activePage === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActivePage(t.id)}
              className={`p-3 rounded-xl border text-left transition ${
                active
                  ? "bg-indigo-950/80 border-indigo-500 ring-2 ring-indigo-500/30"
                  : "bg-slate-900/70 border-slate-800 hover:bg-slate-900"
              }`}
            >
              <div className="text-xs font-bold text-white flex items-center gap-1.5">
                <Icon className="w-3.5 h-3.5 text-indigo-400" />
                {t.label}
              </div>
              <div className="text-[11px] text-slate-400 mt-0.5">{t.sub}</div>
            </button>
          );
        })}
      </nav>

      {/* PAGE: VALUES (トロッコ問題・原発・データセンター協調対話スタジオ) */}
      {activePage === "values" && (
        <main className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* 左カラム: KnowledgeManager から読み込まれた質問リスト */}
          <div className="lg:col-span-7 space-y-3">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-amber-300 flex items-center gap-2">
                  <HeartHandshake className="w-4 h-4" />
                  相手を尊重するトロッコ問題・原発・AIデータセンター対話
                </h2>
                <p className="text-[11px] text-slate-400">
                  knowledge/ethics_trolley/ 内のJSONから質問と対話ガイドを動的に読み込んでいます
                </p>
              </div>
            </div>

            {questions.map((q) => {
              const sel = answers[q.id] ?? 0;
              return (
                <div key={q.id} className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] bg-amber-950/80 border border-amber-700/50 text-amber-300 px-2 py-0.5 rounded">
                      {q.badge}
                    </span>
                    <span className="text-xs font-bold text-slate-200">{q.title}</span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">{q.question}</p>
                  <div className="space-y-1.5">
                    {q.options.map((opt, idx) => (
                      <button
                        key={opt.id}
                        onClick={() => setAnswers((p) => ({ ...p, [q.id]: idx }))}
                        className={`w-full text-left rounded-lg px-3 py-2 text-xs border transition ${
                          sel === idx
                            ? "bg-amber-600/25 border-amber-500 text-white font-semibold"
                            : "bg-slate-950 border-slate-800 text-slate-400 hover:bg-slate-800"
                        }`}
                      >
                        {sel === idx ? "● " : "○ "}
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {/* 右カラム: レーダーチャート ＋ 相手を尊重する対話ファシリテーションガイド */}
          <div className="lg:col-span-5 space-y-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <div className="flex justify-between items-center mb-2 text-xs">
                <span className="font-bold text-slate-200">📊 6軸価値観＆対話バランス</span>
                <span className="text-amber-400 font-bold">
                  一貫性: {valueReport.axes.consistency} / 100
                </span>
              </div>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={valueReport.radarData}>
                    <PolarGrid stroke="#334155" />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: "#cbd5e1", fontSize: 11 }} />
                    <PolarRadiusAxis domain={[0, 100]} tick={false} />
                    <Radar dataKey="value" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.4} />
                    <Tooltip contentStyle={{ backgroundColor: "#0f172a", fontSize: "12px" }} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* 矛盾検知 */}
            {valueReport.contradictions.map((c, i) => (
              <div key={i} className="bg-rose-950/40 border border-rose-800 rounded-xl p-3 text-xs text-rose-200">
                <div className="font-bold text-rose-400 flex items-center gap-1 mb-1">
                  <AlertTriangle className="w-3.5 h-3.5" /> 機械的に検出された矛盾点
                </div>
                {c}
              </div>
            ))}

            {/* しっかりしている点 */}
            {valueReport.strengths.map((s, i) => (
              <div key={i} className="bg-emerald-950/30 border border-emerald-800/70 rounded-xl p-3 text-xs text-emerald-200">
                <div className="font-bold text-emerald-400 mb-1">✨ 一貫している強み</div>
                {s}
              </div>
            ))}

            {/* 相手の意見を尊重する対話ガイド（原発・データセンター討論用） */}
            <div className="bg-indigo-950/40 border border-indigo-800/80 rounded-xl p-3.5 text-xs space-y-2">
              <div className="font-bold text-indigo-300 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" />
                相手の意見を尊重する対話・ファシリテーション指針
              </div>
              {valueReport.dialogueGuides.map((g, i) => (
                <p key={i} className="text-slate-300 leading-relaxed border-l-2 border-indigo-500 pl-2.5">
                  {g}
                </p>
              ))}
            </div>
          </div>
        </main>
      )}

      {/* PAGE: VIDEO */}
      {activePage === "video" && (
        <main className="max-w-7xl mx-auto bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-sm font-bold flex items-center gap-2">
              <Music className="w-4 h-4 text-pink-400" /> 動画URL・タイムバー＆造語曲辞書スタジオ
            </h2>
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="bg-indigo-600 px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1"
            >
              {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              {currentTime.toFixed(1)}s / 24.0s
            </button>
          </div>
          <input
            type="range" min={0} max={24} step={0.5} value={currentTime}
            onChange={(e) => setCurrentTime(parseFloat(e.target.value))}
            className="w-full accent-indigo-500"
          />
          <div className="flex flex-wrap gap-2 text-xs">
            {Object.entries(conlangDict).map(([k, v]) => (
              <span key={k} className="bg-slate-950 border border-slate-800 px-2.5 py-1 rounded font-mono">
                <b className="text-pink-400">{k}</b> = {v}
              </span>
            ))}
          </div>
        </main>
      )}

      {/* PAGE: MEMO */}
      {activePage === "memo" && (
        <main className="max-w-7xl mx-auto bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-bold text-emerald-400">📝 日本語体験談＆コメントJSON化</h2>
          <textarea
            rows={3} value={memoText} onChange={(e) => setMemoText(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs"
          />
          <div className="flex gap-2">
            <input
              value={newComment} onChange={(e) => setNewComment(e.target.value)}
              placeholder="振り返りコメントを追加..."
              className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs"
            />
            <button
              onClick={() => {
                if (!newComment.trim()) return;
                setMemoComments((p) => [...p, { id: `c_${Date.now()}`, author: "自分", text: newComment }]);
                setNewComment("");
              }}
              className="bg-emerald-600 px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1"
            >
              <Plus className="w-3.5 h-3.5" /> 追加
            </button>
          </div>
        </main>
      )}

      {/* PAGE: SECURITY */}
      {activePage === "security" && (
        <main className="max-w-7xl mx-auto bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-bold text-rose-400">🛡️ マルウェアHEX解析＆防御ルール適用</h2>
          <textarea
            rows={2} value={malwareInput} onChange={(e) => setMalwareInput(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs font-mono text-sky-300"
          />
          <button
            onClick={() => {
              setSecApplied(true);
              notify("C2遮断とkeylog.txtロックを適用しました", { action: "apply_rules" });
            }}
            className="bg-rose-600 px-4 py-2 rounded-lg text-xs font-bold"
          >
            {secApplied ? "✔ 防御ルール適用済" : "SYN Flood遮断 ＆ keylog.txt ロック適用"}
          </button>
        </main>
      )}

      {/* PAGE: CODE */}
      {activePage === "code" && (
        <main className="max-w-7xl mx-auto bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
          <h2 className="text-sm font-bold text-sky-400">💻 KnowledgeManager 連携スニペット</h2>
          {Object.entries(codeSnippets).map(([title, code]) => (
            <pre key={title} className="bg-slate-950 p-3 rounded-lg text-xs font-mono text-emerald-300 overflow-x-auto">
              {code}
            </pre>
          ))}
        </main>
      )}
    </div>
  );
}