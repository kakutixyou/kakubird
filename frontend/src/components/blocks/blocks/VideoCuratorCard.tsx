// VideoCuratorCard.tsx
// AIChatMessageList.tsx の response_type === "video_curator" 用カード。
// バックエンド(VideoAnalyzerTool)が project.json 相当のデータを返せばそれを表示し、
// まだ返ってこない場合は「決定論的ルール」のローカル解析でプレビューする(AI学習前でも動作)。

import React, { useCallback, useMemo, useState } from "react";

// ==========================================
// 1. 型定義
// ==========================================

export interface VideoCaption {
  id: string;
  start: number;
  end: number;
  text: string;
}

export interface VideoCaptionEffect {
  caption_id: string;
  effect: string;
  color: string;
  bgOpacity: number;
  excitement_score: number;
}

export interface VideoClip {
  clip_id: string;
  original_range: [number, number];
  edited_range: [number, number];
  duration: number;
  excitement_score: number;
}

export interface RemovedSilenceRange {
  original_start: number;
  original_end: number;
  duration_removed: number;
  audio_db: number;
  reason: string;
}

export interface VideoProjectMetadata {
  resolution: string;
  fps: number;
  original_duration_sec: number;
  edited_duration_sec: number;
  removed_silence_sec: number;
  silence_cuts_count: number;
  silence_threshold_sec: number;
}

export interface VideoFontConfig {
  headlineFont: string;
  bodyFont: string;
  defaultFontSize: number;
}

export interface VideoProject {
  version: string;
  metadata: VideoProjectMetadata;
  fontConfig: VideoFontConfig;
  shortcuts: Record<string, string>;
  captions: VideoCaption[];
  captionEffects: VideoCaptionEffect[];
  timelineClips: VideoClip[];
  removedSilenceRanges: RemovedSilenceRange[];
  pluginSlots: Record<string, string>;
}

export interface VideoCuratorCardProps {
  /** msg.data (バックエンドの data をそのまま渡す) */
  payload: Record<string, unknown>;
  /** 閾値変更などをバックエンド(本体)へ戻すコールバック */
  onOptionSelect?: (data: unknown) => void;
}

type SchemaKey = "project" | "captions" | "effects" | "cuts" | "config";

// ==========================================
// 2. ローカル解析 (HTML版 runHybridVideoAnalysis の移植)
// ==========================================

interface RawSegment {
  start: number;
  end: number;
  text: string;
  db: number;
  ev: string;
}

const SAMPLE_SEGMENTS: RawSegment[] = [
  { start: 0.0, end: 3.2, text: "【戦闘開始】ボスHP 200・残機 2！3秒周期の強化アイテムを狙います。", db: -12.0, ev: "session_init" },
  { start: 3.2, end: 4.6, text: "", db: -48.0, ev: "silence" },
  { start: 4.6, end: 8.5, text: "【火力強化】攻撃力+3を回収！現在攻撃力が 8 に永続上昇！", db: -8.5, ev: "item_pickup" },
  { start: 8.5, end: 12.8, text: "【10秒無敵発動】全ダメージnullバリア展開！正面から撃ち込めます！", db: -5.2, ev: "item_pickup" },
  { start: 12.8, end: 14.1, text: "", db: -50.0, ev: "silence" },
  { start: 14.1, end: 18.0, text: "【撃破クリア！】経過 16.5秒・最終攻撃力 14 でボスを完全撃破しました！", db: -3.8, ev: "boss_defeated" },
];

const round2 = (n: number): number => Math.round(n * 100) / 100;

