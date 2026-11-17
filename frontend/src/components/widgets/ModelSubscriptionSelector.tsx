// frontend/src/components/widgets/ModelSubscriptionSelector.tsx
import React, { useState, useEffect } from "react";
import {
  Crown,
  Sparkles,
  Lock,
  CheckCircle2,
  Zap,
  ShieldCheck,
  Cpu,
  CreditCard,
  RefreshCw,
} from "lucide-react";

export interface AIModelOption {
  id: string;
  name: string;
  tier: "free" | "pro";
  speed: string;
  power_usage: string;
  description: string;
}

export interface SubscriptionState {
  plan: "free" | "pro_1yen";
  price_jpy: number;
  selected_model: string;
  subscribed_at: string | null;
  auto_renew: boolean;
  available_models: AIModelOption[];
}

const FALLBACK_STATE: SubscriptionState = {
  plan: "free",
  price_jpy: 0,
  selected_model: "to_model_local",
  subscribed_at: null,
  auto_renew: false,
  available_models: [
    {
      id: "to_model_local",
      name: "🌱 To_model Standard (Local + KnowledgeRouter)",
      tier: "free",
      speed: "超高速 (0.1秒)",
      power_usage: "極小 (Green AI)",
      description: "決定論的ルーターと共同学習エンジンで動く省電力・無料の標準モデル",
    },
    {
      id: "ollama_qwen_local",
      name: "🦙 Local LLM (Ollama / Qwen-Coder)",
      tier: "free",
      speed: "中速 (ローカル推論)",
      power_usage: "中",
      description: "オフライン環境でコード生成や要約を行うローカル推論モデル",
    },
    {
      id: "to_model_pro_hybrid",
      name: "👑 To_model Pro (Gemini大先輩ハイブリッド推論 + 深掘りRAG)",
      tier: "pro",
      speed: "高速・高精度",
      power_usage: "最適化済",
      description: "月額1円サブスク限定！長文要約・図解OCR深掘り・高度な価値観討論をフル解放",
    },
    {
      id: "to_model_ultra_agent",
      name: "🚀 To_model Ultra Agent (マルチハンドラー自律検証)",
      tier: "pro",
      speed: "高精度マルチステップ",
      power_usage: "高",
      description: "月額1円サブスク限定！複数ファイルの自動設計・セキュリティ深層解析・無制限チャンク検索",
    },
  ],
};

export interface ModelSubscriptionSelectorProps {
  apiBaseUrl?: string;
  onModelChange?: (modelId: string, plan: "free" | "pro_1yen") => void;
}

