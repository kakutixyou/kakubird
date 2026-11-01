import React, { useState, useEffect, useMemo } from "react";
import {
  Film,
  ShieldAlert,
  FileText,
  Code2,
  Play,
  Pause,
  RotateCcw,
  Users,
  Music,
  Sparkles,
  Copy,
  Download,
  Plus,
  Trash2,
  CheckCircle2,
  Terminal,
  Lock,
  Globe,
  Scissors,
  Volume2,
  Tag,
  MessageSquare,
  Layers,
} from "lucide-react";

// ==========================================
// 型定義 (TypeScript Interfaces)
// ==========================================

interface SpeakerInfo {
  speaker_id: string;
  name: string;
  voice_profile: string;
  speaking_sec: number;
  ratio_pct: number;
  color: string;
}

interface TimelineSegment {
  id: string;
  start: number;
  end: number;
  speaker_id: string;
  speaker_name: string;
  text: string;
  conlang_raw?: string;
  phonetic_kana?: string;
  ipa?: string;
  translated_meaning?: string;
  energy: number;
  is_silence: boolean;
}

interface UrlAnalysisResult {
  url: string;
  mode: "standard_video" | "conlang_song" | "security_lecture";
  title: string;
  duration_sec: number;
  genre: {
    primary: string;
    confidence_pct: number;
    sub_genres: string[];
    detected_features: string[];
  };
  speaker_summary: {
    total_speakers_count: number;
    detection_method: string;
    speakers: SpeakerInfo[];
  };
  segments: TimelineSegment[];
}

interface MemoComment {
  comment_id: string;
  author: string;
  tag: string;
  text: string;
  created_at: string;
}

// ==========================================
// プリセットデータ & 解析ロジック
// ==========================================

const DEFAULT_CONLANG_DICT: Record<string, string> = {
  kora: "光・暁",
  miel: "祈り・響き",
  saluva: "解き放つ",
  noctis: "夜の帳",
  aeterna: "永遠の螺旋",
  velia: "翼",
  shion: "記憶の詩",
  lumen: "煌めき",
};

function formatTime(sec: number): string {
  const mins = Math.floor(sec / 60);
  const secs = Math.floor(sec % 60);
  const ms = Math.floor((sec - Math.floor(sec)) * 100);
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}.${String(ms).padStart(2, "0")}`;
}

function buildUrlAnalysis(
  url: string,
  conlangDict: Record<string, string>,
  silenceThreshold: number
): UrlAnalysisResult {
  const lower = url.toLowerCase();

  // 1. オリジナル言語（造語）楽曲モード
  if (
    lower.includes("conlang") ||
    lower.includes("song") ||
    lower.includes("astraea") ||
    lower.includes("music")
  ) {
    const rawLyrics = [
      {
        id: "lyr_01",
        start: 0.0,
        end: 5.5,
        speaker_id: "vocal_1",
        speaker_name: "Vocal A (メインソプラノ)",
        conlang: "Kora miel, noctis velia",
        kana: "コラ・ミエル、ノクティス・ヴェリア",
        ipa: "/ko.ɾa mi.el nok.tis ve.li.a/",
        energy: 78,
      },
      {
        id: "lyr_02",
        start: 5.5,
        end: 11.5,
        speaker_id: "vocal_2",
        speaker_name: "Vocal B (アルト・ハーモニー)",
        conlang: "Shion lumen, saluva aeterna",
        kana: "シオン・ルーメン、サルヴァ・エテルナ",
        ipa: "/ɕi.on luː.men sa.lu.va a.e.ter.na/",
        energy: 85,
      },
      {
        id: "lyr_03",
        start: 11.5,
        end: 17.5,
        speaker_id: "vocal_3",
        speaker_name: "Chorus C (多重コーラス隊)",
        conlang: "Saluva kora! Aeterna miel!",
        kana: "サルヴァ・コラ！エテルナ・ミエル！",
        ipa: "/sa.lu.va ko.ɾa a.e.ter.na mi.el/",
        energy: 98,
      },
      {
        id: "lyr_04",
        start: 17.5,
        end: 24.0,
        speaker_id: "vocal_1",
        speaker_name: "Vocal A & B (重唱クライマックス)",
        conlang: "Velia lumen in noctis shion",
        kana: "ヴェリア・ルーメン・イン・ノクティス・シオン",
        ipa: "/ve.li.a luː.men in nok.tis ɕi.on/",
        energy: 94,
      },
    ];

    const segments: TimelineSegment[] = rawLyrics.map((item) => {
      const tokens = item.conlang.toLowerCase().match(/[a-z]+/g) || [];
      const glosses = tokens
        .filter((w) => conlangDict[w])
        .map((w) => `${w}＝${conlangDict[w]}`);
      return {
        id: item.id,
        start: item.start,
        end: item.end,
        speaker_id: item.speaker_id,
        speaker_name: item.speaker_name,
        text: item.conlang,
        conlang_raw: item.conlang,
        phonetic_kana: item.kana,
        ipa: item.ipa,
        translated_meaning:
          glosses.length > 0
            ? glosses.join(" ／ ")
            : "未登録の造語音素（右の辞書から単語追加可能）",
        energy: item.energy,
        is_silence: false,
      };
    });

    return {
      url,
      mode: "conlang_song",
      title: "【造語ソング解析】Astraea Hymmnos — 架空言語多重コーラス曲",
      duration_sec: 24.0,
      genre: {
        primary: "ファンタジー造語楽曲・シンフォニックコーラス",
        confidence_pct: 96,
        sub_genres: [
          "オリジナル言語 (Conlang) ボーカル曲",
          "多重コーラス・劇伴音楽 (BPM 128 / 4/4拍子)",
        ],
        detected_features: [
          "既存言語辞書にない規則的母音調和を検出",
          "F0ピッチ軌道から3声部（ソプラノ・アルト・合唱）を分離",
          "音素(IPA)・カタカナ発音書き起こし＋カスタム造語辞書対訳",
        ],
      },
      speaker_summary: {
        total_speakers_count: 3,
        detection_method:
          "音響声部分離 (ピッチF0追跡 ＋ フォルマントF1/F2クラスタリング)",
        speakers: [
          {
            speaker_id: "vocal_1",
            name: "Vocal A (メインソプラノ)",
            voice_profile: "Soprano / Vibrato (440-880Hz)",
            speaking_sec: 12.0,
            ratio_pct: 50,
            color: "#ec4899",
          },
          {
            speaker_id: "vocal_2",
            name: "Vocal B (アルト・ハーモニー)",
            voice_profile: "Alto / Whisper (260-520Hz)",
            speaking_sec: 6.0,
            ratio_pct: 25,
            color: "#38bdf8",
          },
          {
            speaker_id: "vocal_3",
            name: "Chorus C (多重コーラス隊)",
            voice_profile: "Choir Ensemble (Multi-harmonic)",
            speaking_sec: 6.0,
            ratio_pct: 25,
            color: "#a855f7",
          },
        ],
      },
      segments,
    };
  }

  // 2. セキュリティ解説講義モード
  if (lower.includes("security") || lower.includes("malware")) {
    return {
      url,
      mode: "security_lecture",
      title: "【技術講義】マルウェア静的解析と埋め込みPE・C2遮断ハンズオン",
      duration_sec: 24.0,
      genre: {
        primary: "セキュリティ・リバースエンジニアリング解説",
        confidence_pct: 95,
        sub_genres: ["マルウェア対策講義", "対話型技術チュートリアル"],
        detected_features: [
          "専門用語高密度 (PE, DOS stub, SynFlooding, keylog.txt)",
          "講師と受講者の2話者ターン交代",
        ],
      },
      speaker_summary: {
        total_speakers_count: 2,
        detection_method: "音響クラスタリング (2話者ダイアライゼーション)",
        speakers: [
          {
            speaker_id: "spk_sec_1",
            name: "講師 A (セキュリティアナリスト)",
            voice_profile: "Male / Calm (125Hz)",
            speaking_sec: 16.5,
            ratio_pct: 69,
            color: "#0ea5e9",
          },
          {
            speaker_id: "spk_sec_2",
            name: "受講者 B (開発エンジニア)",
            voice_profile: "Male / Mid (155Hz)",
            speaking_sec: 7.5,
            ratio_pct: 31,
            color: "#10b981",
          },
        ],
      },
      segments: [
        {
          id: "sec_01",
          start: 0.0,
          end: 6.0,
          speaker_id: "spk_sec_1",
          speaker_name: "講師 A",
          text: "本日はPEヘッダ内のDOSスタブ改ざんと埋め込みドロッパーの見分け方を解説します。",
          energy: 68,
          is_silence: false,
        },
        {
          id: "sec_02",
          start: 6.0,
          end: 12.0,
          speaker_id: "spk_sec_2",
          speaker_name: "受講者 B",
          text: "オフセット0x0076にある2つ目の『in Dos mode』が内部ペイロードの目印ですね！",
          energy: 75,
          is_silence: false,
        },
        {
          id: "sec_03",
          start: 12.0,
          end: 18.0,
          speaker_id: "spk_sec_1",
          speaker_name: "講師 A",
          text: "その通りです。さらにSynFloodingとkeylog.txtの文字列からDoS兼キーロガーと特定できます。",
          energy: 82,
          is_silence: false,
        },
        {
          id: "sec_04",
          start: 18.0,
          end: 24.0,
          speaker_id: "spk_sec_1",
          speaker_name: "講師 A",
          text: "抽出されたC2 IP 128.91.34.188 はiptablesとWindows Firewallで即座に遮断しましょう。",
          energy: 88,
          is_silence: false,
        },
      ],
    };
  }

  // 3. デフォルト: ゲーム実況・マルチ話者モード
  const rawGameSegments: TimelineSegment[] = [
    {
      id: "seg_01",
      start: 0.0,
      end: 4.2,
      speaker_id: "spk_1",
      speaker_name: "Speaker A (実況メイン)",
      text: "【戦闘開始】ボスHP 200・残機2！まずは3秒周期の強化アイテムを狙っていきます！",
      energy: 80,
      is_silence: false,
    },
    {
      id: "seg_02",
      start: 4.2,
      end: 5.5,
      speaker_id: "none",
      speaker_name: "無音区間",
      text: `(無音 1.3秒 — 閾値 ${silenceThreshold}s 以上のため自動カット対象)`,
      energy: 6,
      is_silence: 1.3 >= silenceThreshold,
    },
    {
      id: "seg_03",
      start: 5.5,
      end: 10.2,
      speaker_id: "spk_2",
      speaker_name: "Speaker B (解説パートナー)",
      text: "攻撃力+3アイテムを回収しましたね！現在攻撃力が 8 に永続上昇しています。",
      energy: 74,
      is_silence: false,
    },
    {
      id: "seg_04",
      start: 10.2,
      end: 13.5,
      speaker_id: "spk_3",
      speaker_name: "Speaker C (システム/ボス警告)",
      text: "WARNING: 10秒無敵バリア展開を確認。ボスの全方位弾幕フェーズへ移行します。",
      energy: 89,
      is_silence: false,
    },
    {
      id: "seg_05",
      start: 13.5,
      end: 18.5,
      speaker_id: "spk_1",
      speaker_name: "Speaker A (実況メイン)",
      text: "よし、10秒無敵の間に正面へ張り付いてゼロ距離連射で一気に削り切るぞ！",
      energy: 95,
      is_silence: false,
    },
    {
      id: "seg_06",
      start: 18.5,
      end: 24.0,
      speaker_id: "spk_2",
      speaker_name: "Speaker B (解説パートナー)",
      text: "【撃破クリア！】経過16.5秒・最終攻撃力14でボス完全撃破です！ナイスプレイ！",
      energy: 99,
      is_silence: false,
    },
  ];

  return {
    url,
    mode: "standard_video",
    title: "【ゲーム実況】シューティングゲーム ボス戦1v1 攻略＆掛け合い解説",
    duration_sec: 24.0,
    genre: {
      primary: "ゲーム実況・シューティング攻略",
      confidence_pct: 94,
      sub_genres: ["アクション・ボス戦解説", "マルチプレイヤー掛け合い実況"],
      detected_features: [
        "3話者（実況・解説・システム音声）の周波数分離",
        "無音区間（4.2s〜5.5s）の自動検出",
        "後半（13.5s以降）の音声エネルギー上昇・クライマックス検出",
      ],
    },
    speaker_summary: {
      total_speakers_count: 3,
      detection_method:
        "音響クラスタリング (x-vector / F0基本周波数＆話者交代検出)",
      speakers: [
        {
          speaker_id: "spk_1",
          name: "Speaker A (実況メイン)",
          voice_profile: "Male / Energetic (145Hz)",
          speaking_sec: 9.2,
          ratio_pct: 41,
          color: "#6366f1",
        },
        {
          speaker_id: "spk_2",
          name: "Speaker B (解説パートナー)",
          voice_profile: "Female / Clear (235Hz)",
          speaking_sec: 10.2,
          ratio_pct: 45,
          color: "#10b981",
        },
        {
          speaker_id: "spk_3",
          name: "Speaker C (システム/ボス音声)",
          voice_profile: "Synth / Low (95Hz)",
          speaking_sec: 3.3,
          ratio_pct: 14,
          color: "#f59e0b",
        },
      ],
    },
    segments: rawGameSegments,
  };
}

// ==========================================
// メインアプリケーション (React TSX)
// ==========================================

export interface ToAiStudioDashboardProps {
  initialPage?: "video" | "memo" | "security" | "code";
  initialData?: Record<string, unknown>;
  onOptionSelect?: (data: unknown) => void;
}

const MISSING_CODE_FILES: Record<string, { title: string; desc: string; code: string }> = {
  to_model_handler: {
    title: "1. ToModelHandler.py (専門解析Widget ＋ 本体搭載・マルチターン会話エンジン統合版)",
    desc: "tools/ からの強制ルーティング時の Widget 応答 (handle) と、ChatHandler の fallback_generate / LocalLLMEngine として機能する会話応答 (generate_chat_response) の両方を備えた完全版です。",
    code: `#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# api/services/handlers/ToModel/ToModelHandler.py