export function analyzeLocally(thresholdSec: number): VideoProject {
  let cursor = 0;
  let removedSec = 0;
  const captions: VideoCaption[] = [];
  const effects: VideoCaptionEffect[] = [];
  const clips: VideoClip[] = [];
  const removed: RemovedSilenceRange[] = [];

  for (const seg of SAMPLE_SEGMENTS) {
    const dur = round2(seg.end - seg.start);

    // Stage 1: -40dB以下 かつ 閾値秒数以上 を無音カット
    if ((seg.db <= -40 || !seg.text) && dur >= thresholdSec) {
      removedSec = round2(removedSec + dur);
      removed.push({
        original_start: seg.start,
        original_end: seg.end,
        duration_removed: dur,
        audio_db: seg.db,
        reason: "silence_below_threshold",
      });
      continue;
    }

    const st = cursor;
    const et = round2(cursor + dur);
    cursor = et;

    const idx = captions.length + 1;
    const capId = `cap_00${idx}`;

    // Stage 2: 音量と感嘆符から盛り上がりスコア(0-100)とエフェクトを割当
    const score = Math.min(
      100,
      Math.round((seg.db + 40) * 2.2 + (seg.text.includes("！") ? 15 : 0))
    );
    const effect =
      seg.ev === "boss_defeated" ? "impact_burst" : seg.db > -6 ? "glow_pop" : "typewriter";
    const color =
      effect === "impact_burst" ? "#facc15" : effect === "glow_pop" ? "#38bdf8" : "#f8fafc";

    captions.push({ id: capId, start: st, end: et, text: seg.text || "(無音維持区間)" });
    effects.push({ caption_id: capId, effect, color, bgOpacity: 0.75, excitement_score: score });
    clips.push({
      clip_id: `clip_00${idx}`,
      original_range: [seg.start, seg.end],
      edited_range: [st, et],
      duration: dur,
      excitement_score: score,
    });
  }

  // Stage 3: Electron + React 用の統合 project.json
  return {
    version: "1.0.0",
    metadata: {
      resolution: "1920x1080",
      fps: 60,
      original_duration_sec: 18.0,
      edited_duration_sec: cursor,
      removed_silence_sec: removedSec,
      silence_cuts_count: removed.length,
      silence_threshold_sec: thresholdSec,
    },
    fontConfig: { headlineFont: "Dela Gothic One", bodyFont: "Noto Sans JP", defaultFontSize: 42 },
    shortcuts: { play_pause: "Space", split_clip: "S", speed_up: "B", export_json: "Ctrl+E" },
    captions,
    captionEffects: effects,
    timelineClips: clips,
    removedSilenceRanges: removed,
    pluginSlots: { youtubeTranscriptApi: "ready", whisperLocalAsr: "ready", customToModel: "stagable_v1" },
  };
}

// ==========================================
// 3. ユーティリティ
// ==========================================

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** payload.project / payload 直下 のどちらでも project として受け取る */
function extractProject(payload: Record<string, unknown>): VideoProject | null {
  const candidate = isRecord(payload.project) ? payload.project : payload;
  if (
    isRecord(candidate.metadata) &&
    Array.isArray(candidate.captions) &&
    Array.isArray(candidate.timelineClips)
  ) {
    return candidate as unknown as VideoProject;
  }
  return null;
}

function formatTime(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = sec - m * 60;
  return `${String(m).padStart(2, "0")}:${s.toFixed(2).padStart(5, "0")}`;
}

const THRESHOLDS = [0.5, 0.8, 1.5] as const;

const SCHEMA_TABS: { key: SchemaKey; label: string; file: string }[] = [
  { key: "project", label: "統合 project.json", file: "project.json" },
  { key: "captions", label: "captions.json", file: "captions.json" },
  { key: "effects", label: "caption-effects.json", file: "caption-effects.json" },
  { key: "cuts", label: "timeline-cuts.json", file: "timeline-cuts.json" },
  { key: "config", label: "font & shortcuts.json", file: "font-and-shortcuts.json" },
];

const EFFECT_LABEL: Record<string, string> = {
  impact_burst: "インパクト",
  glow_pop: "グロー",
  typewriter: "タイプライター",
};

// ==========================================
// 4. コンポーネント
// ==========================================

