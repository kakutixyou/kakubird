// frontend/src/components/ui/loadingPresets.ts
import type { LoadingVariant } from "./LoadingIndicator";

export interface LoadingPreset {
  id: string;
  variant: LoadingVariant;
  messages?: string[];
  label?: string;
}

interface Rule {
  pattern: RegExp;
  preset: LoadingPreset;
}

// 上から順に判定。IntentInspector の優先順位と揃えること
const RULES: Rule[] = [
  {
    pattern: /マルウェア|キーロガー|keylog|synflood|portscanner|dos\s*mode|c2|埋め込みpe/i,
    preset: {
      id: "security",
      variant: "steps",
      messages: ["文字列を解析中", "PEヘッダ・埋め込みを確認中", "C2通信先を抽出中", "防御ルールを作成中"],
    },
  },
  {
    pattern: /sha-?(?:1|256|512)|\bmd5\b|ssdeep|tlsh|imphash|ハッシュ|フィンガープリント|fingerprint/i,
    preset: {
      id: "hash",
      variant: "steps",
      messages: ["ファイルを読み込み中", "ハッシュ値を計算中", "結果を整理中"],
    },
  },
  {
    pattern: /https?:\/\/|動画|字幕|造語|話者|何人|タイムバー/i,
    preset: {
      id: "video",
      variant: "steps",
      messages: ["URLを確認中", "音声を取得して話者を分離中", "秒単位の字幕を生成中", "ジャンルを判定中"],
    },
  },
  {
    pattern: /ブラック企業|残業|連勤|パワハラ|体験談|メモ/i,
    preset: {
      id: "memo",
      variant: "messages",
      messages: ["体験談を読み取り中", "カテゴリと数値を抽出中", "JSONメモを作成中"],
    },
  },
  {
    pattern: /vs\s*code|vscode|tasks\.json|settings\.json|launch\.json|\.vscode/i,
    preset: {
      id: "vscode",
      variant: "messages",
      messages: ["VS Codeの知識を検索中", "設定の候補を整理中"],
    },
  },
  {
    pattern: /ギャグ|ダジャレ|ボケ|大喜利/,
    preset: {
      id: "gag",
      variant: "messages",
      messages: ["ネタを考え中", "ルールに合うか確認中", "オチを整え中"],
    },
  },
  {
    pattern: /計算|\d+\s*[+\-*/^×÷]\s*\d+|積分|微分|方程式/,
    preset: { id: "math", variant: "spinner", label: "計算中..." },
  },
];

export const DEFAULT_PRESET: LoadingPreset = { id: "chat", variant: "dots" };

export function resolveLoadingPreset(text: string | null | undefined): LoadingPreset {
  const t = (text ?? "").trim();
  if (!t) return DEFAULT_PRESET;
  return RULES.find((r) => r.pattern.test(t))?.preset ?? DEFAULT_PRESET;
}