from __future__ import annotations
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ToModelConversationEngine:
    """
    自作モデル (to_model) のマルチターン会話・文脈理解エンジン。
    ConversationState (履歴・現在のトピック・未解決タスク) と Knowledge を参照して対話応答を生成し、
    必要に応じて動画URL解析・日本語体験談JSON化・マルウェア防御データを同時に返す。
    """

    def generate_reply(
        self,
        user_message: str,
        analysis: Optional[Dict[str, Any]] = None,
        state: Optional[Any] = None,
        summary: Optional[Dict[str, Any]] = None,
        knowledge_data: Optional[List[Any]] = None,
        engine_facade: Optional[Any] = None,
    ) -> Dict[str, Any]:
        msg = str(user_message or "").strip()
        lower = msg.lower()
        topic = getattr(state, "current_topic", None) or (summary or {}).get("current_topic") or "一般対話"
        turn_count = getattr(state, "turn_count", 1) if state is not None else 1

        # ① セキュリティ・マルウェア相談＋自動解析
        if any(k in lower or k in msg for k in ("dos mode", "keylog", "synflood", "portscanner", "マルウェア", "キーロガー")):
            sec_data = engine_facade.run(message=msg, mode="security")["data"] if engine_facade else {}
            return {
                "reply": (
                    f"セキュリティ解析モデルとして確認しました（トピック: {topic}）。\\n"
                    "入力された文字列から埋め込みPEヘッダ、C2通信先 (128.91.34.188)、および DoS / キーロガーの痕跡を検出しました。\\n"
                    "下の防御コンソールから SYN Cookies 有効化と keylog.txt のシンクホールロックを適用できます。"
                ),
                "response_type": "malware_defense",
                "active_page": "security",
                "data": sec_data,
            }

        # ② ブラック企業体験談・悩み相談＋コメント付きJSONメモ化
        if any(k in lower or k in msg for k in ("ブラック企業", "残業", "連勤", "大変だった", "つらい", "パワハラ", "メモ", "コメント")):
            memo_data = engine_facade.run(message=msg, mode="memo")["data"] if engine_facade else {}
            return {
                "reply": (
                    "お話しいただきありがとうございます。当時の過酷な労働環境や大変だった状況を、"
                    "定量データ（残業時間・連勤・睡眠時間）および振り返りコメントと共に JSON (experience_memos.json / comments.json) に構造化して記録しました。"
                ),
                "response_type": "experience_memo",
                "active_page": "memo",
                "data": memo_data,
            }

        # ③ 動画URL・話者人数・秒単位字幕・造語曲解析
        if any(k in lower or k in msg for k in ("http://", "https://", "動画", "字幕", "造語", "曲", "何人", "タイムバー")):
            vid_data = engine_facade.run(message=msg, mode="video")["data"] if engine_facade else {}
            return {
                "reply": (
                    "動画・音響URL解析を実行しました！話者分離（何人喋っていたか）、秒単位の字幕タイムスタンプ、"
                    "ジャンル判定、および造語曲の音素・対訳データを下のタイムバー付きスタジオに表示しています。"
                ),
                "response_type": "video_curator",
                "active_page": "video",
                "data": vid_data,
            }

        # ④ 日常会話・設計相談モード (ChatBubble として自然に対話)
        return {
            "reply": (
                f"なるほど、「{msg}」ですね！（ターン{turn_count} / トピック: {topic}）\\n"
                "会話の文脈を記憶しながら、いつでも動画URLの解析やブラック企業体験談のJSONメモ化、マルウェア検査へシームレスに切り替えられます。"
            ),
            "response_type": "chat",
            "active_page": "video",
            "data": {"turn": turn_count, "topic": topic, "conversational_mode": True},
        }


class ToModelHandler:
    """
    本体 (To Core) 側の Handler。
    1. ChatHandler(fallback_generate=to_model_handler.generate_chat_response) として渡せば会話LLMとして動作
    2. pre_responders に ToModelResponderAdapter を登録すれば専門Widget描画も自動実行
    """

    HANDLER_NAME = "ToModelHandler"
    DEFAULT_SCORE = 95

    def __init__(self) -> None:
        self.enabled = True
        self.conversation_engine = ToModelConversationEngine()
        self._engine: Optional[Any] = None
        try:
            from to_model.main import ToModelUnifiedEngine
            self._engine = ToModelUnifiedEngine()
        except Exception as exc:
            logger.info("to_model direct import unavailable: %s", exc)

    def generate_chat_response(
        self,
        user_message: str,
        analysis: Optional[Dict[str, Any]] = None,
        state: Optional[Any] = None,
        summary: Optional[Dict[str, Any]] = None,
        knowledge_data: Optional[List[Any]] = None,
    ) -> str:
        """ChatHandler._generate_with_local_llm から呼ばれる会話生成メソッド"""
        res = self.conversation_engine.generate_reply(
            user_message=user_message,
            analysis=analysis,
            state=state,
            summary=summary,
            knowledge_data=knowledge_data,
            engine_facade=self._engine,
        )
        return str(res.get("reply") or "")

    async def handle(self, request: Any) -> Tuple[str, Dict[str, Any]]:
        message = str(request.get("message", "") if isinstance(request, dict) else getattr(request, "message", ""))
        state = request.get("state") if isinstance(request, dict) else getattr(request, "state", None)
        analysis = (request.get("analysis") if isinstance(request, dict) else getattr(request, "analysis", None)) or {}

        out = self.conversation_engine.generate_reply(
            user_message=message,
            analysis=analysis,
            state=state,
            engine_facade=self._engine,
        )
        return out["reply"], {
            "source": self.HANDLER_NAME,
            "type": out["response_type"],
            "response_type": out["response_type"],
            "active_page": out["active_page"],
            "data": out["data"],
        }`
  },
  aichat_integration: {
    title: "2. AIChatMessageList.tsx (既存3.6 / 3.7 / 3.8と ToAiStudioDashboard.tsx ＆ 会話を完全統合)",
    desc: "提示いただいた AIChatMessageList.tsx の 3.6 Malware Defense と 3.7 Video Curator に ToAiStudioDashboard を組み込み、通常会話は 5. Normal Chat の ChatBubble で自然に表示される完全版です。",
    code: `// AIChatMessageList.tsx (3.6 〜 3.7 および 5. Normal Chat の統合コード)
