// frontend/src/components/AiChatPanel.tsx
import React, { useEffect, useRef, useState } from 'react';
import { CHAT_MODES, useAiChat } from '../hooks/useAiChat';
import AiChatHeader from './AiChatHeader';
import AiChatMessageList from './AiChatMessageList';
import AiChatInput from './AiChatInput';
import MemoryDrawer from './MemoryDrawer';
import ZipUploadModal from './ZipUploadModal';
import ManualEditModal from './ManualEditModal';
import HighRatedModal from './HighRatedModal';

// 分散化した設定メニュー・サブスク・ガチャモジュールをインポート
import {
  GearPopupMenu,
  SettingsSubModals,
  INITIAL_PUBLIC_LINKS,
  exportImportantDataJson,
} from './settings_menu';
import type { GearSubModalType } from './settings_menu';
import {
  SubscriptionModal,
  INITIAL_SUB_STATE,
  GACHA_POOL,
} from './subscription';
import type { SubscriptionState, GachaItem } from './subscription';

const MEMORY_TYPES = [
  'project',
  'rule',
  'knowledge',
  'experience',
  'template',
  'vector',
] as const;

type MemoryType = (typeof MEMORY_TYPES)[number];
type MemoriesState = Record<MemoryType, unknown>;

interface Screenshot {
  id: string;
  filename?: string;
  uri?: string | null;
  mime?: string;
  createdAt?: string;
  dataUrl?: string;
  pending?: boolean;
}

interface VsCodeApi {
  postMessage: (message: unknown) => void;
}

declare global {
  interface Window {
    acquireVsCodeApi?: () => VsCodeApi;
  }
}

interface ChatMessageLike {
  type?: string;
  content?: any;
  text?: any;
  blocks?: unknown[];
}

export interface AiChatPanelProps {
  onImportDB?: (historyName: string) => void;
  onCreateDB?: () => void;
  onOpenManualEdit?: (block: unknown) => void;
}

const createEmptyMemories = (): MemoriesState => ({
  project: null,
  rule: null,
  knowledge: null,
  experience: null,
  template: null,
  vector: null,
});

const HIGH_RATED_TRIGGER =
  /(高評価|ベスト).*(見せ|表示|リスト|一覧)|(見せ|表示).*(高評価|ベスト)/;

const ENV_API_BASE_URL: string = String(
  (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8765',
).replace(/\/+$/, '');

const dataURLToFile = (dataUrl: string, filename: string): File => {
  const [header, encoded] = String(dataUrl).split(',');
  const mimeMatch = header?.match(/:(.*?);/);
  const mime = mimeMatch?.[1] || 'image/png';
  const binary = atob(encoded || '');
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return new File([bytes], filename, { type: mime });
};

const fileToDataUrl = (file: File): Promise<string> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });

const randomSuffix = (): string => Math.random().toString(36).slice(2, 8);