export default function VideoCuratorCard({
  payload,
  onOptionSelect,
}: VideoCuratorCardProps): React.ReactElement {
  const backendProject = useMemo(() => extractProject(payload), [payload]);
  const [localThreshold, setLocalThreshold] = useState<number>(0.8);
  const [schemaKey, setSchemaKey] = useState<SchemaKey>("project");
  const [notice, setNotice] = useState<string>("");

  const isLocal = backendProject === null;
  const project = backendProject ?? analyzeLocally(localThreshold);
  const meta = project.metadata;
  const activeThreshold = isLocal ? localThreshold : meta.silence_threshold_sec;

  const effectById = useMemo(() => {
    const map = new Map<string, VideoCaptionEffect>();
    project.captionEffects.forEach((e) => map.set(e.caption_id, e));
    return map;
  }, [project]);

  const bundle: Record<SchemaKey, unknown> = useMemo(
    () => ({
      project,
      captions: project.captions,
      effects: project.captionEffects,
      cuts: {
        timelineClips: project.timelineClips,
        removedSilenceRanges: project.removedSilenceRanges,
      },
      config: { fontConfig: project.fontConfig, shortcuts: project.shortcuts },
    }),
    [project]
  );

  const jsonText = useMemo(() => JSON.stringify(bundle[schemaKey], null, 2), [bundle, schemaKey]);

  const flash = useCallback((msg: string) => {
    setNotice(msg);
    window.setTimeout(() => setNotice(""), 2500);
  }, []);

  const handleThreshold = (sec: number) => {
    setLocalThreshold(sec);
    onOptionSelect?.({ action: "video_reanalyze", silence_threshold_sec: sec });
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(jsonText);
      flash("クリップボードにコピーしました");
    } catch {
      flash("コピーに失敗しました");
    }
  };

  const handleDownload = () => {
    const file = SCHEMA_TABS.find((t) => t.key === schemaKey)?.file ?? "project.json";
    const blob = new Blob([jsonText], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = file;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    flash(`${file} を保存しました`);
  };

  const summary = typeof payload.summary === "string" ? payload.summary : "";

  return (
    <div className="w-full space-y-4 text-sm">
      {summary && (
        <div className="whitespace-pre-wrap border-b border-slate-100 pb-3 leading-relaxed text-slate-700 dark:border-slate-700 dark:text-slate-300">
          {summary}
        </div>
      )}

      {isLocal && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-300">
          サーバーから解析結果が届いていないため、サンプル動画でルールベース解析をプレビューしています。
        </div>
      )}

      {/* 無音カット閾値 */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800">
        <span className="text-xs text-slate-600 dark:text-slate-300">
          無音カット閾値:{" "}
          <b className="text-amber-600 dark:text-amber-300">{activeThreshold}秒以上</b>
        </span>
        <div className="flex gap-1">
          {THRESHOLDS.map((sec) => (
            <button
              key={sec}
              type="button"
              onClick={() => handleThreshold(sec)}
              aria-pressed={activeThreshold === sec}
              className={`rounded px-2 py-1 text-xs font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 ${
                activeThreshold === sec
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-200 text-slate-700 hover:bg-slate-300 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600"
              }`}
            >
              {sec}s
            </button>
          ))}
        </div>
      </div>

      {/* メトリクス */}
      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        <Metric
          label="元動画尺 → 編集後"
          value={`${meta.original_duration_sec}s → ${meta.edited_duration_sec}s`}
          tone="text-sky-600 dark:text-sky-300"
        />
        <Metric
          label="無音カット削減"
          value={`-${meta.removed_silence_sec}s (${meta.silence_cuts_count}箇所)`}
          tone="text-amber-600 dark:text-amber-300"
        />
        <Metric
          label="字幕・エフェクト"
          value={`${project.captions.length}行`}
          tone="text-emerald-600 dark:text-emerald-300"
        />
      </div>

      {/* 字幕タイムライン */}
      <div className="space-y-1.5">
        <div className="text-xs font-semibold text-slate-700 dark:text-slate-200">
          字幕タイムライン（編集後のタイムコード）
        </div>
        {project.captions.length === 0 ? (
          <div className="rounded border border-dashed border-slate-300 p-3 text-xs text-slate-500 dark:border-slate-600 dark:text-slate-400">
            字幕がありません。閾値を短くするか、字幕プラグインを接続してください。
          </div>
        ) : (
          project.captions.map((cap) => {
            const eff = effectById.get(cap.id);
            return (
              <div
                key={cap.id}
                className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded border border-slate-200 bg-white p-2 dark:border-slate-700 dark:bg-slate-900"
              >
                <span className="font-mono text-xs font-semibold text-sky-600 dark:text-sky-400">
                  {formatTime(cap.start)} - {formatTime(cap.end)}
                </span>
                <span className="min-w-0 flex-1 text-xs text-slate-800 dark:text-slate-100">
                  {cap.text}
                </span>
                {eff && (
                  <span className="flex items-center gap-1.5 text-[11px] text-slate-500 dark:text-slate-400">
                    <span
                      className="inline-block h-2.5 w-2.5 rounded-full border border-slate-300 dark:border-slate-600"
                      style={{ backgroundColor: eff.color }}
                      aria-hidden="true"
                    />
                    {EFFECT_LABEL[eff.effect] ?? eff.effect} / 盛り上がり {eff.excitement_score}
                  </span>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* カットされた無音区間 */}
      {project.removedSilenceRanges.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-xs font-semibold text-slate-700 dark:text-slate-200">
            カットした無音区間（元動画の時間）
          </div>
          {project.removedSilenceRanges.map((r) => (
            <div
              key={`${r.original_start}-${r.original_end}`}
              className="flex justify-between rounded border border-slate-200 bg-slate-50 px-2.5 py-1.5 font-mono text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
            >
              <span>
                {formatTime(r.original_start)} - {formatTime(r.original_end)}
              </span>
              <span>
                -{r.duration_removed}s ({r.audio_db}dB)
              </span>
            </div>
          ))}
        </div>
      )}

      {/* JSON プレビュー */}
      <div className="space-y-2">
        <div className="flex flex-wrap gap-1">
          {SCHEMA_TABS.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setSchemaKey(tab.key)}
              aria-pressed={schemaKey === tab.key}
              className={`rounded px-2 py-1 text-[11px] font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 ${
                schemaKey === tab.key
                  ? "bg-emerald-600 text-white"
                  : "bg-slate-200 text-slate-700 hover:bg-slate-300 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <pre className="max-h-60 overflow-auto rounded-lg bg-slate-900 p-3 font-mono text-[11px] leading-relaxed text-emerald-400">
          {jsonText}
        </pre>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleCopy}
            className="rounded-md bg-emerald-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-600"
          >
            JSONをコピー
          </button>
          <button
            type="button"
            onClick={handleDownload}
            className="rounded-md bg-sky-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-sky-600"
          >
            JSONを保存
          </button>
          <span role="status" aria-live="polite" className="text-xs text-slate-500 dark:text-slate-400">
            {notice}
          </span>
        </div>
      </div>

      {/* プラグインスロット */}
      <div className="flex flex-wrap gap-1.5 text-[11px]">
        {Object.entries(project.pluginSlots).map(([name, state]) => (
          <span
            key={name}
            className="rounded border border-slate-200 bg-slate-50 px-2 py-0.5 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
          >
            {name}: {state}
          </span>
        ))}
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: string;
}): React.ReactElement {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-2 dark:border-slate-700 dark:bg-slate-800">
      <div className="text-[10px] text-slate-500 dark:text-slate-400">{label}</div>
      <div className={`mt-0.5 font-bold ${tone}`}>{value}</div>
    </div>
  );
}