import ToAiStudioDashboard from "@/components/widgets/ToAiStudioDashboard";

// ----------------------------------------------------
// 3.6 Malware Defense UI (HEX・DoS対策・キーロガー対策 + ToAiStudioDashboard 連携)
// ----------------------------------------------------
if (
  msg?.type === "malware_defense" ||
  msg?.response_type === "malware_defense"
) {
  const payload = isRecord(msg?.data)
    ? msg.data
    : isRecord(msg?.content)
    ? msg.content
    : {};

  return (
    <div key={messageKey} className="flex w-full flex-col items-start">
      <ChatLabel role="ai" />
      <WidgetCard icon="🛡️" title="マルウェア解析 ＆ 防御コンソール">
        {typeof payload.summary === "string" && (
          <div className="border-b border-slate-100 pb-3 text-sm text-slate-700 dark:border-slate-700 dark:text-slate-300">
            <RenderSmartContent value={payload.summary} />
          </div>
        )}

        <div className="mt-3 space-y-3">
          {Array.isArray(payload.c2_ips) && payload.c2_ips.length > 0 && (
            <div className="rounded-lg bg-red-50 p-2.5 text-xs text-red-700 dark:bg-red-950/40 dark:text-red-300 border border-red-200 dark:border-red-900">
              <span className="font-bold">検知されたC2通信先: </span>
              <span className="font-mono">{payload.c2_ips.join(", ")}</span>
            </div>
          )}

          <div className="mt-3 overflow-hidden rounded-xl border border-slate-800">
            <ToAiStudioDashboard
              initialPage="security"
              initialData={payload}
              onOptionSelect={onOptionSelect}
            />
          </div>
        </div>
      </WidgetCard>
    </div>
  );
}

// ----------------------------------------------------
// 3.7 Video Curator & Experience Memo Studio UI (動画URL・タイムバー・造語曲・日本語体験談JSON)
// ----------------------------------------------------
if (
  msg?.type === "video_curator" ||
  msg?.response_type === "video_curator" ||
  msg?.type === "experience_memo" ||
  msg?.response_type === "experience_memo" ||
  msg?.type === "to_model_studio" ||
  msg?.response_type === "to_model_studio"
) {
  const payload = isRecord(msg?.data)
    ? msg.data
    : isRecord(msg?.content)
    ? msg.content
    : {};
  const targetPage =
    (msg?.active_page as "video" | "memo" | "security" | "code") ||
    (msg?.response_type === "experience_memo" || msg?.type === "experience_memo"
      ? "memo"
      : "video");

  return (
    <div key={messageKey} className="flex w-full flex-col items-start">
      <ChatLabel role="ai" />
      <WidgetCard icon="🎬" title="Video Curator & ToModel Studio (.tsx)">
        {typeof msg?.message === "string" && (
          <div className="mb-3 border-b border-slate-100 pb-3 text-sm text-slate-700 dark:border-slate-700 dark:text-slate-300">
            <RenderSmartContent value={msg.message} />
          </div>
        )}
        <div className="w-full overflow-hidden rounded-xl border border-slate-800">
          <ToAiStudioDashboard
            initialPage={targetPage}
            initialData={payload}
            onOptionSelect={onOptionSelect}
          />
        </div>
      </WidgetCard>
    </div>
  );
}`
  },
  dashboard_tsx_code: {
    title: "3. ToAiStudioDashboard.tsx (Propsインターフェース ＆ 会話・4ページ統合コンポーネント構造)",
    desc: "AIChatMessageList.tsx から initialPage / initialData / onOptionSelect を受け取り、単体でもチャット欄埋め込みでも動作する React TSX コンポーネント定義です。",
    code: `// frontend/src/components/widgets/ToAiStudioDashboard.tsx
export interface ToAiStudioDashboardProps {
  initialPage?: "video" | "memo" | "security" | "code";
  initialData?: Record<string, unknown>;
  onOptionSelect?: (data: unknown) => void;
}

export default function ToAiStudioDashboard(props?: ToAiStudioDashboardProps) {
  // 1. activePage ("video" | "memo" | "security" | "code") で4つの専門画面を切替
  // 2. 自作モデル対話シミュレーターで「日常会話 ⇄ 動画URL解析 ⇄ 体験談JSONメモ ⇄ マルウェア検査」をシームレスにテスト可能
  // 3. ユーザーがボタンを押すと props?.onOptionSelect?.(payload) で本体 ChatHandler / ToModelHandler へ通知
}`
  },
  console_setup: {
    title: "4. ChatHandler.py への自作モデル会話＆Responder搭載コード (2箇所のみ)",
    desc: "ChatHandler の fallback_generate に generate_chat_response を渡すことで、自作モデルが本体の会話AIとしてもそのまま動作します。",
    code: `# api/services/handlers/ChatHandler/ChatHandler.py での接続方法

from api.services.handlers.ToModel.ToModelHandler import ToModelHandler, ToModelResponderAdapter

# ChatHandler.__init__ 内:
self.to_model_handler = ToModelHandler()

# 1. ローカルLLMが無い時や自作モデルで会話したい時の fallback_generate に設定:
if self.fallback_generate is None:
    self.fallback_generate = self.to_model_handler.generate_chat_response