export default function AiChatPanel({
  onImportDB,
  onCreateDB,
  onOpenManualEdit,
}: AiChatPanelProps): React.ReactElement {
  const {
    messages,
    isLoading,
    sendMessage,
    sendImage,
    cancelRequest,
    loadHistory,
    addSystemMessage,
    isRagMode,
    setIsRagMode,
    forceJsonMode,
    setForceJsonMode,
    chatMode,
    setChatMode,
    modeLabel,
    isAiMode,
    isChatbotMode,
    backendStatus,
    backendMode,
    backendSource,
    isBackendModeConfirmed,
  } = useAiChat({ onImportDB });

  const [panelWidth, setPanelWidth] = useState<'normal' | 'wide'>('normal');
  const [isMemoryOpen, setIsMemoryOpen] = useState<boolean>(false);
  const [isPastingImage, setIsPastingImage] = useState<boolean>(false);
  const [isHighRatedOpen, setIsHighRatedOpen] = useState<boolean>(false);
  const [zipModalState, setZipModalState] = useState<{ isOpen: boolean; file: File | null }>({
    isOpen: false,
    file: null,
  });
  const [editModalState, setEditModalState] = useState<{ isOpen: boolean; blockData: unknown }>({
    isOpen: false,
    blockData: null,
  });

  const [screenshots, setScreenshots] = useState<Screenshot[]>([]);
  const [memories, setMemories] = useState<MemoriesState>(createEmptyMemories);
  const savingIdsRef = useRef<Set<string>>(new Set());

  // ⚙️ メニュー ＆ サブスク管理State（専用フォルダーのコンポーネントへ委譲）
  const [isGearMenuOpen, setIsGearMenuOpen] = useState<boolean>(false);
  const [activeSettingsModal, setActiveSettingsModal] = useState<GearSubModalType>(null);
  const [subState, setSubState] = useState<SubscriptionState>(INITIAL_SUB_STATE);
  const [subToast, setSubToast] = useState<string | null>(null);
  const [personalIntelEnabled, setPersonalIntelEnabled] = useState<boolean>(true);
  const [watermarkEnabled, setWatermarkEnabled] = useState<boolean>(true);
  const [publicLinks, setPublicLinks] = useState(INITIAL_PUBLIC_LINKS);

  // 左側サイドバーの「⚙️」アイコンクリックを自動検知
  useEffect(() => {
    const handleGlobalGearClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement | null;
      if (!target) return;
      const text = (target.textContent || '').trim();
      if (text === '⚙️' || target.closest('[data-gear-trigger="true"]')) {
        e.stopPropagation();
        setIsGearMenuOpen((prev) => !prev);
      }
    };
    document.addEventListener('click', handleGlobalGearClick);
    return () => document.removeEventListener('click', handleGlobalGearClick);
  }, []);

  useEffect(() => {
    fetch(`${ENV_API_BASE_URL}/api/to/subscription/status`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && data.plan) setSubState((prev) => ({ ...prev, ...data }));
      })
      .catch(() => {});
  }, []);

  const [vscode] = useState<VsCodeApi | null>(() => {
    if (typeof window !== 'undefined' && typeof window.acquireVsCodeApi === 'function') {
      try {
        return window.acquireVsCodeApi();
      } catch {}
    }
    return null;
  });

  // サブスク・デポジット・ガチャ操作ハンドラ
  const handleChargeDeposit = async (amount: number) => {
    if (amount < 50) {
      setSubToast('🚫 日本円のカード決済は最低50円からの制限があるため、1円単発のカード決済は拒否されます！');
      return;
    }
    if (subState.user_wallet_jpy < amount) {
      setSubToast('⚠️ ユーザー財布の所持金が不足しています！');
      return;
    }
    try {
      const res = await fetch(`${ENV_API_BASE_URL}/api/to/subscription/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'charge_deposit', charge_amount_jpy: amount }),
      });
      if (res.ok) {
        const data = await res.json();
        setSubState((prev) => ({ ...prev, ...data.state }));
        setSubToast(data.message);
        return;
      }
    } catch {}

    const fee = Math.max(1, Math.round(amount * 0.036));
    const net = amount - fee;
    setSubState((prev) => ({
      ...prev,
      user_wallet_jpy: prev.user_wallet_jpy - amount,
      app_deposit_jpy: prev.app_deposit_jpy + amount,
      gateway_fee_jpy: prev.gateway_fee_jpy + fee,
      operator_revenue_jpy: prev.operator_revenue_jpy + net,
    }));
    setSubToast(`💳 ¥${amount}をチャージしました！（手数料3.6%: ¥${fee} / 運営売上: +¥${net}）`);
  };

  const handleSubscribeOneYen = async (method: 'demo_instant' | 'deposit_wallet') => {
    if (method === 'deposit_wallet' && subState.app_deposit_jpy < 1) {
      setSubToast('⚠️ デポジット残高が0ptです。先に+¥50または+¥100チャージを押してください！');
      return;
    }
    try {
      const res = await fetch(`${ENV_API_BASE_URL}/api/to/subscription/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'subscribe_1yen', payment_method: method }),
      });
      if (res.ok) {
        const data = await res.json();
        setSubState((prev) => ({ ...prev, ...data.state }));
        setSubToast(data.message);
        return;
      }
    } catch {}

    setSubState((prev) => ({
      ...prev,
      plan: 'pro_1yen',
      price_jpy: 1,
      gacha_tickets: prev.gacha_tickets + 10,
      user_wallet_jpy: method === 'demo_instant' ? prev.user_wallet_jpy - 1 : prev.user_wallet_jpy,
      app_deposit_jpy: method === 'deposit_wallet' ? prev.app_deposit_jpy - 1 : prev.app_deposit_jpy,
      operator_revenue_jpy: method === 'demo_instant' ? prev.operator_revenue_jpy + 1 : prev.operator_revenue_jpy,
    }));
    setSubToast('🎉 月額1円サブスク登録完了！ガチャ券10枚が追加付与されました！');
  };

  const handlePullGacha = async (count: number) => {
    if (subState.gacha_tickets < count) {
      setSubToast(`⚠️ ガチャ券が足りません（所持: ${subState.gacha_tickets}枚）`);
      return;
    }
    try {
      const res = await fetch(`${ENV_API_BASE_URL}/api/to/subscription/gacha-pull`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ count }),
      });
      if (res.ok) {
        const data = await res.json();
        setSubState((prev) => ({ ...prev, ...data.state }));
        setSubToast(data.message);
        return;
      }
    } catch {}

    const pulled: GachaItem[] = Array.from(
      { length: count },
      () => GACHA_POOL[Math.floor(Math.random() * GACHA_POOL.length)],
    );
    setSubState((prev) => ({
      ...prev,
      gacha_tickets: prev.gacha_tickets - count,
      gacha_inventory: [...pulled, ...prev.gacha_inventory],
    }));
    setSubToast(`🎰 ${count}回ガチャを引きました！`);
  };

  const handleSend = (text: unknown) => {
    if (typeof text === 'string') {
      if (HIGH_RATED_TRIGGER.test(text)) {
        setIsHighRatedOpen(true);
        addSystemMessage('⭐ 高評価リストを開きました。');
        return;
      }
      if (/(サブスク|定期購入|ガチャ券|1円決済)/.test(text)) {
        setActiveSettingsModal('subscription');
        addSystemMessage('💳 定期購入の管理を開きました。');
        return;
      }
    }
    return sendMessage(text);
  };

  const handleChatModeChange = (nextMode: string) => {
    if (isLoading || nextMode === chatMode) return;
    setChatMode(nextMode);
    addSystemMessage(
      nextMode === CHAT_MODES.AI
        ? 'AIモードを選択しました。'
        : 'チャットボットモードを選択しました。',
    );
  };

  const backendModeLabel = backendMode === CHAT_MODES.CHATBOT ? 'チャットボット' : 'AI';

  const saveMemory = async (type: MemoryType, payload: unknown) => {
    const key = `ai_mem_${type}`;
    const savedAt = new Date().toISOString();
    try {
      localStorage.setItem(key, JSON.stringify({ payload, updatedAt: savedAt }));
      setMemories((prev) => ({
        ...prev,
        [type]: { id: `${type}-${Date.now()}`, payload, pending: false, createdAt: savedAt },
      }));
      addSystemMessage(`ローカルに${type}メモリを保存しました。`);
    } catch {
      addSystemMessage(`${type}メモリの保存に失敗しました。`);
    }
  };

  const saveScreenshot = async (file: File | null | undefined) => {
    if (!file) return;
    try {
      const tempId = `shot-temp-${Date.now()}-${randomSuffix()}`;
      const filename = file.name || `screenshot-${Date.now()}.png`;
      const dataUrl = await fileToDataUrl(file);
      const storageKey = `ai_screenshot_${tempId}`;
      localStorage.setItem(storageKey, dataUrl);
      setScreenshots((prev) => [
        { id: `local-${tempId}`, filename, uri: storageKey, mime: file.type || 'image/png', createdAt: new Date().toISOString(), dataUrl, pending: false },
        ...prev,
      ]);
      addSystemMessage(`スクリーンショットを保存しました: ${filename}`);
    } catch {
      addSystemMessage('スクリーンショットの保存に失敗しました。');
    }
  };

  const handleDeleteScreenshot = (screenshotId: string) => {
    setScreenshots((prev) => prev.filter((s) => s.id !== screenshotId));
  };

  const handleUseScreenshot = (screenshot: Screenshot | null | undefined) => {
    if (!screenshot?.dataUrl) return;
    const file = dataURLToFile(screenshot.dataUrl, screenshot.filename || 'screenshot.png');
    sendImage(file);
    addSystemMessage('スクリーンショットを解析に送信しました。');
  };

  const handleImageUpload = (file: File) => {
    void saveScreenshot(file);
    sendImage(file);
  };

  const openManualEdit = (block: unknown) => {
    if (onOpenManualEdit) {
      onOpenManualEdit(block);
      return;
    }
    setEditModalState({ isOpen: true, blockData: block });
  };

  const handleOptionSelect = (selectedOptions: unknown) => {
    if (
      typeof selectedOptions === 'object' &&
      selectedOptions !== null &&
      (selectedOptions as any).action === 'send_chat'
    ) {
      handleSend((selectedOptions as any).text);
      return;
    }
    const options: string[] = Array.isArray(selectedOptions) ? (selectedOptions as string[]) : [];
    addSystemMessage(`選択結果: ${options.join(', ')}`);
    if (options.includes('自分で編集')) {
      const latestUiCodeMessage = [...(messages as unknown as ChatMessageLike[])]
        .reverse()
        .find((m) => m.type === 'ui_code');
      const firstBlock =
        latestUiCodeMessage?.content?.blocks?.[0] ??
        latestUiCodeMessage?.blocks?.[0] ??
        latestUiCodeMessage?.text?.blocks?.[0];
      if (firstBlock) openManualEdit(firstBlock);
    }
  };

  return (
    <div
      className={`relative flex h-full max-h-screen w-full flex-col overflow-hidden border-l bg-white transition-all duration-300 dark:bg-slate-900 ${
        isPastingImage
          ? 'ring-4 ring-blue-500 shadow-[0_0_40px_rgba(59,130,246,0.3)]'
          : 'border-slate-200 dark:border-slate-800'
      }`}
    >
      <section className="shrink-0 border-b border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-950">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="inline-flex rounded-lg bg-slate-200 p-1 dark:bg-slate-800" role="group">
            <button
              type="button"
              disabled={isLoading}
              onClick={() => handleChatModeChange(CHAT_MODES.AI)}
              className={`rounded-md px-3 py-1.5 text-sm font-semibold transition ${
                isAiMode ? 'bg-blue-600 text-white shadow' : 'text-slate-600 dark:text-slate-300'
              }`}
            >
              AI
            </button>
            <button
              type="button"
              disabled={isLoading}
              onClick={() => handleChatModeChange(CHAT_MODES.CHATBOT)}
              className={`rounded-md px-3 py-1.5 text-sm font-semibold transition ${
                isChatbotMode ? 'bg-emerald-600 text-white shadow' : 'text-slate-600 dark:text-slate-300'
              }`}
            >
              チャットボット
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            <button
              type="button"
              onClick={() => setIsHighRatedOpen(true)}
              className="rounded-md bg-amber-100 px-2 py-1 font-semibold text-amber-700 dark:bg-amber-950 dark:text-amber-300"
            >
              ⭐ 高評価
            </button>
            <button
              type="button"
              onClick={() => setIsGearMenuOpen((prev) => !prev)}
              className="rounded-md bg-indigo-100 px-2 py-1 font-semibold text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300"
            >
              ⚙️ 設定・サブスク (🎫{subState.gacha_tickets})
            </button>
            <span className="rounded-full bg-white px-2 py-1 text-slate-600 shadow-sm dark:bg-slate-800 dark:text-slate-300">
              選択: {modeLabel}
            </span>
            <span className="rounded-full px-2 py-1 bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300">
              Backend: {backendModeLabel}
              {isBackendModeConfirmed ? '・同期済み' : '・次回送信で同期'}
            </span>
          </div>
        </div>
      </section>

      <div className="shrink-0">
        <AiChatHeader
          panelWidth={panelWidth}
          setPanelWidth={setPanelWidth}
          onCreateDB={onCreateDB}
          onLoadHistory={loadHistory}
          onOpenMemory={() => setIsMemoryOpen(true)}
          onDownloadZip={() => console.log('ZIPダウンロード')}
          onUploadImage={handleImageUpload}
          onUploadZip={(file: File) => setZipModalState({ isOpen: true, file })}
          onSaveProjectMemory={(metadata: unknown) => saveMemory('project', metadata)}
          onSaveRuleMemory={(rule: unknown) => saveMemory('rule', rule)}
        />
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto flex flex-col">
        <AiChatMessageList
          messages={messages}
          isLoading={isLoading}
          onOptionSelect={handleOptionSelect}
          onOpenManualEdit={openManualEdit}
        />
      </div>

      <div className="shrink-0 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
        <AiChatInput
          onSend={handleSend}
          isLoading={isLoading}
          onSendImage={handleImageUpload}
          forceJsonMode={forceJsonMode}
          setForceJsonMode={setForceJsonMode}
        />
      </div>

      <MemoryDrawer
        isOpen={isMemoryOpen}
        onClose={() => setIsMemoryOpen(false)}
        screenshots={screenshots}
        memories={memories}
        onUseScreenshot={handleUseScreenshot}
        onDeleteScreenshot={handleDeleteScreenshot}
        onSaveMemory={saveMemory}
      />

      <ZipUploadModal
        isOpen={zipModalState.isOpen}
        file={zipModalState.file}
        onClose={() => setZipModalState({ isOpen: false, file: null })}
        onComplete={() => {
          addSystemMessage('📁 ZIPプロジェクトを記憶しました。');
          setIsRagMode(true);
        }}
      />

      <ManualEditModal
        isOpen={editModalState.isOpen}
        blockData={editModalState.blockData}
        onClose={() => setEditModalState({ isOpen: false, blockData: null })}
        onSave={() => {
          setEditModalState({ isOpen: false, blockData: null });
          addSystemMessage('手動編集を保存しました。');
        }}
      />

      <HighRatedModal isOpen={isHighRatedOpen} onClose={() => setIsHighRatedOpen(false)} />

      {/* 分散化した⚙️12項目メニュー＆サブスク管理モーダル */}
      <GearPopupMenu
        isOpen={isGearMenuOpen}
        plan={subState.plan}
        personalIntelEnabled={personalIntelEnabled}
        watermarkEnabled={watermarkEnabled}
        publicLinksCount={publicLinks.length}
        onClose={() => setIsGearMenuOpen(false)}
        onSelectModal={(m) => setActiveSettingsModal(m)}
        onDownloadData={() =>
          exportImportantDataJson({ subscription: subState, memories })
        }
      />

      <SubscriptionModal
        isOpen={activeSettingsModal === 'subscription'}
        subState={subState}
        subToast={subToast}
        onClose={() => setActiveSettingsModal(null)}
        onClearToast={() => setSubToast(null)}
        onChargeDeposit={handleChargeDeposit}
        onSubscribeOneYen={handleSubscribeOneYen}
        onCancelSubscription={() =>
          setSubState((prev) => ({ ...prev, plan: 'free', price_jpy: 0 }))
        }
        onPullGacha={handlePullGacha}
      />

      <SettingsSubModals
        activeModal={activeSettingsModal}
        selectedModel={subState.selected_model}
        personalIntelEnabled={personalIntelEnabled}
        watermarkEnabled={watermarkEnabled}
        publicLinks={publicLinks}
        onClose={() => setActiveSettingsModal(null)}
        onOpenSubscription={() => setActiveSettingsModal('subscription')}
        onTogglePersonalIntel={setPersonalIntelEnabled}
        onToggleWatermark={setWatermarkEnabled}
        onDeletePublicLink={(id) =>
          setPublicLinks((prev) => prev.filter((x) => x.id !== id))
        }
      />
    </div>
  );
}