export default function ModelSubscriptionSelector({
  apiBaseUrl = "",
  onModelChange,
}: ModelSubscriptionSelectorProps) {
  const [subState, setSubState] = useState<SubscriptionState>(FALLBACK_STATE);
  const [showCheckoutModal, setShowCheckoutModal] = useState(false);
  const [pendingProModelId, setPendingProModelId] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const base = apiBaseUrl.replace(/\/+$/, "");

  useEffect(() => {
    fetch(`${base}/api/to/subscription/status`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && data.available_models) {
          setSubState(data);
        }
      })
      .catch(() => {});
  }, [base]);

  const isPro = subState.plan === "pro_1yen";

  // モデルカードをクリックしたときの処理
  const handleSelectModel = async (model: AIModelOption) => {
    // 無料プランなのに有料(pro)モデルを選んだ場合は1円サブスク案内モーダルを開く
    if (model.tier === "pro" && !isPro) {
      setPendingProModelId(model.id);
      setShowCheckoutModal(true);
      return;
    }

    try {
      const res = await fetch(`${base}/api/to/subscription/select-model`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_id: model.id }),
      });
      if (res.ok) {
        const data = await res.json();
        setSubState(data.state);
        setToastMsg(data.message);
        onModelChange?.(model.id, data.state.plan);
        return;
      }
    } catch {}

    // オフラインフォールバック
    setSubState((prev) => ({ ...prev, selected_model: model.id }));
    setToastMsg(`使用モデルを「${model.name}」に切り替えました！`);
    onModelChange?.(model.id, subState.plan);
  };

  // 月額1円サブスクの契約実行
  const handleSubscribeOneYen = async () => {
    setIsProcessing(true);
    try {
      const res = await fetch(`${base}/api/to/subscription/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "subscribe_1yen",
          payment_method: "demo_instant",
        }),
      });
      if (res.ok) {
        const data = await res.json();
        const nextModel = pendingProModelId || "to_model_pro_hybrid";
        setSubState({ ...data.state, selected_model: nextModel });
        setToastMsg(data.message);
        setShowCheckoutModal(false);
        setIsProcessing(false);
        onModelChange?.(nextModel, "pro_1yen");
        return;
      }
    } catch {}

    // オフラインフォールバック
    const nextModel = pendingProModelId || "to_model_pro_hybrid";
    setSubState((prev) => ({
      ...prev,
      plan: "pro_1yen",
      price_jpy: 1,
      subscribed_at: new Date().toLocaleString("ja-JP"),
      auto_renew: true,
      selected_model: nextModel,
    }));
    setToastMsg("🎉 月額1円サブスク（Proプラン）が有効化され、有料モデルが解放されました！");
    setShowCheckoutModal(false);
    setIsProcessing(false);
    onModelChange?.(nextModel, "pro_1yen");
  };

  // サブスク解約処理
  const handleCancelSubscription = async () => {
    try {
      const res = await fetch(`${base}/api/to/subscription/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "cancel" }),
      });
      if (res.ok) {
        const data = await res.json();
        setSubState(data.state);
        setToastMsg(data.message);
        onModelChange?.("to_model_local", "free");
        return;
      }
    } catch {}

    setSubState((prev) => ({
      ...prev,
      plan: "free",
      price_jpy: 0,
      auto_renew: false,
      selected_model: "to_model_local",
    }));
    setToastMsg("無料プラン（To_model Standard）へ戻しました。");
    onModelChange?.("to_model_local", "free");
  };

  return (
    <div className="space-y-5 bg-slate-900 border border-slate-800 rounded-2xl p-5 text-slate-100">
      {/* 1. ヘッダー ＆ 現在の契約プランバッジ */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-amber-400 flex items-center gap-2">
              <Crown className="w-5 h-5" />
              AIモデル選択 ＆ 月額1円サブスクリプション管理
            </h2>
            <span
              className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                isPro
                  ? "bg-amber-500/20 border border-amber-400/50 text-amber-300"
                  : "bg-slate-800 border border-slate-700 text-slate-300"
              }`}
            >
              {isPro ? "👑 Proプラン契約中 (月額1円)" : "🌱 無料プラン (Free)"}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Python (FastAPI) ＋ React だけで動作するモデル切り替え＆サブスク管理画面です（Java / Go 不要）。
          </p>
        </div>

        {/* 右側：ワンクリックで1円サブスク登録 or 解約 */}
        <div>
          {isPro ? (
            <div className="flex items-center gap-3">
              <span className="text-[11px] text-slate-400">
                契約日: {subState.subscribed_at || "本日"}
              </span>
              <button
                type="button"
                onClick={handleCancelSubscription}
                className="rounded-xl border border-slate-700 bg-slate-950 hover:bg-rose-950/60 hover:border-rose-700 px-3 py-1.5 text-xs text-slate-300 hover:text-rose-200 transition"
              >
                無料プランに戻す
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setShowCheckoutModal(true)}
              className="rounded-xl bg-gradient-to-r from-amber-500 to-indigo-600 hover:from-amber-400 hover:to-indigo-500 px-4 py-2 text-xs font-bold text-white shadow-lg flex items-center gap-1.5 transition"
            >
              <Sparkles className="w-4 h-4" />
              <span>月額1円で有料モデルをすべて解放する</span>
            </button>
          )}
        </div>
      </div>

      {/* トースト通知 */}
      {toastMsg && (
        <div className="rounded-xl bg-emerald-950/70 border border-emerald-600/50 px-4 py-2.5 text-xs text-emerald-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{toastMsg}</span>
          </div>
          <button
            type="button"
            onClick={() => setToastMsg(null)}
            className="text-emerald-400 hover:text-white text-[11px]"
          >
            閉じる
          </button>
        </div>
      )}

      {/* 2. 無料モデル / 有料モデル 選択グリッド */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {subState.available_models.map((model) => {
          const isSelected = subState.selected_model === model.id;
          const isLocked = model.tier === "pro" && !isPro;

          return (
            <div
              key={model.id}
              onClick={() => handleSelectModel(model)}
              className={`cursor-pointer rounded-2xl border p-4 transition relative flex flex-col justify-between gap-3 ${
                isSelected
                  ? "bg-indigo-950/50 border-indigo-400 ring-2 ring-indigo-500/30"
                  : isLocked
                  ? "bg-slate-950/60 border-slate-800/80 opacity-75 hover:opacity-100 hover:border-amber-500/50"
                  : "bg-slate-950 border-slate-800 hover:border-slate-600"
              }`}
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      model.tier === "pro"
                        ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                        : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                    }`}
                  >
                    {model.tier === "pro" ? "👑 有料モデル (月額1円)" : "🌱 無料モデル (0円)"}
                  </span>

                  {isSelected ? (
                    <span className="inline-flex items-center gap-1 text-xs font-bold text-indigo-300">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      現在使用中
                    </span>
                  ) : isLocked ? (
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-400">
                      <Lock className="w-3.5 h-3.5" />
                      クリックして1円で解放
                    </span>
                  ) : (
                    <span className="text-[11px] text-slate-400">クリックで選択</span>
                  )}
                </div>

                <h3 className="text-sm font-bold text-white">{model.name}</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  {model.description}
                </p>
              </div>

              <div className="flex items-center gap-3 pt-2 border-t border-slate-800/80 text-[11px] text-slate-400">
                <span className="flex items-center gap-1">
                  <Zap className="w-3.5 h-3.5 text-sky-400" />
                  速度: {model.speed}
                </span>
                <span className="flex items-center gap-1">
                  <Cpu className="w-3.5 h-3.5 text-emerald-400" />
                  電力負荷: {model.power_usage}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* 3. 月額1円サブスク チェックアウト確認モーダル */}
      {showCheckoutModal && (
        <div
          onClick={() => setShowCheckoutModal(false)}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="max-w-md w-full rounded-2xl bg-slate-900 border border-amber-500/50 p-6 shadow-2xl space-y-4"
          >
            <div className="flex items-center gap-2 text-amber-400 font-bold text-base">
              <Crown className="w-5 h-5" />
              <span>To_model Pro 月額1円サブスクリプション</span>
            </div>

            <div className="rounded-xl bg-slate-950 border border-slate-800 p-4 space-y-2">
              <div className="flex items-baseline justify-between">
                <span className="text-xs text-slate-400">月額料金（税込）</span>
                <span className="text-2xl font-extrabold text-amber-300">
                  ¥1 <span className="text-xs font-normal text-slate-400">/ 月</span>
                </span>
              </div>
              <ul className="text-xs text-slate-300 space-y-1.5 pt-2 border-t border-slate-800">
                <li>✅ To_model Pro（Gemini大先輩ハイブリッド推論）無制限利用</li>
                <li>✅ To_model Ultra Agent（自律マルチハンドラー）解放</li>
                <li>✅ スクレイピング図解OCR＆YouTube主張チャンク検索の上限拡大</li>
                <li>✅ いつでもワンクリックで無料プランへ解約可能</li>
              </ul>
            </div>

            <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>
                Python (FastAPI) バックエンドの `/api/to/subscription/checkout` と即時連動します。
              </span>
            </div>

            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowCheckoutModal(false)}
                className="flex-1 rounded-xl border border-slate-700 bg-slate-800 py-2.5 text-xs font-semibold text-slate-300 hover:bg-slate-700"
              >
                キャンセル
              </button>
              <button
                type="button"
                disabled={isProcessing}
                onClick={handleSubscribeOneYen}
                className="flex-1 rounded-xl bg-gradient-to-r from-amber-500 to-indigo-600 hover:from-amber-400 hover:to-indigo-500 py-2.5 text-xs font-bold text-white flex items-center justify-center gap-1.5 shadow-lg"
              >
                {isProcessing ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <CreditCard className="w-4 h-4" />
                )}
                <span>月額1円で今すぐ解放する</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}