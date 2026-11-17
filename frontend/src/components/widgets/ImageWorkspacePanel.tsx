// frontend/src/components/widgets/ImageWorkspacePanel.tsx
import React, { useState, useRef, useEffect } from "react";
import {
  Image as ImageIcon,
  Upload,
  Link2,
  ClipboardPaste,
  ZoomIn,
  ZoomOut,
  Trash2,
  Sparkles,
  ScanText,
  FileSearch,
  CheckCircle2,
} from "lucide-react";

export interface LoadedImageMeta {
  id: string;
  name: string;
  dataUrl: string; // Base64 または URL
  width: number;
  height: number;
  sizeKb: number;
  mimeType: string;
  dominantColors: string[];
  ocrResultText?: string;
}

export interface ImageWorkspacePanelProps {
  apiBaseUrl?: string;
  /** ChatOrchestrator へ image_base64 付きで送信するコールバック */
  onSendImageToChat?: (payload: {
    message: string;
    image_base64: string;
    mode: "ocr_grading" | "ocr_character" | "job_eval" | "general_vision";
  }) => void;
}

export default function ImageWorkspacePanel({
  apiBaseUrl = "",
  onSendImageToChat,
}: ImageWorkspacePanelProps) {
  const [images, setImages] = useState<LoadedImageMeta[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [urlInput, setUrlInput] = useState("");
  const [promptInput, setPromptInput] = useState("この画像のテキストと構造特徴を解析して");
  const [analysisMode, setAnalysisMode] = useState<
    "ocr_grading" | "ocr_character" | "job_eval" | "general_vision"
  >("ocr_character");
  const [zoom, setZoom] = useState(1.0);
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeImage = images.find((img) => img.id === selectedId) || images[0] || null;

  // Canvas を使って画像の解像度と主要カラー（3色）を抽出するヘルパー
  const inspectImageElement = (
    dataUrl: string,
    name: string,
    sizeKb: number,
    mimeType: string
  ) => {
    const img = new window.Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      const colors: string[] = [];
      try {
        const canvas = document.createElement("canvas");
        canvas.width = 16;
        canvas.height = 16;
        const ctx = canvas.getContext("2d");
        if (ctx) {
          ctx.drawImage(img, 0, 0, 16, 16);
          const pts = [
            [4, 4],
            [8, 8],
            [12, 12],
          ];
          pts.forEach(([x, y]) => {
            const p = ctx.getImageData(x, y, 1, 1).data;
            const hex = `#${[p[0], p[1], p[2]]
              .map((v) => v.toString(16).padStart(2, "0"))
              .join("")}`;
            if (!colors.includes(hex)) colors.push(hex);
          });
        }
      } catch {
        colors.push("#6366f1");
      }

      const newEntry: LoadedImageMeta = {
        id: `img_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
        name,
        dataUrl,
        width: img.naturalWidth || 0,
        height: img.naturalHeight || 0,
        sizeKb,
        mimeType,
        dominantColors: colors,
      };
      setImages((prev) => [newEntry, ...prev]);
      setSelectedId(newEntry.id);
      setZoom(1.0);
      setStatusMsg(`画像を読み込みました: ${name} (${img.naturalWidth}×${img.naturalHeight}px)`);
    };
    img.onerror = () => {
      setStatusMsg("⚠️ 画像の読み込みに失敗しました。URLまたはファイル形式を確認してください。");
    };
    img.src = dataUrl;
  };

  // 1. ローカルファイルの読み込み (FileReader -> Base64)
  const handleFiles = (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    Array.from(fileList).forEach((file) => {
      if (!file.type.startsWith("image/")) return;
      const reader = new FileReader();
      reader.onload = (e) => {
        const result = String(e.target?.result || "");
        if (result) {
          inspectImageElement(
            result,
            file.name,
            Math.round(file.size / 1024),
            file.type
          );
        }
      };
      reader.readAsDataURL(file);
    });
  };

  // 2. Ctrl+V (クリップボードからのスクショ貼り付け) 対応
  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      for (const item of Array.from(items)) {
        if (item.type.startsWith("image/")) {
          const file = item.getAsFile();
          if (file) {
            const dt = new DataTransfer();
            dt.items.add(file);
            handleFiles(dt.files);
          }
        }
      }
    };
    window.addEventListener("paste", handlePaste);
    return () => window.removeEventListener("paste", handlePaste);
  }, []);

  // 3. URLから画像を読み込む
  const handleLoadUrl = () => {
    const trimmed = urlInput.trim();
    if (!trimmed) return;
    inspectImageElement(trimmed, trimmed.split("/").pop() || "remote_image", 0, "image/url");
    setUrlInput("");
  };

  // 4. バックエンドの OCR / Image Fast Path へ送信
  const handleAnalyzeWithBackend = async () => {
    if (!activeImage) return;
    setIsAnalyzing(true);
    setStatusMsg("🔍 バックエンドで画像を解析中...");

    // 親コンポーネント (ChatOrchestrator の image_base64 ルート) へ通知
    onSendImageToChat?.({
      message: promptInput,
      image_base64: activeImage.dataUrl,
      mode: analysisMode,
    });

    const base = apiBaseUrl.replace(/\/+$/, "");
    try {
      const res = await fetch(`${base}/api/to/memory/ocr-screenshot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image: activeImage.dataUrl,
          mode: analysisMode,
          prompt: promptInput,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        const resultText = String(data.content || data.message || "解析完了");
        setImages((prev) =>
          prev.map((item) =>
            item.id === activeImage.id
              ? { ...item, ocrResultText: resultText }
              : item
          )
        );
        setStatusMsg("✅ バックエンドOCR解析が完了しました");
        setIsAnalyzing(false);
        return;
      }
    } catch {
      // フォールバック
    }

    // ローカル構造解析プレビュー（オフライン時）
    const fallbackReport = [
      `【画像構造解析レポート (${analysisMode})】`,
      `・ファイル名: ${activeImage.name}`,
      `・解像度: ${activeImage.width} × ${activeImage.height} px (アスペクト比 ${(
        activeImage.width / Math.max(1, activeImage.height)
      ).toFixed(2)})`,
      `・抽出カラーパレット: ${activeImage.dominantColors.join(", ")}`,
      `・ChatOrchestrator の 4. Image fast path (image_base64) へ送信準備完了`,
    ].join("\n");

    setImages((prev) =>
      prev.map((item) =>
        item.id === activeImage.id
          ? { ...item, ocrResultText: fallbackReport }
          : item
      )
    );
    setStatusMsg("✅ 画像構造データを抽出しました");
    setIsAnalyzing(false);
  };

  return (
    <div className="space-y-5 bg-slate-900 border border-slate-800 rounded-2xl p-5 text-slate-100">
      {/* ヘッダー */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div>
          <h2 className="text-base font-bold text-sky-400 flex items-center gap-2">
            <ImageIcon className="w-4 h-4" />
            画像読み込み・プレビュー ＆ OCR構造解析スタジオ
          </h2>
          <p className="text-xs text-slate-400">
            ドラッグ＆ドロップ、ファイル選択、画像URL、または <kbd className="bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700 text-sky-300">Ctrl + V</kbd> でスクショを直接貼り付けて読み込み・表示できます。
          </p>
        </div>
        {statusMsg && (
          <div className="bg-indigo-950/80 border border-indigo-700/60 text-indigo-200 px-3 py-1 rounded-lg text-xs flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>{statusMsg}</span>
          </div>
        )}
      </div>

      {/* 上段：読み込みバー（ファイルドロップ ＋ URL入力） */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            handleFiles(e.dataTransfer.files);
          }}
          onClick={() => fileInputRef.current?.click()}
          className={`lg:col-span-7 cursor-pointer rounded-xl border-2 border-dashed p-4 text-center transition flex flex-col items-center justify-center gap-1.5 ${
            isDragging
              ? "border-sky-400 bg-sky-950/30"
              : "border-slate-700 bg-slate-950/60 hover:border-indigo-500/70 hover:bg-slate-950"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
          <div className="flex items-center gap-2 text-xs font-bold text-sky-300">
            <Upload className="w-4 h-4" />
            <span>クリックして画像を選択 または ここにドラッグ＆ドロップ</span>
          </div>
          <span className="text-[11px] text-slate-400 flex items-center gap-1">
            <ClipboardPaste className="w-3 h-3" />
            画面上で Ctrl + V を押すとクリップボードのスクショを即座に読み込めます
          </span>
        </div>

        {/* URLから画像を読み込む */}
        <div className="lg:col-span-5 bg-slate-950/70 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between gap-2">
          <div className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
            <Link2 className="w-3.5 h-3.5 text-indigo-400" />
            <span>画像URLから直接読み込む</span>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder="https://example.com/sample.png"
              className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono"
            />
            <button
              type="button"
              onClick={handleLoadUrl}
              className="bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded-lg text-xs font-semibold shrink-0"
            >
              URL読込
            </button>
          </div>
        </div>
      </div>

      {/* 下段：左に画像ビューア＆サムネイル一覧、右に解析コントロール＆結果 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* 左7カラム：画像プレビューキャンバス */}
        <div className="lg:col-span-7 space-y-3">
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-3 min-h-[300px] flex flex-col justify-between">
            {activeImage ? (
              <>
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-2 mb-2 text-xs">
                  <span className="font-bold text-slate-200 truncate max-w-[260px]">
                    🖼️ {activeImage.name}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[11px] font-mono text-slate-400">
                      {activeImage.width}×{activeImage.height}px
                      {activeImage.sizeKb > 0 ? ` (${activeImage.sizeKb}KB)` : ""}
                    </span>
                    <button
                      type="button"
                      onClick={() => setZoom((z) => Math.max(0.5, +(z - 0.25).toFixed(2)))}
                      className="p-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-300"
                      title="縮小"
                    >
                      <ZoomOut className="w-3.5 h-3.5" />
                    </button>
                    <span className="text-[10px] font-mono text-sky-400 w-10 text-center">
                      {Math.round(zoom * 100)}%
                    </span>
                    <button
                      type="button"
                      onClick={() => setZoom((z) => Math.min(2.5, +(z + 0.25).toFixed(2)))}
                      className="p-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-300"
                      title="拡大"
                    >
                      <ZoomIn className="w-3.5 h-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setImages((prev) => prev.filter((i) => i.id !== activeImage.id));
                        setSelectedId(null);
                      }}
                      className="p-1 rounded bg-slate-900 hover:bg-rose-950 text-slate-400 hover:text-rose-400"
                      title="削除"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* 画像表示エリア */}
                <div className="flex-1 overflow-auto flex items-center justify-center max-h-[340px] bg-slate-900/40 rounded-lg p-2">
                  <img
                    src={activeImage.dataUrl}
                    alt={activeImage.name}
                    style={{ transform: `scale(${zoom})`, transformOrigin: "center" }}
                    className="max-h-[300px] w-auto object-contain rounded transition-transform duration-150"
                  />
                </div>

                {/* 抽出カラーパレット表示 */}
                <div className="flex items-center justify-between pt-2 mt-2 border-t border-slate-800/80 text-[11px] text-slate-400">
                  <div className="flex items-center gap-1.5">
                    <span>主要カラー:</span>
                    {activeImage.dominantColors.map((hex) => (
                      <span
                        key={hex}
                        className="inline-flex items-center gap-1 bg-slate-900 border border-slate-800 px-1.5 py-0.5 rounded font-mono text-[10px]"
                      >
                        <span
                          style={{ backgroundColor: hex }}
                          className="w-2.5 h-2.5 rounded-full inline-block"
                        />
                        {hex}
                      </span>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-slate-500 text-xs py-16 gap-2">
                <ImageIcon className="w-8 h-8 opacity-40" />
                <span>まだ画像が読み込まれていません（上の枠にドロップまたは Ctrl+V で貼り付け）</span>
              </div>
            )}
          </div>

          {/* 複数画像のサムネイルストリップ */}
          {images.length > 1 && (
            <div className="flex gap-2 overflow-x-auto pb-1">
              {images.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setSelectedId(item.id)}
                  className={`h-14 w-14 shrink-0 rounded-lg overflow-hidden border-2 transition ${
                    activeImage?.id === item.id
                      ? "border-sky-400 ring-2 ring-sky-500/30"
                      : "border-slate-800 opacity-60 hover:opacity-100"
                  }`}
                >
                  <img src={item.dataUrl} alt={item.name} className="h-full w-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 右5カラム：OCR・画像解析モード選択 ＆ 結果出力 */}
        <div className="lg:col-span-5 space-y-3">
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3">
            <div className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
              <ScanText className="w-4 h-4 text-indigo-400" />
              <span>画像の解析モード（LoadingIndicator / Backend 連動）</span>
            </div>

            <div className="grid grid-cols-2 gap-1.5 text-[11px]">
              {[
                { id: "ocr_character", label: "🔍 文字・スクショOCR" },
                { id: "ocr_grading", label: "📝 解答用紙・自動採点" },
                { id: "job_eval", label: "📊 求人票・条件抽出" },
                { id: "general_vision", label: "🖼️ 構造・配色解析" },
              ].map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setAnalysisMode(m.id as any)}
                  className={`px-2.5 py-2 rounded-lg border text-left transition ${
                    analysisMode === m.id
                      ? "bg-indigo-600/30 border-indigo-500 text-white font-semibold"
                      : "bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800"
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>

            <input
              type="text"
              value={promptInput}
              onChange={(e) => setPromptInput(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200"
              placeholder="画像に対する指示（例: 求人票の年収と残業時間を抽出して）"
            />

            <button
              type="button"
              disabled={!activeImage || isAnalyzing}
              onClick={handleAnalyzeWithBackend}
              className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-bold py-2.5 rounded-xl text-xs flex items-center justify-center gap-1.5 transition"
            >
              <Sparkles className="w-4 h-4" />
              {isAnalyzing ? "画像を解析中..." : "選択中の画像をAIで読み取る・解析する"}
            </button>
          </div>

          {/* 解析結果テキスト表示 */}
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-2">
            <div className="text-xs font-bold text-emerald-400 flex items-center gap-1.5">
              <FileSearch className="w-4 h-4" />
              <span>読み取り・解析結果</span>
            </div>
            <pre className="text-xs text-slate-300 whitespace-pre-wrap font-mono bg-slate-900/80 border border-slate-800 rounded-lg p-3 min-h-[120px] max-h-[200px] overflow-y-auto leading-relaxed">
              {activeImage?.ocrResultText ||
                "画像を読み込んで「AIで読み取る・解析する」を押すと、ここに抽出テキストや構造データが表示されます。"}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}