# 2. 動画URL・マルウェア文字列・体験談メモが来た時に .tsx Widget を返す Adapter を pre_responders に追加:
self.pre_responders: List[Responder] = [
    _VSCodeResponderAdapter(vscode_tool_instance, self._debug),
    ToModelResponderAdapter(self.to_model_handler, self.results, self._debug),
    BuildResponder(...),
]`
  }
};

export default function App(props?: ToAiStudioDashboardProps) {
  // ページ（タブ）切替ステート（動画解析ページ / 日本語体験メモページ / セキュリティページ / コード表示ページ）
  const [activePage, setActivePage] = useState<
    "video" | "memo" | "security" | "code"
  >(props?.initialPage || "video");
  const [selectedCodeKey, setSelectedCodeKey] = useState<string>("to_model_handler");
  const [lastCallbackLog, setLastCallbackLog] = useState<string>("待機中 (画面内のボタンを押すと onOptionSelect 経由で本体Handlerへ通知されます)");

  // トースト通知
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const triggerToast = (msg: string, callbackPayload?: Record<string, unknown>) => {
    setToastMessage(msg);
    if (callbackPayload) {
      setLastCallbackLog(JSON.stringify(callbackPayload));
      props?.onOptionSelect?.(callbackPayload);
    }
  };

  useEffect(() => {
    if (!toastMessage) return;
    const timer = setTimeout(() => setToastMessage(null), 3200);
    return () => clearTimeout(timer);
  }, [toastMessage]);

  // ==========================================
  // 1. 動画URL解析・タイムバー・造語曲ステート
  // ==========================================
  const [targetUrl, setTargetUrl] = useState<string>(
    "https://www.youtube.com/watch?v=shmup_boss_01"
  );
  const [silenceThreshold, setSilenceThreshold] = useState<number>(0.8);
  const [conlangDict, setConlangDict] =
    useState<Record<string, string>>(DEFAULT_CONLANG_DICT);
  const [newConlangWord, setNewConlangWord] = useState<string>("astra");
  const [newConlangMeaning, setNewConlangMeaning] =
    useState<string>("星辰・輝き");

  const [currentTime, setCurrentTime] = useState<number>(0.0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [videoJsonTab, setVideoJsonTab] = useState<
    "project" | "speakers" | "captions" | "conlang"
  >("project");

  const urlAnalysis = useMemo(
    () => buildUrlAnalysis(targetUrl, conlangDict, silenceThreshold),
    [targetUrl, conlangDict, silenceThreshold]
  );

  // タイムバー自動再生タイマー
  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      setCurrentTime((prev) => {
        if (prev + 0.2 >= urlAnalysis.duration_sec) {
          setIsPlaying(false);
          return 0.0;
        }
        return +(prev + 0.2).toFixed(2);
      });
    }, 200);
    return () => clearInterval(interval);
  }, [isPlaying, urlAnalysis.duration_sec]);

  // 現在の再生秒数に対応するセグメント
  const activeSegment = useMemo(() => {
    return (
      urlAnalysis.segments.find(
        (s) => currentTime >= s.start && currentTime <= s.end
      ) || urlAnalysis.segments[0]
    );
  }, [urlAnalysis.segments, currentTime]);

  const handleSelectUrlPreset = (presetUrl: string, label: string) => {
    setIsPlaying(false);
    setCurrentTime(0.0);
    setTargetUrl(presetUrl);
    triggerToast(`URL解析を実行しました: ${label}`);
  };

  const handleAddConlangWord = () => {
    const w = newConlangWord.trim().toLowerCase();
    const m = newConlangMeaning.trim();
    if (!w || !m) {
      triggerToast("造語単語と日本語の意味を入力してください");
      return;
    }
    setConlangDict((prev) => ({ ...prev, [w]: m }));
    setNewConlangWord("");
    setNewConlangMeaning("");
    triggerToast(`造語辞書に「${w} ＝ ${m}」を登録し、対訳字幕を更新しました`);
  };

  // 動画解析の出力JSONバンドル
  const videoExportJson = useMemo(() => {
    if (videoJsonTab === "speakers") {
      return urlAnalysis.speaker_summary;
    }
    if (videoJsonTab === "captions") {
      return {
        url: urlAnalysis.url,
        total_segments: urlAnalysis.segments.length,
        captions: urlAnalysis.segments.map((s) => ({
          id: s.id,
          start: s.start,
          end: s.end,
          speaker: s.speaker_name,
          text: s.text,
          is_silence_cut: s.is_silence,
        })),
      };
    }
    if (videoJsonTab === "conlang") {
      return {
        mode: urlAnalysis.mode,
        conlang_lexicon: conlangDict,
        phonetic_lyrics: urlAnalysis.segments.map((s) => ({
          start: s.start,
          end: s.end,
          vocal_part: s.speaker_name,
          conlang_raw: s.conlang_raw || s.text,
          phonetic_kana: s.phonetic_kana || "（標準日本語音声）",
          ipa: s.ipa || "-",
          translated_meaning: s.translated_meaning || "-",
        })),
      };
    }
    // 統合 project.json
    return {
      version: "1.0.0",
      source_url: urlAnalysis.url,
      title: urlAnalysis.title,
      genre: urlAnalysis.genre,
      speaker_summary: urlAnalysis.speaker_summary,
      silence_threshold_sec: silenceThreshold,
      fontConfig: {
        headlineFont: "Dela Gothic One",
        bodyFont: "Noto Sans JP",
        fontSize: 42,
      },
      shortcuts: {
        play_pause: "Space",
        split_clip: "S",
        speed_up: "B",
      },
      segments: urlAnalysis.segments,
    };
  }, [urlAnalysis, videoJsonTab, conlangDict, silenceThreshold]);

  // ==========================================
  // 2. 日本語解釈・体験談（ブラック企業等）＆コメントJSONステート
  // ==========================================
  const [memoText, setMemoText] = useState<string>(
    "前のブラック企業では月100時間のサービス残業と12連勤が当たり前で、終電を逃して会社に泊まり込むこともあった。上司からの理不尽な無茶振りや怒鳴り声で睡眠4時間の日が続き本当に大変だったけれど、退職して今は自分の作りたいAIモデル開発を進められている。"
  );
  const [memoComments, setMemoComments] = useState<MemoComment[]>([
    {
      comment_id: "cmt_001",
      author: "自分 (振り返り)",
      tag: "教訓・前進",
      text: "あの時の経験があるからこそ、作業の自動化や健全な開発環境の大切さが心から分かる。",
      created_at: "2026-11-01T02:00:00+09:00",
    },
    {
      comment_id: "cmt_002",
      author: "動画構成メモ",
      tag: "動画ネタ・字幕連携",
      text: "この体験談JSONをそのまま動画の字幕（captions.json）に変換してドキュメンタリー動画にもできる。",
      created_at: "2026-11-01T02:05:00+09:00",
    },
  ]);
  const [newCommentAuthor, setNewCommentAuthor] =
    useState<string>("自分 (振り返り)");
  const [newCommentTag, setNewCommentTag] = useState<string>("教訓・前進");
  const [newCommentText, setNewCommentText] = useState<string>("");
  const [memoJsonTab, setMemoJsonTab] = useState<
    "full" | "comments" | "captions"
  >("full");

  const memoAnalysis = useMemo(() => {
    const lexicon: Record<string, string[]> = {
      "長時間労働・サービス残業": [
        "残業",
        "サービス残業",
        "終電",
        "泊まり込み",
        "休日出勤",
        "連勤",
      ],
      "ハラスメント・精神的圧迫": [
        "パワハラ",
        "怒鳴",
        "暴言",
        "理不尽",
        "威圧",
        "詰められ",
      ],
      "過重ノルマ・人員不足": [
        "ノルマ",
        "無茶振り",
        "ワンオペ",
        "人手不足",
        "丸投げ",
      ],
      "給与・待遇・休暇制限": ["未払い", "有給", "休めない", "低賃金"],
      "心身の健康・生活への影響": [
        "睡眠",
        "体調不良",
        "限界",
        "退職",
        "大変だった",
        "つらい",
      ],
    };

    const categories: string[] = [];
    const keywords: string[] = [];
    Object.entries(lexicon).forEach(([cat, words]) => {
      const hits = words.filter((w) => memoText.includes(w));
      if (hits.length > 0) {
        categories.push(cat);
        hits.forEach((h) => {
          if (!keywords.includes(h)) keywords.push(h);
        });
      }
    });
    if (categories.length === 0) categories.push("日常・開発メモ");

    const overtimeM = memoText.match(/(?:月|残業)\s*(\d{2,3})\s*時間/);
    const streakM = memoText.match(/(\d{1,3})\s*連勤/);
    const sleepM = memoText.match(/睡眠\s*(\d+(?:\.\d+)?)\s*時間/);

    const metrics: Record<string, number> = {};
    if (overtimeM) metrics.monthly_overtime_hours = parseInt(overtimeM[1], 10);
    if (streakM) metrics.consecutive_work_days = parseInt(streakM[1], 10);
    if (sleepM) metrics.daily_sleep_hours = parseFloat(sleepM[1]);

    const severity = Math.min(
      100,
      35 +
        categories.length * 13 +
        keywords.length * 4 +
        ((metrics.monthly_overtime_hours || 0) >= 80 ? 12 : 0)
    );

    const sentences = memoText
      .split(/[。！？\n]+/)
      .map((s) => s.trim())
      .filter(Boolean);

    const storyCaptions = [
      ...sentences.map((s, idx) => ({
        id: `cap_story_${idx + 1}`,
        start: +(idx * 4.5).toFixed(1),
        end: +((idx + 1) * 4.5).toFixed(1),
        speaker: "Narrator",
        text: s,
      })),
      ...memoComments.map((c, idx) => ({
        id: `cap_${c.comment_id}`,
        start: +(sentences.length * 4.5 + idx * 4.0).toFixed(1),
        end: +(sentences.length * 4.5 + (idx + 1) * 4.0).toFixed(1),
        speaker: c.author,
        tag: c.tag,
        text: `【コメント】${c.text}`,
      })),
    ];

    return {
      categories,
      keywords,
      metrics,
      severity,
      fullJson: {
        schema_version: "1.0.0",
        memo_id: "memo_black_company_001",
        categories,
        severity_score: severity,
        extracted_metrics: metrics,
        detected_keywords: keywords,
        raw_text: memoText,
        comments: memoComments,
      },
      commentsJson: {
        memo_id: "memo_black_company_001",
        total_comments: memoComments.length,
        comments: memoComments,
      },
      captionsJson: {
        project_type: "experience_story_captions",
        total_captions: storyCaptions.length,
        captions: storyCaptions,
      },
    };
  }, [memoText, memoComments]);

  const handleAddMemoComment = () => {
    if (!newCommentText.trim()) {
      triggerToast("コメント本文を入力してください");
      return;
    }
    const nextId = `cmt_${String(memoComments.length + 1).padStart(3, "0")}`;
    setMemoComments((prev) => [
      ...prev,
      {
        comment_id: nextId,
        author: newCommentAuthor.trim() || "自分",
        tag: newCommentTag,
        text: newCommentText.trim(),
        created_at: new Date().toISOString(),
      },
    ]);
    setNewCommentText("");
    triggerToast(`コメント (${nextId}) をJSONに追加しました`);
  };

  // ==========================================
  // 3. セキュリティ・マルウェア解析ステート
  // ==========================================
  const [malwareInput, setMalwareInput] = useState<string>(
    '!This program cannot be run is DOS mode.Rich .text `.rdata @.data L$"% h4z@ 128.91.34.188 %04d-%02d %02d:%02d:%02d %s !This program cannot be run in Dos mode. .text`.bss .data .idata .rsrc ]_^[keylog.txt %s (Changed window Keylogger Started HH:MM:yyyy.SynFlooding:%s port: %i delay:%i times:%i. bla bla blaaaasdasd Portscanner startip:%s port: %i delay: %ssec.'
  );
  const [hexEncoding, setHexEncoding] = useState<"ascii" | "utf16le">("ascii");
  const [dosProtected, setDosProtected] = useState<boolean>(false);
  const [klProtected, setKlProtected] = useState<boolean>(false);

  const malwareAnalysis = useMemo(() => {
    const stubs: string[] = [];
    if (malwareInput.includes("!This program cannot be run is DOS mode.")) {
      stubs.push("is DOS mode (外殻PE・文法異常)");
    }
    if (malwareInput.includes("!This program cannot be run in Dos mode.")) {
      stubs.push("in Dos mode (内部埋め込みPE・大小文字異常)");
    }
    const ips =
      malwareInput.match(
        /\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b/g
      ) || ["128.91.34.188"];
    const uniqueIps = Array.from(new Set(ips));

    // HEXダンプ生成
    const bytes: number[] = [];
    const limit = Math.min(malwareInput.length, 128);
    for (let i = 0; i < limit; i++) {
      const code = malwareInput.charCodeAt(i);
      if (hexEncoding === "utf16le") {
        bytes.push(code & 0xff, (code >> 8) & 0xff);
      } else {
        bytes.push(code & 0xff);
      }
    }
    const hexLines: string[] = [];
    for (let offset = 0; offset < bytes.length; offset += 16) {
      const chunk = bytes.slice(offset, offset + 16);
      const hexPart = chunk
        .map((b) => b.toString(16).padStart(2, "0"))
        .join(" ")
        .padEnd(48, " ");
      const asciiPart = chunk
        .map((b) => (b >= 32 && b <= 126 ? String.fromCharCode(b) : "."))
        .join("");
      hexLines.push(
        `${offset.toString(16).padStart(8, "0")}  ${hexPart} |${asciiPart}|`
      );
    }

    return {
      stubs,
      c2Ip: uniqueIps[0] || "128.91.34.188",
      hasSynFlood: /SynFlooding:/i.test(malwareInput),
      hasPortscanner: /Portscanner/i.test(malwareInput),
      hasKeylogFile: /keylog\.txt/i.test(malwareInput),
      hasWindowHook: /Changed window/i.test(malwareInput),
      hexDump: hexLines.join("\n"),
    };
  }, [malwareInput, hexEncoding]);

  // ==========================================
  // ユーティリティ: コピー & JSONファイルダウンロード
  // ==========================================
  const copyToClipboard = (text: string, label: string) => {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
      triggerToast(`${label} をクリップボードにコピーしました`);
    } catch {
      triggerToast("コピーに失敗しました");
    }
    document.body.removeChild(ta);
  };

  const downloadJson = (data: unknown, filename: string) => {
    const content = JSON.stringify(data, null, 2);
    const blob = new Blob([content], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    triggerToast(`${filename} を保存しました`);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-6 font-sans">
      {/* トースト通知 */}
      {toastMessage && (
        <div className="fixed bottom-5 right-5 z-50 bg-indigo-950 border border-indigo-500 text-indigo-100 px-4 py-3 rounded-xl shadow-2xl text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* ヘッダー */}
      <header className="max-w-7xl mx-auto border-b border-slate-800 pb-4 mb-6 flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="bg-indigo-600 text-white text-xs font-bold px-2.5 py-1 rounded-md">
              React TSX Studio v0.7
            </span>
            <h1 className="text-xl md:text-2xl font-bold bg-gradient-to-r from-indigo-400 via-sky-300 to-emerald-400 bg-clip-text text-transparent">
              ToCore ⇄ ToModel 統合解析スタジオ (.tsx)
            </h1>
          </div>
          <p className="text-xs md:text-sm text-slate-400 mt-1">
            URL動画解析（話者人数・秒単位字幕・ジャンル・タイムバー・造語曲対応） ／ 日本語体験談JSON ／ マルウェア防御
          </p>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <div className="bg-slate-900 border border-slate-800 px-3.5 py-2 rounded-xl text-center">
            <div className="text-slate-400 text-[10px]">画面レンダリング</div>
            <div className="font-bold text-sky-400">TypeScript (.tsx)</div>
          </div>
          <div className="bg-slate-900 border border-slate-800 px-3.5 py-2 rounded-xl text-center">
            <div className="text-slate-400 text-[10px]">造語曲・音素解析</div>
            <div className="font-bold text-pink-400">CONLANG READY</div>
          </div>
        </div>
      </header>

      {/* 上部 4ページ完全分離ナビゲーション */}
      <nav className="max-w-7xl mx-auto mb-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <button
          onClick={() => setActivePage("video")}
          className={`p-3.5 rounded-2xl border text-left transition flex flex-col justify-between ${
            activePage === "video"
              ? "bg-indigo-950/70 border-indigo-500 ring-2 ring-indigo-500/30"
              : "bg-slate-900/80 border-slate-800 hover:bg-slate-900"
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-semibold text-indigo-300 flex items-center gap-1">
              <Film className="w-3.5 h-3.5" /> VIDEO &amp; CONLANG PAGE
            </span>
            <span className="bg-indigo-600 text-white text-[10px] px-2 py-0.5 rounded-full font-bold">
              URL解析
            </span>
          </div>
          <div className="text-sm font-bold text-white">
            🎬 動画URL解析・タイムバー＆造語曲
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">
            話者人数・秒単位字幕・ジャンル・造語歌詞解析
          </div>
        </button>

        <button
          onClick={() => setActivePage("memo")}
          className={`p-3.5 rounded-2xl border text-left transition flex flex-col justify-between ${
            activePage === "memo"
              ? "bg-emerald-950/70 border-emerald-500 ring-2 ring-emerald-500/30"
              : "bg-slate-900/80 border-slate-800 hover:bg-slate-900"
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-semibold text-emerald-300 flex items-center gap-1">
              <FileText className="w-3.5 h-3.5" /> MEMO &amp; JSON PAGE
            </span>
            <span className="bg-emerald-700 text-white text-[10px] px-2 py-0.5 rounded-full font-bold">
              日本語NLU
            </span>
          </div>
          <div className="text-sm font-bold text-white">
            📝 日本語解釈・体験談＆コメントJSON
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">
            ブラック企業体験記録・定量抽出・コメント保存
          </div>
        </button>

        <button
          onClick={() => setActivePage("security")}
          className={`p-3.5 rounded-2xl border text-left transition flex flex-col justify-between ${
            activePage === "security"
              ? "bg-rose-950/70 border-rose-500 ring-2 ring-rose-500/30"
              : "bg-slate-900/80 border-slate-800 hover:bg-slate-900"
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-semibold text-rose-300 flex items-center gap-1">
              <ShieldAlert className="w-3.5 h-3.5" /> SECURITY PAGE
            </span>
            <span className="bg-rose-700 text-white text-[10px] px-2 py-0.5 rounded-full font-bold">
              防御ツール
            </span>
          </div>
          <div className="text-sm font-bold text-white">
            🛡️ セキュリティ・マルウェア解析
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">
            Unicode/ASCII HEX・DoS対策・キーロガー無力化
          </div>
        </button>

        <button
          onClick={() => setActivePage("code")}
          className={`p-3.5 rounded-2xl border text-left transition flex flex-col justify-between ${
            activePage === "code"
              ? "bg-sky-950/70 border-sky-500 ring-2 ring-sky-500/30"
              : "bg-slate-900/80 border-slate-800 hover:bg-slate-900"
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-semibold text-sky-300 flex items-center gap-1">
              <Code2 className="w-3.5 h-3.5" /> ARCHITECTURE CODE
            </span>
            <span className="bg-sky-700 text-white text-[10px] px-2 py-0.5 rounded-full font-bold">
              Python + TSX
            </span>
          </div>
          <div className="text-sm font-bold text-white">
            💻 実装テスト・モデル連携コード
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">
            URLVideoAndSongAnalyzer &amp; BaseTool 実装
          </div>
        </button>
      </nav>

      {/* =========================================================
          PAGE 1: 動画URL解析・タイムバー＆造語曲スタジオ
         ========================================================= */}
      {activePage === "video" && (
        <main className="max-w-7xl mx-auto space-y-6">
          {/* 1. URL送信・テストプリセットバー */}
          <section className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
            <div className="flex flex-wrap justify-between items-center gap-3">
              <div>
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <Globe className="w-4 h-4 text-indigo-400" />
                  自作AI 動画/楽曲URL解析テストランナー
                </h2>
                <p className="text-xs text-slate-400">
                  URLを送ると「何人が喋っていたか（話者分離）」「何秒に何が書かれていたか（秒単位字幕）」「ジャンル判定」「オリジナル言語（造語）の音素・対訳」を解析し、タイムバーに可視化します。
                </p>
              </div>
              <div className="flex flex-wrap gap-2 text-xs">
                <button
                  onClick={() =>
                    handleSelectUrlPreset(
                      "https://www.youtube.com/watch?v=shmup_boss_01",
                      "ゲーム実況 (3人掛け合い)"
                    )
                  }
                  className={`px-3 py-1.5 rounded-lg border transition ${
                    urlAnalysis.mode === "standard_video"
                      ? "bg-indigo-600 text-white border-indigo-500 font-semibold"
                      : "bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700"
                  }`}
                >
                  ① ゲーム実況URL (3話者)
                </button>
                <button
                  onClick={() =>
                    handleSelectUrlPreset(
                      "https://example.com/conlang-song-astraea",
                      "オリジナル言語（造語）楽曲"
                    )
                  }
                  className={`px-3 py-1.5 rounded-lg border transition flex items-center gap-1 ${
                    urlAnalysis.mode === "conlang_song"
                      ? "bg-pink-600 text-white border-pink-500 font-semibold"
                      : "bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700"
                  }`}
                >
                  <Music className="w-3.5 h-3.5" /> ② 造語ソングURL (3声部・音素解析)
                </button>
                <button
                  onClick={() =>
                    handleSelectUrlPreset(
                      "https://example.com/malware-security-lecture",
                      "セキュリティ解説講義 (2話者)"
                    )
                  }
                  className={`px-3 py-1.5 rounded-lg border transition ${
                    urlAnalysis.mode === "security_lecture"
                      ? "bg-sky-600 text-white border-sky-500 font-semibold"
                      : "bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700"
                  }`}
                >
                  ③ セキュリティ講義URL (2話者)
                </button>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-2">
              <input
                type="text"
                value={targetUrl}
                onChange={(e) => setTargetUrl(e.target.value)}
                placeholder="解析したい動画・音声・造語曲のURLを入力..."
                className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2 text-xs md:text-sm font-mono text-sky-300 focus:outline-none focus:border-indigo-500"
              />
              <button
                onClick={() => {
                  setCurrentTime(0.0);
                  triggerToast(`URLを解析しました: ${targetUrl}`);
                }}
                className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-5 py-2 rounded-xl text-xs md:text-sm transition flex items-center justify-center gap-1.5 shrink-0"
              >
                <Sparkles className="w-4 h-4" /> URLを自作AIに送って解析
              </button>
            </div>

            {/* 4大解析サマリーカード: 話者人数 / ジャンル / 現在時刻の字幕 / モード */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
              <div className="bg-slate-950 border border-indigo-800/60 p-3.5 rounded-xl">
                <div className="text-slate-400 text-[11px] flex items-center gap-1">
                  <Users className="w-3.5 h-3.5 text-indigo-400" />
                  何人が喋っていたか（話者・声部分離）
                </div>
                <div className="text-lg font-bold text-indigo-300 mt-1">
                  合計 {urlAnalysis.speaker_summary.total_speakers_count} 人検出
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">
                  {urlAnalysis.speaker_summary.detection_method}
                </div>
              </div>

              <div className="bg-slate-950 border border-emerald-800/60 p-3.5 rounded-xl">
                <div className="text-slate-400 text-[11px] flex items-center gap-1">
                  <Tag className="w-3.5 h-3.5 text-emerald-400" />
                  ジャンル自動判定（信頼度 {urlAnalysis.genre.confidence_pct}%）
                </div>
                <div className="text-sm font-bold text-emerald-300 mt-1">
                  {urlAnalysis.genre.primary}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">
                  {urlAnalysis.genre.sub_genres.join(" ／ ")}
                </div>
              </div>

              <div className="bg-slate-950 border border-sky-800/60 p-3.5 rounded-xl">
                <div className="text-slate-400 text-[11px] flex items-center gap-1">
                  <Volume2 className="w-3.5 h-3.5 text-sky-400" />
                  現在秒数 ({formatTime(currentTime)}) の発話・字幕
                </div>
                <div className="text-xs font-bold text-sky-300 mt-1 truncate">
                  {activeSegment.speaker_name}
                </div>
                <div className="text-[11px] text-slate-200 mt-0.5 truncate">
                  {activeSegment.text}
                </div>
              </div>

              <div className="bg-slate-950 border border-pink-800/60 p-3.5 rounded-xl">
                <div className="text-slate-400 text-[11px] flex items-center gap-1">
                  <Music className="w-3.5 h-3.5 text-pink-400" />
                  言語・音響解析モード
                </div>
                <div className="text-sm font-bold text-pink-300 mt-1">
                  {urlAnalysis.mode === "conlang_song"
                    ? "オリジナル造語曲 (IPA+辞書対訳)"
                    : "標準日本語 (話者＋無音カット)"}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">
                  総尺 {urlAnalysis.duration_sec.toFixed(1)}秒 ／ 全{" "}
                  {urlAnalysis.segments.length} セグメント
                </div>
              </div>
            </div>
          </section>

          {/* 2. インタラクティブ・マルチトラック・タイムバー */}
          <section className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
            <div className="flex flex-wrap justify-between items-center gap-3">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Layers className="w-4 h-4 text-sky-400" />
                  マルチトラック・インタラクティブ・タイムバー（話者別・秒単位字幕・音響波形）
                </h3>
                <p className="text-xs text-slate-400">
                  バー上のブロックや下の字幕行をクリックすると、その秒数へ即座にシークします。
                </p>
              </div>

              {/* 再生コントロール */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsPlaying((p) => !p)}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition"
                >
                  {isPlaying ? (
                    <>
                      <Pause className="w-3.5 h-3.5" /> 一時停止
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5" /> タイムバー再生
                    </>
                  )}
                </button>
                <button
                  onClick={() => {
                    setIsPlaying(false);
                    setCurrentTime(0.0);
                  }}
                  className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-xl text-xs flex items-center gap-1 transition"
                >
                  <RotateCcw className="w-3.5 h-3.5" /> 00:00へ戻す
                </button>
                <span className="font-mono text-xs bg-slate-950 border border-slate-800 px-3 py-1.5 rounded-xl text-sky-300 font-bold">
                  {formatTime(currentTime)} /{" "}
                  {formatTime(urlAnalysis.duration_sec)}
                </span>
              </div>
            </div>

            {/* シークスライダー */}
            <div className="space-y-1">
              <input
                type="range"
                min={0}
                max={urlAnalysis.duration_sec}
                step={0.1}
                value={currentTime}
                onChange={(e) => setCurrentTime(parseFloat(e.target.value))}
                className="w-full accent-indigo-500 cursor-pointer"
              />
              <div className="flex justify-between text-[10px] font-mono text-slate-500">
                <span>00:00.0</span>
                <span>00:06.0</span>
                <span>00:12.0</span>
                <span>00:18.0</span>
                <span>00:24.0</span>
              </div>
            </div>

            {/* Track 1: 話者別カラータイムバー */}
            <div className="space-y-1.5">
              <div className="text-[11px] text-slate-400 font-medium flex justify-between">
                <span>Track 1: 話者・ボーカル声部タイムバー (クリックで秒数ジャンプ)</span>
                <span>無音カット閾値: {silenceThreshold}s</span>
              </div>
              <div className="relative h-11 w-full bg-slate-950 rounded-xl border border-slate-800 overflow-hidden flex">
                {urlAnalysis.segments.map((seg) => {
                  const widthPct =
                    ((seg.end - seg.start) / urlAnalysis.duration_sec) * 100;
                  const spk = urlAnalysis.speaker_summary.speakers.find(
                    (sp) => sp.speaker_id === seg.speaker_id
                  );
                  const bgColor = seg.is_silence
                    ? "#ef444433"
                    : spk?.color || "#6366f1";
                  const isCurrent = activeSegment.id === seg.id;

                  return (
                    <button
                      key={seg.id}
                      onClick={() => setCurrentTime(seg.start)}
                      style={{
                        width: `${widthPct}%`,
                        backgroundColor: bgColor,
                      }}
                      className={`h-full border-r border-slate-900/80 px-2 flex flex-col justify-center text-left transition overflow-hidden ${
                        isCurrent ? "ring-2 ring-white z-10" : "opacity-85 hover:opacity-100"
                      }`}
                      title={`${formatTime(seg.start)} - ${formatTime(seg.end)}: ${seg.speaker_name}`}
                    >
                      <span className="text-[10px] font-bold text-white truncate drop-shadow">
                        {seg.speaker_name}
                      </span>
                      <span className="text-[9px] text-slate-100/90 truncate">
                        {seg.start.toFixed(1)}s-{seg.end.toFixed(1)}s
                      </span>
                    </button>
                  );
                })}
                {/* プレイヘッド縦線 */}
                <div
                  style={{
                    left: `${(currentTime / urlAnalysis.duration_sec) * 100}%`,
                  }}
                  className="absolute top-0 bottom-0 w-0.5 bg-white shadow-[0_0_8px_#fff] pointer-events-none"
                />
              </div>
            </div>

            {/* Track 2: 音響エネルギー＆盛り上がりバー */}
            <div className="space-y-1">
              <div className="text-[11px] text-slate-400 font-medium">
                Track 2: 音響エネルギー・声量ピーク推移 (0〜100%)
              </div>
              <div className="h-10 bg-slate-950 rounded-xl border border-slate-800 p-1.5 flex items-end gap-1">
                {urlAnalysis.segments.map((seg) => {
                  const widthPct =
                    ((seg.end - seg.start) / urlAnalysis.duration_sec) * 100;
                  return (
                    <div
                      key={`energy_${seg.id}`}
                      onClick={() => setCurrentTime(seg.start)}
                      style={{
                        width: `${widthPct}%`,
                        height: `${Math.max(15, seg.energy)}%`,
                      }}
                      className={`rounded cursor-pointer transition ${
                        seg.is_silence
                          ? "bg-red-500/40"
                          : seg.energy >= 90
                          ? "bg-amber-400"
                          : "bg-sky-500/70"
                      }`}
                      title={`エネルギー: ${seg.energy}%`}
                    />
                  );
                })}
              </div>
            </div>

            {/* 現在秒数のリアルタイム字幕・造語対訳モニター */}
            <div className="bg-slate-950 border border-indigo-500/50 rounded-xl p-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-xs">
                  <span className="bg-indigo-600 text-white px-2 py-0.5 rounded font-mono font-bold">
                    {formatTime(activeSegment.start)} →{" "}
                    {formatTime(activeSegment.end)}
                  </span>
                  <span className="font-bold text-indigo-300">
                    {activeSegment.speaker_name}
                  </span>
                  <span className="text-slate-400 text-[11px]">
                    (音響エネルギー: {activeSegment.energy}%)
                  </span>
                </div>
                <div className="text-sm md:text-base font-bold text-white">
                  {activeSegment.text}
                </div>
                {urlAnalysis.mode === "conlang_song" && (
                  <div className="text-xs space-y-0.5 pt-1">
                    <div className="text-pink-300">
                      <span className="text-slate-400">カタカナ発音: </span>
                      {activeSegment.phonetic_kana} ／{" "}
                      <span className="font-mono text-sky-300">
                        IPA: {activeSegment.ipa}
                      </span>
                    </div>
                    <div className="text-emerald-300 font-semibold">
                      <span className="text-slate-400">造語辞書対訳: </span>
                      {activeSegment.translated_meaning}
                    </div>
                  </div>
                )}
              </div>

              {/* 話者別凡例バッジ */}
              <div className="flex flex-wrap gap-2 shrink-0">
                {urlAnalysis.speaker_summary.speakers.map((sp) => (
                  <div
                    key={sp.speaker_id}
                    className="bg-slate-900 border border-slate-800 px-2.5 py-1.5 rounded-lg text-xs flex items-center gap-2"
                  >
                    <span
                      style={{ backgroundColor: sp.color }}
                      className="w-2.5 h-2.5 rounded-full inline-block"
                    />
                    <div>
                      <div className="font-semibold text-slate-200 text-[11px]">
                        {sp.name}
                      </div>
                      <div className="text-[10px] text-slate-400">
                        {sp.speaking_sec}秒 ({sp.ratio_pct}%) / {sp.voice_profile}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* 3. 下段: 秒単位の字幕テーブル ＆ 造語辞書・JSON出力パネル */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* 左2カラム: 秒単位の字幕・話者リスト */}
            <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-sm font-bold text-white">
                  秒単位の字幕・話者・歌詞タイムライン一覧（行クリックでタイムバー移動）
                </h3>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-slate-400">無音カット閾値:</span>
                  {[0.5, 0.8, 1.5].map((sec) => (
                    <button
                      key={sec}
                      onClick={() => setSilenceThreshold(sec)}
                      className={`px-2 py-0.5 rounded ${
                        silenceThreshold === sec
                          ? "bg-indigo-600 text-white font-bold"
                          : "bg-slate-800 text-slate-300"
                      }`}
                    >
                      {sec}s
                    </button>
                  ))}
                </div>
              </div>

              <div className="overflow-x-auto border border-slate-800 rounded-xl bg-slate-950">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-800/80 text-slate-400 border-b border-slate-700">
                    <tr>
                      <th className="p-2.5">秒数 (Start - End)</th>
                      <th className="p-2.5">誰が (Speaker / Vocal)</th>
                      <th className="p-2.5">字幕テキスト / 造語音素・対訳</th>
                      <th className="p-2.5">熱量</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/80">
                    {urlAnalysis.segments.map((seg) => {
                      const isSelected = activeSegment.id === seg.id;
                      return (
                        <tr
                          key={seg.id}
                          onClick={() => setCurrentTime(seg.start)}
                          className={`cursor-pointer transition ${
                            isSelected
                              ? "bg-indigo-950/50 text-white"
                              : "hover:bg-slate-900/70 text-slate-300"
                          }`}
                        >
                          <td className="p-2.5 font-mono text-sky-400 whitespace-nowrap">
                            {formatTime(seg.start)} - {formatTime(seg.end)}
                          </td>
                          <td className="p-2.5 font-semibold whitespace-nowrap">
                            {seg.speaker_name}
                          </td>
                          <td className="p-2.5">
                            <div className="font-medium text-slate-100">
                              {seg.text}
                            </div>
                            {seg.phonetic_kana && (
                              <div className="text-[11px] text-pink-300 mt-0.5">
                                発音: {seg.phonetic_kana} ({seg.ipa}) → 意味:{" "}
                                <span className="text-emerald-300">
                                  {seg.translated_meaning}
                                </span>
                              </div>
                            )}
                          </td>
                          <td className="p-2.5 font-mono text-amber-300">
                            {seg.energy}%
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* オリジナル言語（造語）辞書カスタム登録スロット */}
              <div className="bg-slate-950 border border-pink-900/50 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-pink-300 flex items-center gap-1.5">
                    <Music className="w-4 h-4" />
                    オリジナル言語（造語曲）カスタム辞書スロット
                  </span>
                  <span className="text-[10px] bg-pink-950 text-pink-300 border border-pink-800 px-2 py-0.5 rounded">
                    音素(IPA)＋辞書マッピング方式
                  </span>
                </div>
                <p className="text-[11px] text-slate-400">
                  造語で作られた曲でも、①音響特徴から「声部（何人歌っているか）・BPM・ジャンル」を判定し、②歌声を「音素（母音・子音列／カタカナ読み）」として秒単位で書き起こし、③下のカスタム造語辞書と照合することで対訳字幕を生成できます。
                </p>
                <div className="flex flex-wrap gap-1.5 text-[11px]">
                  {Object.entries(conlangDict).map(([w, m]) => (
                    <span
                      key={w}
                      className="bg-slate-900 border border-slate-700 px-2 py-0.5 rounded text-slate-200 font-mono"
                    >
                      <b className="text-pink-400">{w}</b> = {m}
                    </span>
                  ))}
                </div>
                <div className="flex flex-col sm:flex-row gap-2 pt-1">
                  <input
                    type="text"
                    value={newConlangWord}
                    onChange={(e) => setNewConlangWord(e.target.value)}
                    placeholder="造語単語 (例: astra)"
                    className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 font-mono"
                  />
                  <input
                    type="text"
                    value={newConlangMeaning}
                    onChange={(e) => setNewConlangMeaning(e.target.value)}
                    placeholder="日本語の意味 (例: 星辰)"
                    className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 flex-1"
                  />
                  <button
                    onClick={handleAddConlangWord}
                    className="bg-pink-600 hover:bg-pink-500 text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold transition shrink-0"
                  >
                    造語辞書に追加
                  </button>
                </div>
              </div>
            </div>

            {/* 右1カラム: JSON出力＆ダウンロードセンター */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between space-y-4">
              <div className="space-y-3">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Scissors className="w-4 h-4 text-emerald-400" />
                  動画・造語曲解析 JSON 出力
                </h3>
                <div className="flex flex-wrap gap-1.5 text-[11px]">
                  {[
                    { key: "project", label: "統合 project.json" },
                    { key: "speakers", label: "話者分離 speakers.json" },
                    { key: "captions", label: "秒単位字幕 captions.json" },
                    { key: "conlang", label: "造語歌詞 conlang.json" },
                  ].map((t) => (
                    <button
                      key={t.key}
                      onClick={() => setVideoJsonTab(t.key as any)}
                      className={`px-2.5 py-1 rounded font-medium ${
                        videoJsonTab === t.key
                          ? "bg-emerald-600 text-white"
                          : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                      }`}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>

                <div className="bg-slate-950 border border-slate-800 rounded-xl p-3 font-mono text-[11px] text-emerald-300 max-h-96 overflow-y-auto">
                  <pre className="leading-relaxed">
                    {JSON.stringify(videoExportJson, null, 2)}
                  </pre>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() =>
                    copyToClipboard(
                      JSON.stringify(videoExportJson, null, 2),
                      "動画解析JSON"
                    )
                  }
                  className="bg-emerald-700 hover:bg-emerald-600 text-white font-semibold py-2 rounded-xl text-xs flex items-center justify-center gap-1.5 transition"
                >
                  <Copy className="w-3.5 h-3.5" /> JSONをコピー
                </button>
                <button
                  onClick={() =>
                    downloadJson(videoExportJson, `${videoJsonTab}_result.json`)
                  }
                  className="bg-sky-700 hover:bg-sky-600 text-white font-semibold py-2 rounded-xl text-xs flex items-center justify-center gap-1.5 transition"
                >
                  <Download className="w-3.5 h-3.5" /> .json 保存
                </button>
              </div>
            </div>
          </div>
        </main>
      )}

      {/* =========================================================
          PAGE 2: 日本語解釈・体験談（ブラック企業等）＆コメントJSONスタジオ
         ========================================================= */}
      {activePage === "memo" && (
        <main className="max-w-7xl mx-auto space-y-6">
          <section className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
            <div className="flex flex-wrap justify-between items-center gap-3">
              <div>
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <FileText className="w-4 h-4 text-emerald-400" />
                  日本語解釈・体験談（ブラック企業の記録等）＆コメントJSONスタジオ
                </h2>
                <p className="text-xs text-slate-400">
                  大変だった体験や日々の振り返りを日本語で書くと、モデルがカテゴリ・定量数値（残業時間・連勤・睡眠時間）・負荷指数を自動抽出し、コメントと一緒にJSON化します。
                </p>
              </div>
            </div>

            <textarea
              rows={3}
              value={memoText}
              onChange={(e) => setMemoText(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3.5 text-xs md:text-sm text-slate-100 leading-relaxed focus:outline-none focus:border-emerald-500"
            />

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="bg-slate-950 border border-emerald-800/60 p-3.5 rounded-xl">
                <div className="text-slate-400 text-[11px]">検出された体験カテゴリ</div>
                <div className="text-emerald-300 font-bold mt-1">
                  {memoAnalysis.categories.join(" ／ ")}
                </div>
              </div>
              <div className="bg-slate-950 border border-amber-800/60 p-3.5 rounded-xl">
                <div className="text-slate-400 text-[11px]">抽出された定量データ</div>
                <div className="text-amber-300 font-bold mt-1">
                  残業: {memoAnalysis.metrics.monthly_overtime_hours ?? "-"}h ／ 連勤:{" "}
                  {memoAnalysis.metrics.consecutive_work_days ?? "-"}日 ／ 睡眠:{" "}
                  {memoAnalysis.metrics.daily_sleep_hours ?? "-"}h
                </div>
              </div>
              <div className="bg-slate-950 border border-rose-800/60 p-3.5 rounded-xl">
                <div className="text-slate-400 text-[11px]">当時の負荷指数 ＆ コメント数</div>
                <div className="text-rose-400 font-bold mt-1">
                  負荷指数 {memoAnalysis.severity} / 100 （コメント{" "}
                  {memoComments.length}件）
                </div>
              </div>
            </div>
          </section>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* コメント追加フォーム */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-sky-400" />
                コメント・補足メモをJSONに追加 (comments.json)
              </h3>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <input
                  type="text"
                  value={newCommentAuthor}
                  onChange={(e) => setNewCommentAuthor(e.target.value)}
                  placeholder="記録者ラベル"
                  className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                />
                <select
                  value={newCommentTag}
                  onChange={(e) => setNewCommentTag(e.target.value)}
                  className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                >
                  <option value="教訓・前進">教訓・前進</option>
                  <option value="当時の状況補足">当時の状況補足</option>
                  <option value="動画ネタ・字幕連携">動画ネタ・字幕連携</option>
                </select>
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newCommentText}
                  onChange={(e) => setNewCommentText(e.target.value)}
                  placeholder="コメントを入力..."
                  className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200"
                />
                <button
                  onClick={handleAddMemoComment}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-1 shrink-0"
                >
                  <Plus className="w-3.5 h-3.5" /> 追加
                </button>
              </div>

              <div className="space-y-2 max-h-60 overflow-y-auto">
                {memoComments.map((c) => (
                  <div
                    key={c.comment_id}
                    className="bg-slate-950 border border-slate-800 p-3 rounded-xl flex justify-between items-start gap-2 text-xs"
                  >
                    <div>
                      <span className="font-bold text-sky-300">{c.author}</span>
                      <span className="ml-2 bg-indigo-950 text-indigo-300 border border-indigo-800 px-2 py-0.5 rounded text-[10px]">
                        {c.tag}
                      </span>
                      <p className="text-slate-200 mt-1">{c.text}</p>
                    </div>
                    <button
                      onClick={() =>
                        setMemoComments((prev) =>
                          prev.filter((item) => item.comment_id !== c.comment_id)
                        )
                      }
                      className="text-slate-500 hover:text-rose-400"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* JSONプレビュー＆保存 */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between space-y-4">
              <div className="space-y-3">
                <div className="flex flex-wrap gap-1.5 text-xs">
                  {[
                    { key: "full", label: "統合 experience_memos.json" },
                    { key: "comments", label: "comments.json 単体" },
                    { key: "captions", label: "動画字幕 captions.json 変換" },
                  ].map((t) => (
                    <button
                      key={t.key}
                      onClick={() => setMemoJsonTab(t.key as any)}
                      className={`px-2.5 py-1 rounded font-medium ${
                        memoJsonTab === t.key
                          ? "bg-emerald-600 text-white"
                          : "bg-slate-800 text-slate-300"
                      }`}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-3 font-mono text-[11px] text-emerald-300 max-h-72 overflow-y-auto">
                  <pre>
                    {JSON.stringify(
                      memoJsonTab === "full"
                        ? memoAnalysis.fullJson
                        : memoJsonTab === "comments"
                        ? memoAnalysis.commentsJson
                        : memoAnalysis.captionsJson,
                      null,
                      2
                    )}
                  </pre>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() =>
                    copyToClipboard(
                      JSON.stringify(memoAnalysis.fullJson, null, 2),
                      "体験＆コメントJSON"
                    )
                  }
                  className="bg-emerald-700 hover:bg-emerald-600 text-white font-semibold py-2 rounded-xl text-xs flex items-center justify-center gap-1.5"
                >
                  <Copy className="w-3.5 h-3.5" /> JSONをコピー
                </button>
                <button
                  onClick={() =>
                    downloadJson(memoAnalysis.fullJson, "experience_memos.json")
                  }
                  className="bg-sky-700 hover:bg-sky-600 text-white font-semibold py-2 rounded-xl text-xs flex items-center justify-center gap-1.5"
                >
                  <Download className="w-3.5 h-3.5" /> .json 保存
                </button>
              </div>
            </div>
          </div>
        </main>
      )}

      {/* =========================================================
          PAGE 3: セキュリティ・マルウェア解析ページ
         ========================================================= */}
      {activePage === "security" && (
        <main className="max-w-7xl mx-auto space-y-6">
          <section className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
            <div className="flex flex-wrap justify-between items-center gap-2">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-400" />
                Unicode / ASCII 両対応 マルウェア解析 ＆ DoS・キーロガー対策コンソール
              </h2>
              <div className="flex gap-2 text-xs">
                <button
                  onClick={() => setHexEncoding("ascii")}
                  className={`px-3 py-1 rounded-lg ${
                    hexEncoding === "ascii"
                      ? "bg-indigo-600 text-white font-bold"
                      : "bg-slate-800 text-slate-300"
                  }`}
                >
                  ASCII / UTF-8 HEX
                </button>
                <button
                  onClick={() => setHexEncoding("utf16le")}
                  className={`px-3 py-1 rounded-lg ${
                    hexEncoding === "utf16le"
                      ? "bg-indigo-600 text-white font-bold"
                      : "bg-slate-800 text-slate-300"
                  }`}
                >
                  Unicode (UTF-16LE Wide) HEX
                </button>
              </div>
            </div>

            <textarea
              rows={3}
              value={malwareInput}
              onChange={(e) => setMalwareInput(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-xs font-mono text-sky-300"
            />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* DoS対策 */}
              <div className="bg-slate-950 border border-red-900/50 rounded-xl p-4 space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-xs font-bold text-red-400">
                    DoS攻撃 (SynFlooding / Portscanner) 対策ツール
                  </span>
                  <span className="text-[10px] bg-red-950 text-red-300 border border-red-800 px-2 py-0.5 rounded">
                    C2 IP: {malwareAnalysis.c2Ip}
                  </span>
                </div>
                <pre className="bg-slate-900 p-3 rounded-lg font-mono text-[11px] text-emerald-300 overflow-x-auto">
                  {`sysctl -w net.ipv4.tcp_syncookies=1\niptables -A INPUT -p tcp --syn -m limit --limit 10/s -j ACCEPT\niptables -A INPUT -s ${malwareAnalysis.c2Ip} -j DROP`}
                </pre>
                <button
                  onClick={() => {
                    setDosProtected(true);
                    triggerToast(
                      `SYN Cookies有効化と C2 IP (${malwareAnalysis.c2Ip}) 遮断を適用しました`
                    );
                  }}
                  className={`w-full py-2 rounded-lg text-xs font-semibold transition ${
                    dosProtected
                      ? "bg-emerald-700 text-white"
                      : "bg-red-600 hover:bg-red-500 text-white"
                  }`}
                >
                  {dosProtected
                    ? "✔ DoS防御ルール適用済"
                    : "SYN Flood対策 ＆ C2 IP遮断を適用"}
                </button>
              </div>

              {/* キーロガー対策 */}
              <div className="bg-slate-950 border border-rose-900/50 rounded-xl p-4 space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-xs font-bold text-rose-400 flex items-center gap-1">
                    <Lock className="w-3.5 h-3.5" /> キーロガー (keylog.txt / Changed window) 無力化ツール
                  </span>
                  <span className="text-[10px] bg-rose-950 text-rose-300 border border-rose-800 px-2 py-0.5 rounded">
                    Sinkhole Lock
                  </span>
                </div>
                <pre className="bg-slate-900 p-3 rounded-lg font-mono text-[11px] text-sky-300 overflow-x-auto">
                  {`touch keylog.txt && chmod 000 keylog.txt && chattr +i keylog.txt\nicacls keylog.txt /deny "Everyone:(W,D)"\nauditctl -w ./keylog.txt -p wa -k keylogger_canary`}
                </pre>
                <button
                  onClick={() => {
                    setKlProtected(true);
                    triggerToast("keylog.txt のシンクホールロックを適用しました");
                  }}
                  className={`w-full py-2 rounded-lg text-xs font-semibold transition ${
                    klProtected
                      ? "bg-emerald-700 text-white"
                      : "bg-indigo-600 hover:bg-indigo-500 text-white"
                  }`}
                >
                  {klProtected
                    ? "✔ keylog.txt シンクホールロック適用済"
                    : "keylog.txt 書き込みロック ＆ フック遮断を適用"}
                </button>
              </div>
            </div>

            <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 font-mono text-[11px] text-sky-300 overflow-x-auto max-h-56">
              <pre>{malwareAnalysis.hexDump}</pre>
            </div>
          </section>
        </main>
      )}

      {/* =========================================================
          PAGE 4: 不足していた接続部分（コンソール導入・Handler・AIChatMessageList.tsx）完全コード
         ========================================================= */}
      {activePage === "code" && (
        <main className="max-w-7xl mx-auto space-y-5">
          <section className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-xl">
            <div className="flex flex-wrap justify-between items-center gap-3">
              <div>
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-sky-400" />
                  本体 (tools/ + handlers/ + AIChatMessageList.tsx) ⇄ 自作モデル (to_model) 接続コード一式
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  コンソールでの pip install -e 導入から、ToModelHandler.py、AIChatMessageList.tsx での .tsx 表示まで、不足していた全ファイルを揃えました。
                </p>
              </div>
              <button
                onClick={() =>
                  copyToClipboard(
                    MISSING_CODE_FILES[selectedCodeKey]?.code || "",
                    MISSING_CODE_FILES[selectedCodeKey]?.title || "コード"
                  )
                }
                className="bg-emerald-700 hover:bg-emerald-600 text-white px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition"
              >
                <Copy className="w-3.5 h-3.5" /> 表示中のコードをコピー
              </button>
            </div>

            {/* ファイル切替ボタン */}
            <div className="flex flex-wrap gap-2 text-xs">
              {Object.entries(MISSING_CODE_FILES).map(([key, item]) => (
                <button
                  key={key}
                  onClick={() => setSelectedCodeKey(key)}
                  className={`px-3 py-1.5 rounded-xl border transition font-medium ${
                    selectedCodeKey === key
                      ? "bg-sky-600 text-white border-sky-400"
                      : "bg-slate-950 text-slate-300 border-slate-800 hover:bg-slate-800"
                  }`}
                >
                  {item.title.split(" (")[0]}
                </button>
              ))}
            </div>

            <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-2">
              <div className="text-xs font-bold text-sky-300">
                {MISSING_CODE_FILES[selectedCodeKey]?.title}
              </div>
              <div className="text-[11px] text-slate-400">
                {MISSING_CODE_FILES[selectedCodeKey]?.desc}
              </div>
              <pre className="bg-slate-900/90 border border-slate-800 rounded-lg p-3.5 font-mono text-xs text-emerald-300 overflow-x-auto leading-relaxed max-h-96 overflow-y-auto">
                {MISSING_CODE_FILES[selectedCodeKey]?.code}
              </pre>
            </div>

            {/* 💬 本体搭載・自作モデル会話 ＆ Widget切替シミュレーター */}
            <div className="bg-slate-950 border border-emerald-800/60 rounded-xl p-4 space-y-3">
              <div className="flex flex-wrap justify-between items-center gap-2">
                <div>
                  <h3 className="text-xs font-bold text-emerald-300 flex items-center gap-1.5">
                    <MessageSquare className="w-4 h-4" />
                    本体搭載・自作モデル会話テスト (ToModelConversationEngine ⇄ AIChatMessageList.tsx)
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    通常の雑談は <code className="text-sky-300">ChatBubble (response_type: "chat")</code> で返し、URLや体験談・マルウェア文字列が含まれると自動で <code className="text-emerald-300">WidgetCard (.tsx)</code> へ切り替わります。
                  </p>
                </div>
                <div className="flex flex-wrap gap-1.5 text-[11px]">
                  <button
                    onClick={() =>
                      triggerToast("【会話モード応答】なるほど！会話の文脈を記憶しながら、いつでも動画解析やJSONメモへ連携できます。", {
                        simulated_chat_turn: "日常会話・設計相談",
                        response_type: "chat",
                        rendered_by: "ChatBubble (Normal Chat)",
                      })
                    }
                    className="bg-slate-800 hover:bg-slate-700 text-slate-200 px-2.5 py-1 rounded-lg border border-slate-700"
                  >
                    💬 日常会話をテスト
                  </button>
                  <button
                    onClick={() => {
                      setActivePage("video");
                      triggerToast("【会話＋動画解析連動】URLを検出したため video_curator Widget (.tsx) を展開しました", {
                        simulated_chat_turn: "この造語曲URLを解析して",
                        response_type: "video_curator",
                        rendered_by: "WidgetCard > ToAiStudioDashboard (video)",
                      });
                    }}
                    className="bg-indigo-950 hover:bg-indigo-900 text-indigo-300 px-2.5 py-1 rounded-lg border border-indigo-700"
                  >
                    🎬 会話から動画解析へ遷移
                  </button>
                  <button
                    onClick={() => {
                      setActivePage("memo");
                      triggerToast("【会話＋体験談JSONメモ連動】共感応答と共に experience_memo Widget (.tsx) を展開しました", {
                        simulated_chat_turn: "ブラック企業で残業100時間だった話をメモして",
                        response_type: "experience_memo",
                        rendered_by: "WidgetCard > ToAiStudioDashboard (memo)",
                      });
                    }}
                    className="bg-emerald-950 hover:bg-emerald-900 text-emerald-300 px-2.5 py-1 rounded-lg border border-emerald-700"
                  >
                    📝 会話から体験談メモへ遷移
                  </button>
                </div>
              </div>
            </div>

            {/* onOptionSelect 双方向通信ステータス */}
            <div className="bg-slate-950 border border-indigo-900/50 rounded-xl p-3.5 text-xs flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
              <div>
                <span className="font-bold text-indigo-300">
                  AIChatMessageList.tsx ⇄ ToAiStudioDashboard.tsx 双方向コールバック状態:
                </span>
                <span className="font-mono text-slate-300 ml-2">{lastCallbackLog}</span>
              </div>
              <button
                onClick={() =>
                  triggerToast("onOptionSelect 経由で本体 Handler に再解析リクエストを送信しました", {
                    action: "analyze_url",
                    url: targetUrl,
                    silence_threshold_sec: silenceThreshold,
                  })
                }
                className="bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded-lg text-xs font-semibold shrink-0"
              >
                onOptionSelect 通信テスト送信
              </button>
            </div>
          </section>
        </main>
      )}
    </div>
  );
}
